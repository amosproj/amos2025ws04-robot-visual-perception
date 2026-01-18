# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import torch

from common.typing import Detection


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


def calculate_region_bounds(
    center_x: int,
    center_y: int,
    region_size: int,
    frame_width: int,
    frame_height: int,
) -> tuple[int, int, int, int]:
    """Calculate bounded region coordinates for depth sampling.

    Returns region that is clamped to frame boundaries to avoid out-of-bounds access.

    Args:
        center_x: X coordinate of region center
        center_y: Y coordinate of region center
        region_size: Size of square region to extract
        frame_width: Width of the frame
        frame_height: Height of the frame

    Returns:
        Tuple of (x_start, x_end, y_start, y_end) in pixels, clamped to frame bounds
    """
    half_size = region_size // 2
    x_start = max(center_x - half_size, 0)
    x_end = min(center_x + half_size + 1, frame_width)
    y_start = max(center_y - half_size, 0)
    y_end = min(center_y + half_size + 1, frame_height)

    return x_start, x_end, y_start, y_end


def bbox_center(x1: int, y1: int, x2: int, y2: int) -> tuple[int, int]:
    """Calculate the center point of a bounding box.

    Args:
        x1, y1: Top-left corner
        x2, y2: Bottom-right corner

    Returns:
        Tuple of (center_x, center_y) as integers
    """
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def inverse_depth_to_distance(
    inverse_depth: float,
    scale_factor: float,
    min_depth: float = 1e-6,
) -> float:
    """Convert inverse depth to distance in meters.

    Inverse depth models (like MiDaS) output values where larger numbers
    mean closer objects. This converts to metric distance.

    Args:
        inverse_depth: Inverse depth value from model
        scale_factor: Calibration factor to convert to meters
        min_depth: Minimum depth to avoid division by zero

    Returns:
        Distance in meters
    """
    depth_value = max(inverse_depth, min_depth)
    return float(scale_factor / depth_value)


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
        cx, cy = bbox_center(det.x1, det.y1, det.x2, det.y2)
        x_start, x_end, y_start, y_end = calculate_region_bounds(
            cx, cy, region_size, w, h
        )

        region = depth_map[y_start:y_end, x_start:x_end]
        inverse_depth = np.mean(region)
        distance = inverse_depth_to_distance(inverse_depth, scale_factor)
        distances.append(distance)

    return distances
