# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
from typing import Optional

import cv2
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

from common.core.camera import _shared_cam
from common.core.detector import _get_detector
from common.utils.video import numpy_to_video_frame
from common.utils.geometry import draw_detections, _get_estimator_distance


class CameraVideoTrack(VideoStreamTrack):
    """
    WebRTC video track that streams camera frames with YOLO detection overlays.

    Captures frames from the shared local camera, performs YOLO-based object
    detection, draws bounding boxes and distance labels, and sends annotated
    frames to connected clients.
    """

    kind = "video"

    def __init__(self) -> None:
        """Initialize a new camera video track."""
        super().__init__()

    async def recv(self) -> VideoFrame:
        """Capture, process, and return the next camera frame.

        Retrieves the latest frame from the shared camera, performs YOLO detection,
        overlays bounding boxes and distance labels, and returns it as a WebRTC
        VideoFrame.

        Returns:
            VideoFrame: The processed frame with detection overlays.
        """
        pts, time_base = await self.next_timestamp()

        frame: Optional[np.ndarray] = None
        tries = 0
        while frame is None:
            frame = _shared_cam.latest()
            if frame is not None:
                break
            tries += 1
            if tries >= 100:
                await asyncio.sleep(0.008)
                tries = 0
            else:
                await asyncio.sleep(0.005)

        # Flip frame for mirror effect
        overlay = cv2.flip(frame, 1)
        # Convert BGR to RGB
        overlay = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)

        # Run YOLO detection on flipped frame
        detections = await _get_detector().infer(overlay)
        # Estimate distances for each detection
        distances_m = _get_estimator_distance().estimate_distance_m(overlay, detections)

        overlay = draw_detections(
            overlay,
            detections,
            distances_m
        )
        return numpy_to_video_frame(overlay, pts, time_base)
