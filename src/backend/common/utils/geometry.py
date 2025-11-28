# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import cv2
import numpy as np

from common.config import config
import math

from ultralytics.engine.results import Results  # type: ignore[import-untyped]


def get_detections(
    inference_results: list[Results],
) -> list[tuple[int, int, int, int, int, float]]:
    """Convert YOLO inference output into structured detection tuples.

    Args:
        inference_results (list[Results]): The list of YOLO results returned by model.predict().

    Returns:
        list[tuple[int, int, int, int, int, float]]: Each tuple is (x1, y1, x2, y2, class_id, confidence).
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
        (int(x1), int(y1), int(x2), int(y2), int(class_id), float(confidence))
        for (x1, y1, x2, y2), class_id, confidence in zip(
            bbox_coords, class_ids, confidences
        )
    ]

    return detections


def draw_detections(
    frame: np.ndarray,
    detections: list[tuple[int, int, int, int, int, float]],
    distances_m: list[float],
) -> np.ndarray:
    """Draw bounding boxes and distance labels for detected objects on a frame.

    For each detection, computes the estimated distance using the pinhole
    camera model, then overlays a bounding box and text label with class ID,
    confidence, and distance.

    Args:
        frame: Input frame as a NumPy array in RGB format.
        detections: List of detections as (x1, y1, x2, y2, class_id, confidence).
        fov_deg: Horizontal field of view of the camera in degrees.
        obj_width_m: Assumed real-world width of the detected object in meters.
        scale: Additional scaling factor applied to the computed distance.

    Returns:
        Frame with bounding boxes and annotated labels drawn on it.
    """
    h, w = frame.shape[:2]
    fx, fy, cx, cy = compute_camera_intrinsics(w, h)

    # Draw bounding boxes and labels for each detection
    for (x1, y1, x2, y2, cls_id, conf), dist_m in zip(detections, distances_m):
        px, py, pz = unproject_bbox_center_to_camera(
            x1, y1, x2, y2, dist_m, fx, fy, cx, cy
        )
        label = f"{cls_id}:{conf:.2f} {dist_m:.1f}m X:{px:.2f} Y:{py:.2f} Z:{pz:.2f}"
        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Draw label text
        cv2.putText(
            frame,
            label,
            (x1, max(0, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            3,
            cv2.LINE_AA,
        )

    return frame


def compute_camera_intrinsics(width: int, height: int) -> tuple[float, float, float, float]:
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
    x1: int, y1: int, x2: int, y2: int, depth_m: float, fx: float, fy: float, cx: float, cy: float
) -> tuple[float, float, float]:
    """Map a bounding box center and depth to camera-space XYZ (meters)."""
    if depth_m <= 0 or fx <= 0 or fy <= 0:
        return 0.0, 0.0, float(max(depth_m, 0.0))

    u = (x1 + x2) / 2.0
    v = (y1 + y2) / 2.0

    x = (u - cx) * depth_m / fx
    y = (v - cy) * depth_m / fy
    return float(x), float(y), float(depth_m)
