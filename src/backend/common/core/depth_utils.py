# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import numpy as np
import torch

from common.core.contracts import Detection


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
    dets: list[Detection],
    region_size: int,
    scale_factor: float,
) -> list[float]:
    """Calculate distance in meters for each detection based on depth map.

    Args:
        depth_map: The depth map (inverse depth).
        dets: List of detections.
        region_size: Size of the region to sample depth from.
        scale_factor: Factor to convert inverse depth to meters.
    """
    h, w = depth_map.shape
    distances: list[float] = []

    for det in dets:
        # If binary mask is available, prefer sampling from mask region
        if det.binary_mask is not None:
            depth_value = _estimate_depth_from_mask(depth_map, det)
        else:
            # Fall back to bounding box center region
            depth_value = _estimate_depth_from_bbox(depth_map, det, region_size, w, h)

        distances.append(float(scale_factor / depth_value))

    return distances


def _estimate_depth_from_mask(
    depth_map: np.ndarray,
    det: Detection,
) -> float:
    """Extract depth value from mask region.

    Uses the mask to select only object pixels and calculates mean depth
    from the depth map, weighted by mask confidence.
    """
    # print("Estimating depth from mask")
    mask = det.binary_mask
    if mask is None or mask.size == 0:
        return 1e-6

    # Resize mask to match depth_map size if necessary
    h, w = depth_map.shape
    mask_h, mask_w = mask.shape

    if (mask_h, mask_w) != (h, w):
        # Resize mask using nearest neighbor to preserve binary values
        import cv2

        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)

    # Extract depth values only where mask is True
    mask_array = np.asarray(mask)
    mask_pixels = mask_array.astype(np.bool_)
    if not mask_pixels.any():
        return 1e-6

    masked_depth = depth_map[mask_pixels]

    # Use median to be robust against outliers
    depth_value = max(np.median(masked_depth), 1e-6)
    return depth_value


def _estimate_depth_from_bbox(
    depth_map: np.ndarray,
    det: Detection,
    region_size: int,
    w: int,
    h: int,
) -> float:
    """Extract depth value from bounding box region.

    Samples depth from a small region around the center of the bounding box.
    """
    # print("Estimating depth from bbox")
    cx = int((det.x1 + det.x2) / 2)
    cy = int((det.y1 + det.y2) / 2)
    half_size = region_size // 2

    x_start = max(cx - half_size, 0)
    x_end = min(cx + half_size + 1, w)
    y_start = max(cy - half_size, 0)
    y_end = min(cy + half_size + 1, h)

    region = depth_map[y_start:y_end, x_start:x_end]
    depth_value = max(np.mean(region), 1e-6)
    return depth_value
