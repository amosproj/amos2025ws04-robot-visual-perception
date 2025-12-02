# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import cv2
import numpy as np
import torch
from pathlib import Path
from typing import Literal, Optional
from common.config import config

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


class DistanceEstimator:
    def __init__(
        self,
        model_type: Literal["MiDaS_small", "DPT_Hybrid", "DPT_Large"] = "MiDaS_small",
        midas_model: str = "intel-isl/MiDaS",
        midas_cache_directory: Optional[Path] = None,
    ) -> None:
        """Initialize the distance estimator with MiDaS depth estimation model.

        Args:
            model_type: Type of MiDaS model to use.
            midas_model: Repository identifier for the MiDaS model.
            midas_cache_directory: Custom directory for PyTorch Hub cache.
                If None, uses PyTorch's default cache location.
        """
        self.region_size = (
            config.REGION_SIZE
        )  # size of region around bbox center to sample depth
        self.scale_factor = config.SCALE_FACTOR  # empirical calibration factor
        self.update_freq = config.UPDATE_FREQ  # frames between depth updates

        self.update_id = 0
        self.last_depths: list[float] = []
        self.model_type = model_type
        self.midas_model = midas_model
        self.device = (
            torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        )

        if midas_cache_directory is not None:
            torch.hub.set_dir(str(midas_cache_directory))

        self.depth_estimation_model = (
            torch.hub.load(midas_model, model_type, trust_repo=True)
            .to(self.device)
            .eval()
        )
        # get MiDaS transforms
        midas_transforms = torch.hub.load(midas_model, "transforms", trust_repo=True)
        if model_type == "DPT_Large" or model_type == "DPT_Hybrid":
            self.transform = midas_transforms.dpt_transform
        else:
            self.transform = midas_transforms.small_transform

    def estimate_distance_m(
        self, frame_rgb: np.ndarray, dets: list[tuple[int, int, int, int, int, float]]
    ) -> list[float]:
        """Estimate distance in meters for each detection based on depth map.

        Returns list of distances in meters."""
        self.update_id += 1
        if self.update_id % self.update_freq == 0 and len(self.last_depths) == len(
            dets
        ):
            return self.last_depths
        h, w, _ = frame_rgb.shape

        input_batch = self.transform(frame_rgb).to(self.device)
        with torch.no_grad():
            prediction = self.depth_estimation_model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=(h, w),
                mode="bicubic",
                align_corners=False,
            ).squeeze()
        depth_map = prediction.cpu().numpy()
        distances = []
        for x1, y1, x2, y2, cls_id, conf in dets:
            # extract 5x5 central region of bbox and clip to image bounds
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            # Define region size (odd for symmetry)
            half_size = self.region_size // 2
            x_start = max(cx - half_size, 0)
            x_end = min(cx + half_size + 1, w)
            y_start = max(cy - half_size, 0)
            y_end = min(cy + half_size + 1, h)

            region = depth_map[y_start:y_end, x_start:x_end]
            # Use mean depth value for robustness
            depth_value = max(np.mean(region), 1e-6)  # avoid div by zero

            distances.append(float(self.scale_factor / depth_value))
        self.last_depths = distances
        return distances


estimator_instance = None


def _get_estimator_instance(
    midas_cache_directory: Optional[Path] = None,
) -> DistanceEstimator:
    """Get or create the singleton distance estimator instance.

    Args:
        midas_cache_directory: Custom directory for PyTorch Hub cache.
            Only used on first call. Subsequent calls will return the
            existing instance.

    Returns:
        The singleton distance estimator instance.
    """
    global estimator_instance
    if estimator_instance is None:
        estimator_instance = DistanceEstimator(
            midas_cache_directory=midas_cache_directory
        )
    return estimator_instance


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
