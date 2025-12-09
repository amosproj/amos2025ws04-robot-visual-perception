# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

import numpy as np


def xywh_to_xyxy(xywh: np.ndarray) -> np.ndarray:
    """Convert bounding boxes from center-size format to corner format."""
    xyxy = np.zeros_like(xywh)
    xyxy[:, 0] = xywh[:, 0] - xywh[:, 2] / 2
    xyxy[:, 1] = xywh[:, 1] - xywh[:, 3] / 2
    xyxy[:, 2] = xywh[:, 0] + xywh[:, 2] / 2
    xyxy[:, 3] = xywh[:, 1] + xywh[:, 3] / 2
    return xyxy


def non_maximum_supression(
    boxes: np.ndarray, scores: np.ndarray, iou_thres: float
) -> list[int]:
    """Perform non-maximum suppression to remove overlapping bounding boxes."""
    if boxes.size == 0:
        return []
    idxs = scores.argsort()[::-1]
    keep: list[int] = []
    while len(idxs) > 0:
        i = idxs[0]
        keep.append(i)
        if len(idxs) == 1:
            break
        ious = _intersection_over_union(boxes[i], boxes[idxs[1:]])
        idxs = idxs[1:][ious <= iou_thres]
    return keep


def _intersection_over_union(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    """Compute the intersection-over-union between one box and multiple boxes."""
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


def lerp(val1: float, val2: float, t: float) -> float:
    """Linear interpolation between two values.

    Args:
        value1: Start value
        value2: End value
        t: Interpolation factor (0.0 = value1, 1.0 = value2)

    Returns:
        Interpolated value
    """
    return val1 + (val2 - val1) * t


def lerp_int(value1: int, value2: int, t: float) -> int:
    """Linear interpolation between two integer values, rounded to int.

    Args:
        value1: Start value (int)
        value2: End value (int)
        t: Interpolation factor (0.0 = value1, 1.0 = value2)

    Returns:
        Interpolated value rounded to int
    """
    return int(round(lerp(value1, value2, t)))


def calculate_interpolation_factor(
    frame1: int, frame2: int, target_frame: int, clamp_max: float = 1.5
) -> float:
    """Calculate interpolation factor t between two frames.

    Args:
        frame1: Start frame ID
        frame2: End frame ID
        target_frame: Target frame ID to interpolate for
        clamp_max: Maximum value for t (default 1.5 for extrapolation)

    Returns:
        Interpolation factor t (0.0 = frame1, 1.0 = frame2, >1.0 = extrapolation)
    """
    if frame1 == frame2:
        return 0.0
    t = (target_frame - frame1) / (frame2 - frame1)
    return max(0.0, min(clamp_max, t))
