# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from common.config import config
from common.core.contracts import Detection
import math

from ultralytics.engine.results import Results  # type: ignore[import-untyped]


def get_detections(
    inference_results: list[Results],
) -> list[Detection]:
    """Convert YOLO prediction output into a flat list of Detection objects.

    Args:
        inference_results: Output of `model.predict(...)` (only the first item is used).

    Returns:
        Detections with (x1, y1, x2, y2, cls_id, confidence). Empty if none found.
    """
    if not inference_results:
        return []

    result = inference_results[0]
    if result.boxes is None or len(result.boxes) == 0:
        return []

    bbox_coords = result.boxes.xyxy.cpu().numpy().astype(int)
    class_ids = result.boxes.cls.cpu().numpy().astype(int)
    confidences = result.boxes.conf.cpu().numpy()

    detections = [
        Detection(
            x1=int(x1),
            y1=int(y1),
            x2=int(x2),
            y2=int(y2),
            cls_id=int(class_id),
            confidence=float(confidence),
        )
        for (x1, y1, x2, y2), class_id, confidence in zip(
            bbox_coords, class_ids, confidences
        )
    ]

    return detections


def compute_camera_intrinsics(
    width: int, height: int
) -> tuple[float, float, float, float]:
    """Compute camera intrinsic parameters (fx, fy, cx, cy).

    Calculates focal lengths and principal point using config values or FOV-based
    fallbacks. Uses pinhole camera model: x_pixel = fx * (X/Z) + cx

    Args:
        width: Image width in pixels (min 1)
        height: Image height in pixels (min 1)

    Returns:
        Tuple of (fx, fy, cx, cy) in pixels where:
            fx, fy: Focal lengths
            cx, cy: Principal point (defaults to image center)

    Priority order:
        1. Explicit config (CAMERA_FX, CAMERA_FY, CAMERA_CX, CAMERA_CY)
        2. FOV-based calculation (CAMERA_FOV_X_DEG, CAMERA_FOV_Y_DEG)
        3. Defaults (cx = width/2, cy = height/2, fy = fx)

    Note:
        If no fx/fy or FOV provided, focal lengths will be 0.0
    """
    fx = getattr(config, "CAMERA_FX", 0.0)
    fy = getattr(config, "CAMERA_FY", 0.0)
    cx = getattr(config, "CAMERA_CX", 0.0)
    cy = getattr(config, "CAMERA_CY", 0.0)
    fov_x = getattr(config, "CAMERA_FOV_X_DEG", 0.0)
    fov_y = getattr(config, "CAMERA_FOV_Y_DEG", 0.0)

    width = max(1, int(width))
    height = max(1, int(height))

    # Derive fx/fy from field of view when not explicitly provided
    if fx <= 0 and fov_x > 0:
        fx = width / (2.0 * math.tan(math.radians(fov_x) / 2.0))
    if fy <= 0:
        if fov_y > 0:
            fy = height / (2.0 * math.tan(math.radians(fov_y) / 2.0))
        else:
            fy = fx

    # Principal point defaults to image center
    if cx <= 0:
        cx = width / 2.0
    if cy <= 0:
        cy = height / 2.0

    return float(fx), float(fy), float(cx), float(cy)


def unproject_bbox_center_to_camera(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    depth_m: float,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
) -> tuple[float, float, float]:
    """Map a bounding box center and depth to camera-space XYZ (meters)."""
    if depth_m <= 0 or fx <= 0 or fy <= 0:
        return 0.0, 0.0, float(max(depth_m, 0.0))

    u = (x1 + x2) / 2.0
    v = (y1 + y2) / 2.0

    x = (u - cx) * depth_m / fx
    y = (v - cy) * depth_m / fy
    return float(x), float(y), float(depth_m)


def calculate_iou(
    box1: tuple[float, float, float, float], box2: tuple[float, float, float, float]
) -> float:
    """Calculate Intersection over Union (IoU) between two bounding boxes.

    Args:
        box1: (x1, y1, x2, y2) coordinates
        box2: (x1, y1, x2, y2) coordinates

    Returns:
        IoU value between 0.0 and 1.0
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # Calculate intersection
    inter_x1 = max(x1_1, x1_2)
    inter_y1 = max(y1_1, y1_2)
    inter_x2 = min(x2_1, x2_2)
    inter_y2 = min(y2_1, y2_2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    # Calculate union
    box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = box1_area + box2_area - inter_area

    if union_area == 0:
        return 0.0

    return inter_area / union_area


def normalize_bbox_coordinates(
    x1: float, y1: float, x2: float, y2: float, frame_width: int, frame_height: int
) -> tuple[float, float, float, float]:
    """Normalize bounding box coordinates to [0, 1] range.

    Args:
        x1, y1, x2, y2: Box coordinates in pixels
        frame_width, frame_height: Frame dimensions

    Returns:
        Tuple of (norm_x, norm_y, norm_width, norm_height)
    """
    box_w = max(0.0, float(x2 - x1))
    box_h = max(0.0, float(y2 - y1))

    if box_w <= 0 or box_h <= 0:
        return 0.0, 0.0, 0.0, 0.0

    norm_x = max(0.0, min(1.0, x1 / frame_width))
    norm_y = max(0.0, min(1.0, y1 / frame_height))
    norm_w = max(0.0, min(1.0, box_w / frame_width))
    norm_h = max(0.0, min(1.0, box_h / frame_height))

    return norm_x, norm_y, norm_w, norm_h
