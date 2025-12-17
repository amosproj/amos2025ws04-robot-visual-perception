# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path
from typing import Callable, Literal, Optional

import numpy as np
import torch

from common.config import config
from common.core.contracts import DepthEstimator
from common.core.depth_utils import calculate_distances, resize_to_frame

import logging

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency import
    import onnxruntime as ort  # type: ignore[import-not-found,import-untyped]
except Exception:  # pragma: no cover - handled during backend selection
    ort = None

# Factories let us swap depth estimation backends without changing call sites.
DepthEstimatorFactory = Callable[[Optional[Path]], DepthEstimator]

_depth_estimator: Optional[DepthEstimator] = None
_backend_registry: dict[str, DepthEstimatorFactory] = {}


def register_depth_backend(name: str, factory: DepthEstimatorFactory) -> None:
    """Register a depth-estimation backend factory by name."""
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("Depth backend name cannot be empty")
    _backend_registry[normalized] = factory


def available_depth_backends() -> list[str]:
    """Return the list of registered depth backends."""
    return sorted(_backend_registry)


def _default_depth_estimator_factory(
    midas_cache_directory: Optional[Path] = None,
) -> DepthEstimator:
    backend_name = config.DEPTH_BACKEND
    logger.info(f"Initializing Depth Estimator with backend: {backend_name}")
    try:
        factory = _backend_registry[backend_name]
    except KeyError:
        known = ", ".join(available_depth_backends())
        raise ValueError(
            f"Unsupported DEPTH_BACKEND '{backend_name}'. "
            f"Known backends: {known or 'none'}."
        ) from None
    return factory(midas_cache_directory)


_depth_estimator_factory: DepthEstimatorFactory = _default_depth_estimator_factory


def register_depth_estimator(factory: DepthEstimatorFactory) -> None:
    """Register a factory used to build the singleton depth estimator."""
    global _depth_estimator_factory, _depth_estimator
    _depth_estimator_factory = factory
    _depth_estimator = None


def get_depth_estimator(midas_cache_directory: Optional[Path] = None) -> DepthEstimator:
    """Return the active depth estimator instance, creating it on first use."""
    global _depth_estimator
    if _depth_estimator is None:
        _depth_estimator = _depth_estimator_factory(midas_cache_directory)
    return _depth_estimator


class _BaseMiDasDepthEstimator(DepthEstimator):
    """Shared logic for MiDaS-backed depth estimators."""

    def __init__(
        self,
        midas_cache_directory: Optional[Path] = None,
        model_type: Literal["MiDaS_small", "DPT_Hybrid", "DPT_Large"]
        | str = config.MIDAS_MODEL_TYPE,
        midas_model: str = config.MIDAS_MODEL_REPO,
    ) -> None:
        self.region_size = config.REGION_SIZE
        self.scale_factor = config.SCALE_FACTOR
        self.update_freq = config.UPDATE_FREQ

        self.update_id = -1
        self.last_depths: list[float] = []
        self.model_type = model_type
        self.midas_model = midas_model
        self.midas_cache_directory = (
            midas_cache_directory or Path.home() / ".cache" / "torch" / "hub"
        )
        torch.hub.set_dir(str(self.midas_cache_directory))
        logger.info("Using MiDaS cache directory: %s", self.midas_cache_directory)

        self.transform = self._load_transform()

    def estimate_distance_m(
        self, frame_rgb: np.ndarray, dets: list[tuple[int, int, int, int, int, float]]
    ) -> list[float]:
        """Estimate distance in meters for each detection based on depth map."""
        self.update_id += 1
        if self.update_id % self.update_freq != 0 and len(self.last_depths) == len(
            dets
        ):
            return self.last_depths

        h, w, _ = frame_rgb.shape
        depth_map = self._predict_depth_map(frame_rgb, (h, w))
        distances = self._distances_from_depth_map(depth_map, dets)
        self.last_depths = distances
        return distances

    def _load_transform(self) -> Callable[[np.ndarray], torch.Tensor]:
        torch.hub.set_dir(str(self.midas_cache_directory))
        midas_transforms = torch.hub.load(
            self.midas_model, "transforms", trust_repo=True
        )
        if self.model_type in {"DPT_Large", "DPT_Hybrid"}:
            return midas_transforms.dpt_transform
        return midas_transforms.small_transform

    def _predict_depth_map(
        self, frame_rgb: np.ndarray, output_shape: tuple[int, int]
    ) -> np.ndarray:
        raise NotImplementedError

    def _distances_from_depth_map(
        self,
        depth_map: np.ndarray,
        dets: list[tuple[int, int, int, int, int, float]],
    ) -> list[float]:
        return calculate_distances(depth_map, dets, self.region_size, self.scale_factor)


