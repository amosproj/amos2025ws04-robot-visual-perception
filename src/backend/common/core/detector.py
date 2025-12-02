# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import asyncio

from pathlib import Path
from typing import Optional, Callable

import numpy as np
import torch
from ultralytics import YOLO  # type: ignore[import-untyped]

from common.core.contracts import Detection, ObjectDetectionBackend, ObjectDetector
from common.config import config
from common.utils.geometry import get_detections
from common.utils.image import letterbox, scale_boxes
from common.utils.math import non_maximum_supression, xywh_to_xyxy

try:  # pragma: no cover - optional dependency import
    import onnxruntime as ort  # type: ignore[import-not-found,import-untyped]
except Exception:  # pragma: no cover - handled during backend selection
    ort = None
BackendFactory = Callable[[Optional[Path]], ObjectDetectionBackend]
_backend_registry: dict[str, BackendFactory] = {}


def register_detector_backend(name: str, factory: BackendFactory) -> None:
    """Register a detector backend factory by name."""
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("Detector backend name cannot be empty")
    _backend_registry[normalized] = factory


def available_detector_backends() -> list[str]:
    """Return the list of known detector backends."""
    return sorted(_backend_registry)


def _build_engine(
    model_path: Optional[Path], backend: Optional[str]
) -> ObjectDetectionBackend:
    backend_name = (backend or config.DETECTOR_BACKEND).lower()
    try:
        factory = _backend_registry[backend_name]
    except KeyError:
        known = ", ".join(available_detector_backends())
        raise ValueError(
            f"Unsupported DETECTOR_BACKEND '{backend_name}'. Known backends: {known or 'none'}."
        ) from None
    return factory(model_path)


class _Detector(ObjectDetector):
    def __init__(
        self, model_path: Optional[Path] = None, backend: Optional[str] = None
    ) -> None:
        """Initialize the object detector for the chosen backend.

        Selects a registered backend (torch/onnx by default) and sets up
        internal state for asynchronous inference and caching.

        Args:
            model_path: Optional path to a model file to override config.
            backend: Optional backend name ('torch' or 'onnx'). If None, uses config.DETECTOR_BACKEND.
        """

        self._engine: ObjectDetectionBackend = _build_engine(model_path, backend)
        self._last_det: Optional[list[Detection]] = None
        self._last_time: float = 0.0
        self._lock = asyncio.Lock()

    async def infer(self, frame_rgb: np.ndarray) -> list[Detection]:
        """Run detection asynchronously on a single frame.

        Performs object detection on the given RGB image using the loaded backend.
        Uses simple caching to avoid repeated inference calls within 100 ms.

        Args:
            frame_rgb (np.ndarray): Input image in RGB color format.

        Returns:
            list[tuple[int, int, int, int, int, float]]: A list of detections, where each
            tuple contains (x1, y1, x2, y2, class_id, confidence).
        """
        now = asyncio.get_running_loop().time()
        if self._last_det is not None and (now - self._last_time) < 0.10:
            return self._last_det

        async with self._lock:
            now = asyncio.get_running_loop().time()
            if self._last_det is not None and (now - self._last_time) < 0.10:
                return self._last_det

            loop = asyncio.get_running_loop()
            detections = await loop.run_in_executor(
                None, self._engine.predict, frame_rgb
            )
            self._last_det = detections
            self._last_time = now
            return detections


_detector_instance: Optional[_Detector] = None


