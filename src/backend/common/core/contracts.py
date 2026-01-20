# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass
class Detection:
    """Raw detection from object detector."""

    x1: int
    y1: int
    x2: int
    y2: int
    cls_id: int
    confidence: float
    binary_mask: np.ndarray | None = field(default=None, kw_only=True)
    """Optional binary segmentation mask (H x W) where True = object pixel, False = background."""


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

    model_type: str
    """Model type identifier (e.g., 'MiDaS_small', 'DPT_Hybrid', 'DPT_Large')."""

    def estimate_distance_m(
        self, frame_rgb: np.ndarray, detections: list[Detection]
    ) -> list[float]:
        """Return per-detection distance estimates in meters."""
        ...
