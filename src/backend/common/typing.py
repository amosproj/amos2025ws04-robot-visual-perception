# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from dataclasses import dataclass, field

import numpy as np
from typing_extensions import TypedDict


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


# Strict typing for Metadata message because it's coupled with the frontend
Box = TypedDict("Box", {"x": float, "y": float, "width": float, "height": float})
Pos3D = TypedDict("Pos3D", {"x": float, "y": float, "z": float})


class DetectionPayload(TypedDict):
    """Detection data sent to the frontend via WebSocket metadata payload."""

    box: Box
    position: Pos3D
    label: int
    label_text: str
    confidence: float
    distance: float
    interpolated: bool