class MiDasDepthEstimator(_BaseMiDasDepthEstimator):
    """Depth estimator backed by the PyTorch MiDaS implementation."""

    def __init__(
        self,
        midas_cache_directory: Optional[Path] = None,
        model_type: Literal["MiDaS_small", "DPT_Hybrid", "DPT_Large"]
        | str = config.MIDAS_MODEL_TYPE,
        midas_model: str = config.MIDAS_MODEL_REPO,
    ) -> None:
        super().__init__(
            midas_cache_directory=midas_cache_directory,
            model_type=model_type,
            midas_model=midas_model,
        )
        self.device = (
            torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        )

        self.depth_estimation_model = (
            torch.hub.load(midas_model, model_type, trust_repo=True)
            .to(self.device)
            .eval()
        )

    def _predict_depth_map(
        self, frame_rgb: np.ndarray, output_shape: tuple[int, int]
    ) -> np.ndarray:
        input_batch = self.transform(frame_rgb).to(self.device)
        with torch.no_grad():
            prediction = self.depth_estimation_model(input_batch)
        return resize_to_frame(prediction, output_shape)


class OnnxMiDasDepthEstimator(_BaseMiDasDepthEstimator):
    """Depth estimator backed by an exported ONNX MiDaS model."""

    def __init__(
        self,
        midas_cache_directory: Optional[Path] = None,
        model_type: Literal["MiDaS_small", "DPT_Hybrid", "DPT_Large"]
        | str = config.MIDAS_MODEL_TYPE,
        midas_model: str = config.MIDAS_MODEL_REPO,
        onnx_model_path: Optional[Path] = None,
    ) -> None:
        if ort is None:
            raise RuntimeError(
                "onnxruntime is required for DEPTH_BACKEND='onnx'. Install "
                "`onnxruntime` (CPU) or the appropriate GPU package such as "
                "`onnxruntime-gpu` or `onnxruntime-rocm`."
            )

        self.onnx_model_path = Path(
            onnx_model_path or config.MIDAS_ONNX_MODEL_PATH
        ).resolve()
        if not self.onnx_model_path.exists():
            raise FileNotFoundError(
                f"MiDaS ONNX model not found at '{self.onnx_model_path}'. "
                "Export a model via scripts/export_midas_onnx.py first."
            )

        self.providers = self._resolve_providers()
        sess_options = ort.SessionOptions()
        sess_options.enable_mem_pattern = False
        sess_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        sess_options.log_severity_level = 3
        self._session = ort.InferenceSession(
            str(self.onnx_model_path),
            providers=self.providers or None,
            sess_options=sess_options,
        )
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name

        super().__init__(
            midas_cache_directory=midas_cache_directory,
            model_type=model_type,
            midas_model=midas_model,
        )

    def _resolve_providers(self) -> list[str]:
        configured = config.MIDAS_ONNX_PROVIDERS or config.ONNX_PROVIDERS
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

    def _predict_depth_map(
        self, frame_rgb: np.ndarray, output_shape: tuple[int, int]
    ) -> np.ndarray:
        input_batch = self.transform(frame_rgb)
        _, _, h, w = input_batch.shape
        size = max(w, h)
        input_batch = torch.nn.functional.pad(input_batch, (0, size - w, 0, size - h))
        input_array = input_batch.detach().cpu().numpy().astype(np.float32)
        ort_inputs = {self._input_name: input_array}
        output = self._session.run([self._output_name], ort_inputs)[0]
        prediction = np.asarray(output)
        if prediction.ndim == 3:  # (1,H,W) -> (1,1,H,W)
            prediction = np.expand_dims(prediction, axis=1)
        return resize_to_frame(prediction, output_shape)


# Register built-in backends
register_depth_backend("torch", MiDasDepthEstimator)
register_depth_backend("onnx", OnnxMiDasDepthEstimator)

try:
    from common.core.depth_anything import DepthAnythingV2Estimator
    register_depth_backend("depth_anything_v2", DepthAnythingV2Estimator)
except ImportError:
    pass


