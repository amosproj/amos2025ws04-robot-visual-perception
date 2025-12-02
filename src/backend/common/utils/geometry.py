# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import cv2
import numpy as np

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
    _, w = frame.shape[:2]

    # Draw bounding boxes and labels for each detection
    for (x1, y1, x2, y2, cls_id, conf), dist_m in zip(detections, distances_m):
        # Estimate distance and create label
        label = f"{cls_id}:{conf:.2f} {dist_m:.1f}m"
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
