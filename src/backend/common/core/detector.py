# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
from typing import Optional

import cv2
import numpy as np
import torch
from ultralytics import YOLO  # type: ignore[import-untyped]

from common.config import config
from common.utils.geometry import get_detections

try:  # pragma: no cover - optional dependency import
    import onnxruntime as ort  # type: ignore[import-not-found,import-untyped]
except Exception:  # pragma: no cover - handled during backend selection
    ort = None


Detection = tuple[int, int, int, int, int, float]


class _Detector:
    def __init__(self, backend: Optional[str] = None) -> None:
        """Initialize the YOLO object detector.

        Loads the YOLO model from the configured path and sets up internal
        state for asynchronous inference, caching, and distance estimation.

        Raises:
            FileNotFoundError: If the YOLO model file does not exist at the
            configured path.
        """
        backend_name = (backend or config.DETECTOR_BACKEND).lower()
        self._engine: _DetectorEngine
        if backend_name == "onnx":
            self._engine = _OnnxRuntimeDetector()
        elif backend_name == "torch":
            self._engine = _TorchDetector()
        else:
            raise ValueError(
                f"Unsupported DETECTOR_BACKEND '{backend_name}'. Use 'torch' or 'onnx'."
            )

        self._last_det: Optional[list[Detection]] = None
        self._last_time: float = 0.0
        self._lock = asyncio.Lock()

    async def infer(
        self, frame_rgb: np.ndarray
    ) -> list[Detection]:
        """Run YOLO inference asynchronously on a single frame.

        Performs object detection on the given RGB image using the loaded YOLO model.
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


def _get_detector() -> _Detector:
    """Get or create the singleton detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = _Detector()
    return _detector_instance


class _DetectorEngine:
    def predict(self, frame_rgb: np.ndarray) -> list[Detection]:
        raise NotImplementedError


class _TorchDetector(_DetectorEngine):
    def __init__(self) -> None:
        model_path = config.MODEL_PATH
        if not model_path.exists():
            raise FileNotFoundError(
                f"YOLO model not found at '{model_path}'. Set MODEL_PATH accordingly."
            )

        self._model = YOLO(str(model_path))
        self._device = self._resolve_device(config.TORCH_DEVICE)
        self._half = self._resolve_half_precision(config.TORCH_HALF_PRECISION)
        self._imgsz = config.DETECTOR_IMAGE_SIZE
        self._conf = config.DETECTOR_CONF_THRESHOLD

    def predict(self, frame_rgb: np.ndarray) -> list[Detection]:
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
        if override:
            return override
        if torch.cuda.is_available():
            return "cuda:0"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _resolve_half_precision(self, pref: Optional[str]) -> bool:
        if pref is None:
            pref = "auto"
        pref = pref.lower()
        if pref in ("true", "1", "yes"):
            return True
        if pref in ("false", "0", "no"):
            return False
        return self._device.startswith("cuda")


class _OnnxRuntimeDetector(_DetectorEngine):
    def __init__(self) -> None:
        if ort is None:
            raise RuntimeError(
                "onnxruntime is required for DETECTOR_BACKEND='onnx'. Install "
                "`onnxruntime` (CPU) or the appropriate GPU package such as "
                "`onnxruntime-gpu` or `onnxruntime-rocm`."
            )

        model_path = config.ONNX_MODEL_PATH
        if not model_path.exists():
            raise FileNotFoundError(
                f"ONNX model not found at '{model_path}'. Set ONNX_MODEL_PATH or export "
                "a YOLO onnx model first."
            )

        providers = self._resolve_providers()
        sess_options = ort.SessionOptions()
        sess_options.enable_mem_pattern = False
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
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
        input_tensor, ratio, dwdh = self._prepare_input(frame_rgb)
        ort_inputs = {self._input_name: input_tensor}
        outputs = self._session.run(self._output_names, ort_inputs)[0]
        h, w = frame_rgb.shape[:2]
        return self._postprocess(outputs, (h, w), ratio, dwdh)

    def _prepare_input(
        self, frame_rgb: np.ndarray
    ) -> tuple[np.ndarray, float, tuple[float, float]]:
        resized, ratio, dwdh = _letterbox(frame_rgb, self._imgsz)
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
        boxes = _xywh_to_xyxy(xywh)
        boxes = _scale_boxes(boxes, ratio, dwdh, original_hw)

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
            keep = _nms(cls_boxes, cls_scores, self._iou)
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


def _letterbox(
    image: np.ndarray,
    new_size: int,
    color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize image with unchanged aspect ratio using padding."""
    shape = image.shape[:2]  # (h, w)
    scale = min(new_size / shape[0], new_size / shape[1])
    new_unpad = (int(round(shape[1] * scale)), int(round(shape[0] * scale)))
    resized = cv2.resize(image, new_unpad, interpolation=cv2.INTER_LINEAR)

    dw = new_size - new_unpad[0]
    dh = new_size - new_unpad[1]
    top = int(np.floor(dh / 2))
    bottom = int(np.ceil(dh / 2))
    left = int(np.floor(dw / 2))
    right = int(np.ceil(dw / 2))

    resized = cv2.copyMakeBorder(
        resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
    )
    return resized, scale, (dw / 2, dh / 2)


def _xywh_to_xyxy(xywh: np.ndarray) -> np.ndarray:
    xyxy = np.zeros_like(xywh)
    xyxy[:, 0] = xywh[:, 0] - xywh[:, 2] / 2
    xyxy[:, 1] = xywh[:, 1] - xywh[:, 3] / 2
    xyxy[:, 2] = xywh[:, 0] + xywh[:, 2] / 2
    xyxy[:, 3] = xywh[:, 1] + xywh[:, 3] / 2
    return xyxy


def _scale_boxes(
    boxes: np.ndarray,
    ratio: float,
    dwdh: tuple[float, float],
    original_hw: tuple[int, int],
) -> np.ndarray:
    boxes = boxes.copy()
    boxes[:, [0, 2]] -= dwdh[0]
    boxes[:, [1, 3]] -= dwdh[1]
    boxes[:, :4] /= max(ratio, 1e-6)

    h, w = original_hw
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, max(w - 1, 0))
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, max(h - 1, 0))
    return boxes


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thres: float) -> list[int]:
    if boxes.size == 0:
        return []
    idxs = scores.argsort()[::-1]
    keep: list[int] = []
    while len(idxs) > 0:
        i = idxs[0]
        keep.append(i)
        if len(idxs) == 1:
            break
        ious = _iou(boxes[i], boxes[idxs[1:]])
        idxs = idxs[1:][ious <= iou_thres]
    return keep


def _iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    if boxes.size == 0:
        return np.empty(0, dtype=np.float32)
    inter_x1 = np.maximum(box[0], boxes[:, 0])
    inter_y1 = np.maximum(box[1], boxes[:, 1])
    inter_x2 = np.minimum(box[2], boxes[:, 2])
    inter_y2 = np.minimum(box[3], boxes[:, 3])

    inter_w = np.clip(inter_x2 - inter_x1, a_min=0.0, a_max=None)
    inter_h = np.clip(inter_y2 - inter_y1, a_min=0.0, a_max=None)
    inter_area = inter_w * inter_h

    box_area = max((box[2] - box[0]) * (box[3] - box[1]), 0.0)
    boxes_area = np.clip(boxes[:, 2] - boxes[:, 0], 0.0, None) * np.clip(
        boxes[:, 3] - boxes[:, 1], 0.0, None
    )
    union = box_area + boxes_area - inter_area + 1e-6
    return inter_area / union