def _get_detector(model_path: Optional[Path] = None) -> _Detector:
    """Get or create the singleton detector instance.

    Args:
        model_path: Path to the YOLO model file. Only used on first call.
            Subsequent calls will return the existing instance.

    Returns:
        The singleton detector instance.
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = _Detector(model_path=model_path)
    return _detector_instance


# Public alias to encourage non-underscored access in new code
get_detector = _get_detector


class _DetectorEngine:
    """Base class for synchronous detector backends."""

    def predict(self, frame_rgb: np.ndarray) -> list[Detection]:
        """Run inference on an RGB frame and return parsed detections."""
        raise NotImplementedError


class _TorchDetector(_DetectorEngine):
    def __init__(self, model_path: Optional[Path] = None) -> None:
        # Accept an override model_path, otherwise use configured path
        if model_path is None:
            model_path = config.MODEL_PATH
        else:
            model_path = Path(model_path).resolve()

        self._model = YOLO(str(model_path))
        self._device = self._resolve_device(config.TORCH_DEVICE)
        self._half = self._resolve_half_precision(config.TORCH_HALF_PRECISION)
        self._imgsz = config.DETECTOR_IMAGE_SIZE
        self._conf = config.DETECTOR_CONF_THRESHOLD

    def predict(self, frame_rgb: np.ndarray) -> list[Detection]:
        """Run a single-frame inference with the torch-backed YOLO model."""
        inference_results = self._model.predict(
            frame_rgb,
            imgsz=self._imgsz,
            conf=self._conf,
            verbose=False,
            device=self._device,
            half=self._half,
        )
        return get_detections(inference_results)

    def _resolve_device(self, override: Optional[str]) -> str:
        """Pick the torch device, favoring explicit override, then CUDA/MPS, else CPU."""
        if override:
            return override
        if torch.cuda.is_available():
            return "cuda:0"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _resolve_half_precision(self, pref: Optional[str]) -> bool:
        """Return whether to run the model in FP16."""
        if pref is None:
            pref = "auto"
        pref = pref.lower()
        if pref in ("true", "1", "yes"):
            return True
        if pref in ("false", "0", "no"):
            return False
        return self._device.startswith("cuda")


class _OnnxRuntimeDetector(_DetectorEngine):
    def __init__(self, model_path: Optional[Path] = None) -> None:
        if ort is None:
            raise RuntimeError(
                "onnxruntime is required for DETECTOR_BACKEND='onnx'. Install "
                "`onnxruntime` (CPU) or the appropriate GPU package such as "
                "`onnxruntime-gpu` or `onnxruntime-rocm`."
            )

        # Accept an override model_path, otherwise use configured ONNX path
        if model_path is None:
            model_path = config.ONNX_MODEL_PATH
        else:
            model_path = Path(model_path).resolve()

        if not model_path.exists():
            raise FileNotFoundError(
                f"ONNX model not found at '{model_path}'. Set ONNX_MODEL_PATH or export "
                "a YOLO onnx model first."
            )

        providers = self._resolve_providers()
        sess_options = ort.SessionOptions()
        sess_options.enable_mem_pattern = False
        sess_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        self._session = ort.InferenceSession(
            str(model_path),
            providers=providers or None,
            sess_options=sess_options,
        )
        self._input_name = self._session.get_inputs()[0].name
        self._output_names = [node.name for node in self._session.get_outputs()]
        self._imgsz = config.DETECTOR_IMAGE_SIZE
        self._conf = config.DETECTOR_CONF_THRESHOLD
        self._iou = config.DETECTOR_IOU_THRESHOLD
        self._max_det = config.DETECTOR_MAX_DETECTIONS
        self._num_classes = config.DETECTOR_NUM_CLASSES

    def predict(self, frame_rgb: np.ndarray) -> list[Detection]:
        """Run ONNX Runtime inference and return scaled, filtered detections."""
        input_tensor, ratio, dwdh = self._prepare_input(frame_rgb)
        ort_inputs = {self._input_name: input_tensor}
        outputs = self._session.run(self._output_names, ort_inputs)[0]
        h, w = frame_rgb.shape[:2]
        return self._postprocess(outputs, (h, w), ratio, dwdh)

    def _prepare_input(
        self, frame_rgb: np.ndarray
    ) -> tuple[np.ndarray, float, tuple[float, float]]:
        """Resize, normalize, and batch the input frame for ONNX Runtime."""
        resized, ratio, dwdh = letterbox(frame_rgb, self._imgsz)
        img = resized.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        return np.ascontiguousarray(img), ratio, dwdh

    def _postprocess(
        self,
        output: np.ndarray,
        original_hw: tuple[int, int],
        ratio: float,
        dwdh: tuple[float, float],
    ) -> list[Detection]:
        """Convert raw model output into scaled, filtered, and NMS-processed detections in the format (x1, y1, x2, y2, class_id, score)."""
        preds = np.squeeze(output, axis=0)
        if preds.ndim == 1:
            preds = np.expand_dims(preds, 0)
        elif preds.ndim > 2:
            preds = preds.reshape(-1, preds.shape[-1])

        expected_no_obj = 4 + self._num_classes
        expected_with_obj = expected_no_obj + 1
        if preds.shape[-1] not in (expected_no_obj, expected_with_obj):
            preds = preds.T

        cols = preds.shape[-1]
        if cols not in (expected_no_obj, expected_with_obj):
            raise RuntimeError(
                f"Unexpected ONNX output shape {preds.shape}, expected "
                f"last dimension to be {expected_no_obj} or {expected_with_obj}"
            )

        preds = preds.reshape(-1, cols)
        xywh = preds[:, :4]
        boxes = xywh_to_xyxy(xywh)
        boxes = scale_boxes(boxes, ratio, dwdh, original_hw)

        if cols == expected_with_obj:
            obj = preds[:, 4:5]
            class_scores = preds[:, 5:] * obj
        else:
            class_scores = preds[:, 4:]

        confidences = np.max(class_scores, axis=1)
        class_ids = np.argmax(class_scores, axis=1)

        mask = confidences >= self._conf
        boxes = boxes[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        if boxes.size == 0:
            return []

        detections: list[Detection] = []
        for cls in np.unique(class_ids):
            cls_mask = class_ids == cls
            cls_boxes = boxes[cls_mask]
            cls_scores = confidences[cls_mask]
            keep = non_maximum_supression(cls_boxes, cls_scores, self._iou)
            for idx in keep:
                box = cls_boxes[idx]
                score = cls_scores[idx]
                detections.append(
                    (
                        int(round(box[0])),
                        int(round(box[1])),
                        int(round(box[2])),
                        int(round(box[3])),
                        int(cls),
                        float(score),
                    )
                )

        detections.sort(key=lambda det: det[5], reverse=True)
        return detections[: self._max_det]

    def _resolve_providers(self) -> list[str]:
        """Choose ONNX Runtime execution providers, preferring GPU-capable ones."""
        configured = config.ONNX_PROVIDERS
        if configured:
            return configured
        if ort is None:
            return []
        available = ort.get_available_providers()
        preferred = [
            "CUDAExecutionProvider",
            "ROCMExecutionProvider",
            "CoreMLExecutionProvider",
            "DmlExecutionProvider",
            "CPUExecutionProvider",
        ]
        providers = [p for p in preferred if p in available]
        return providers or available


# Register built-in backends
register_detector_backend("torch", _TorchDetector)
register_detector_backend("onnx", _OnnxRuntimeDetector)
