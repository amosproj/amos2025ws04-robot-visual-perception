# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import numpy as np
import torch


def resize_to_frame(
    prediction: torch.Tensor | np.ndarray, output_shape: tuple[int, int]
) -> np.ndarray:
    """Resize a depth map tensor/array to the target frame size."""
    tensor = (
        prediction
        if isinstance(prediction, torch.Tensor)
        else torch.as_tensor(prediction)
    )
    if tensor.dim() == 3:
        tensor = tensor.unsqueeze(1)
    resized = torch.nn.functional.interpolate(
        tensor,
        size=output_shape,
        mode="bicubic",
        align_corners=False,
    ).squeeze()
    return resized.cpu().numpy()


def calculate_distances(
    depth_map: np.ndarray,
    dets: list[tuple[int, int, int, int, int, float]],
    region_size: int,
    scale_factor: float,
) -> list[float]:
    """Calculate distance in meters for each detection based on depth map.

    Args:
        depth_map: The depth map (inverse depth).
        dets: List of detections (x1, y1, x2, y2, cls_id, conf).
        region_size: Size of the region to sample depth from.
        scale_factor: Factor to convert inverse depth to meters.
    """
    h, w = depth_map.shape
    distances: list[float] = []
    for x1, y1, x2, y2, _cls_id, _conf in dets:
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        half_size = region_size // 2
        x_start = max(cx - half_size, 0)
        x_end = min(cx + half_size + 1, w)
        y_start = max(cy - half_size, 0)
        y_end = min(cy + half_size + 1, h)

        region = depth_map[y_start:y_end, x_start:x_end]
        # Avoid division by zero
        depth_value = max(np.mean(region), 1e-6)
        distances.append(float(scale_factor / depth_value))
    return distances
