# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import cv2
import numpy as np
import torch

from common.typing import Detection
from common.utils.detection import bbox_center


def resize_to_frame(
    prediction: torch.Tensor | np.ndarray, output_shape: tuple[int, int]
) -> np.ndarray:
    """Resize a depth map tensor/array to the target frame size.

    Uses bicubic interpolation to resize the depth prediction to match
    the original video frame dimensions.

    Args:
        prediction: Depth map from model, either as torch.Tensor or np.ndarray.
            Expected shape is (H, W), (1, H, W), or (1, 1, H, W).
        output_shape: Target (height, width) to resize to.

    Returns:
        Resized depth map as a numpy array with shape (height, width).
    """
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
            inverse_depth = _estimate_depth_from_mask(depth_map, det)
        else:
            # Fall back to bounding box center region
            inverse_depth = _estimate_depth_from_bbox(depth_map, det, region_size, w, h)

        distance = _inverse_depth_to_distance(inverse_depth, scale_factor)
        distances.append(distance)

    return distances


def _inverse_depth_to_distance(
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


def _estimate_depth_from_mask(
    depth_map: np.ndarray,
    det: Detection,
) -> float:
    # """Extract depth value from mask region.

    # Uses the mask to select only object pixels and calculates mean depth
    # from the depth map, weighted by mask confidence.
    # """
    mask = det.binary_mask
    if mask is None or mask.size == 0:
        return 1e-6

    # Resize mask to match depth_map size if necessary
    h, w = depth_map.shape
    mask_h, mask_w = mask.shape

    if (mask_h, mask_w) != (h, w):
        # Resize mask using nearest neighbor to preserve binary values
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)

    # Extract depth values only where mask is True
    mask_array = np.asarray(mask)
    mask_pixels = mask_array.astype(np.bool_)
    if not mask_pixels.any():
        return 1e-6

    masked_depth = depth_map[mask_pixels]

    # Use median to be robust against outliers
    depth_value = max(np.median(masked_depth), 1e-6)
    return float(depth_value)


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
    cx, cy = bbox_center(det.x1, det.y1, det.x2, det.y2)
    x_start, x_end, y_start, y_end = _calculate_region_bounds(cx, cy, region_size, w, h)
    region = depth_map[y_start:y_end, x_start:x_end]
    inverse_depth = np.mean(region)

    return float(inverse_depth)


def _calculate_region_bounds(
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
