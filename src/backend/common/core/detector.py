# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
from typing import Optional

import cv2
import numpy as np
from ultralytics import YOLO  # type: ignore[import-untyped]

from common.config import config
from common.utils.geometry import get_detections


class _Detector:
    def __init__(self) -> None:
        """Initialize the YOLO object detector.

        Loads the YOLO model from the configured path and sets up internal
        state for asynchronous inference, caching, and distance estimation.

        Raises:
            FileNotFoundError: If the YOLO model file does not exist at the
            configured path.
        """
        model_path = config.MODEL_PATH
        self._model = YOLO(str(model_path))
        self._last_det: Optional[list[tuple[int, int, int, int, int, float]]] = None
        self._last_time: float = 0.0
        self._lock = asyncio.Lock()
        self._fov_deg = config.CAMERA_HFOV_DEG

    async def infer(
        self, frame_bgr: np.ndarray
    ) -> list[tuple[int, int, int, int, int, float]]:
        """Run YOLO inference asynchronously on a single frame.

        Performs object detection on the given BGR image using the loaded YOLO model.
        Uses simple caching to avoid repeated inference calls within 100 ms.

        Args:
            frame_bgr (np.ndarray): Input image in BGR color format (OpenCV style).

        Returns:
            list[tuple[int, int, int, int, int, float]]: A list of detections, where each
            tuple contains (x1, y1, x2, y2, class_id, confidence).
        """
        now = asyncio.get_running_loop().time()
        if self._last_det is not None and (now - self._last_time) < 0.10:
            return self._last_det

        async with self._lock:
            now = asyncio.get_running_loop().time()
            if self._last_det is not None and (now - self._last_time) < 0.10:
                return self._last_det

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            inference_results = self._model.predict(
                frame_rgb, imgsz=640, conf=0.25, verbose=False
            )

            detections = get_detections(inference_results)
            self._last_det = detections
            self._last_time = now
            return detections


_detector_instance: Optional[_Detector] = None


def _get_detector() -> _Detector:
    """Get or create the singleton detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = _Detector()
    return _detector_instance
