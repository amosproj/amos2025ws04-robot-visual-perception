# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

# Common detection tuple: (x1, y1, x2, y2, class_id, confidence)
Detection = tuple[int, int, int, int, int, float]


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


@runtime_checkable
class DepthEstimator(Protocol):
    """Interface for depth estimation backends."""

    def estimate_distance_m(
        self, frame_rgb: np.ndarray, detections: list[Detection]
    ) -> list[float]:
        """Return per-detection distance estimates in meters."""
        ...
