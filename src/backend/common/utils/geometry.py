# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import cv2
import numpy as np

from common.config import config
from common.core.contracts import Detection
import math

from ultralytics.engine.results import Results  # type: ignore[import-untyped]


def get_detections(
    inference_results: list[Results],
) -> list[Detection]:
    """Convert YOLO inference output into structured detection tuples.

    Args:
        inference_results (list[Results]): The list of YOLO results returned by model.predict().

    Returns:
        list[Detection]: Each detection includes optional binary_mask if available from segmentation model.
    """
    if not inference_results:
        return []

    result = inference_results[0]
    if result.boxes is None or len(result.boxes) == 0:
        return []

    bbox_coords = result.boxes.xyxy.cpu().numpy().astype(int)
    class_ids = result.boxes.cls.cpu().numpy().astype(int)
    confidences = result.boxes.conf.cpu().numpy()

    # Check if segmentation masks are available (YOLOv8-seg or similar)
    has_masks = result.masks is not None and len(result.masks) > 0
    masks = None
    if has_masks:
        # Get binary masks (H x W x N) and convert to individual masks
        try:
            masks = result.masks.data.cpu().numpy()
            # masks shape: (N, H, W) where N is number of detections
        except Exception:
            masks = None

    detections = []
    for idx, ((x1, y1, x2, y2), class_id, confidence) in enumerate(
        zip(bbox_coords, class_ids, confidences)
    ):
        # Extract individual mask if available
        binary_mask = None
        if masks is not None and idx < len(masks):
            # Convert mask to boolean array (0.5 threshold for confidence)
            mask_data = masks[idx]
            binary_mask = (mask_data > 0.5).astype(np.uint8)

        detection = Detection(
            x1=int(x1),
            y1=int(y1),
            x2=int(x2),
            y2=int(y2),
            cls_id=int(class_id),
            confidence=float(confidence),
            binary_mask=binary_mask,
        )
        detections.append(detection)

    return detections


def draw_detections(
    frame: np.ndarray,
    detections: list[Detection],
    distances_m: list[float],
) -> np.ndarray:
    """Draw bounding boxes and annotate distance plus camera-space XYZ.

    Args:
        frame: Input frame as a NumPy array in RGB format.
        detections: List of detections.
        distances_m: Per-detection distance estimates (meters), aligned with detections.

    Returns:
        Frame with bounding boxes and annotated labels drawn on it.
    """
    h, w = frame.shape[:2]
    fx, fy, cx, cy = compute_camera_intrinsics(w, h)

    # Draw bounding boxes and labels for each detection
    for det, dist_m in zip(detections, distances_m):
        px, py, pz = unproject_bbox_center_to_camera(
            det.x1, det.y1, det.x2, det.y2, dist_m, fx, fy, cx, cy
        )
        label = f"{det.cls_id}:{det.confidence:.2f} {dist_m:.1f}m X:{px:.2f} Y:{py:.2f} Z:{pz:.2f}"
        # Draw bounding box
        cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), (0, 255, 0), 2)

        # Draw label text
        cv2.putText(
            frame,
            label,
            (det.x1, max(0, det.y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            3,
            cv2.LINE_AA,
        )

    return frame


def compute_camera_intrinsics(
    width: int, height: int
) -> tuple[float, float, float, float]:
    """Return fx, fy, cx, cy using overrides or FOV-based defaults."""
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
