# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from typing import Protocol, runtime_checkable

import numpy as np

from common.typing import Detection


@runtime_checkable
class ObjectDetectionBackend(Protocol):
    """Synchronous interface implemented by model-specific adapters."""

    def predict(self, frame_rgb: np.ndarray) -> list[Detection]:
        """Run inference on an RGB frame and return parsed detections."""
        ...


@runtime_checkable
class ObjectDetector(Protocol):
    """Asynchronous detector wrapper used by the analyzer pipeline."""

    async def infer(self, frame_rgb: np.ndarray) -> list[Detection]:
        """Run inference with caching/throttling and return detections."""
        ...

    async def infer_preprocessed(
        self,
        resized_rgb: np.ndarray,
        ratio: float,
        dwdh: tuple[float, float],
        original_hw: tuple[int, int],
    ) -> list[Detection]:
        """Run inference on a preprocessed frame when supported."""
        ...


@runtime_checkable
class DepthEstimator(Protocol):
    """Interface for depth estimation backends."""

    model_type: str
    """Model type identifier (e.g., 'MiDaS_small', 'DPT_Hybrid', 'DPT_Large')."""

    def estimate_distance_m(
        self, frame_rgb: np.ndarray, detections: list[Detection]
    ) -> list[float]:
        """Return per-detection distance estimates in meters."""
        ...

    def estimate_distance_m_preprocessed(
        self,
        resized_rgb: np.ndarray,
        detections: list[Detection],
        output_shape: tuple[int, int],
    ) -> list[float]:
        """Return distances using a preprocessed frame when supported."""
        ...
