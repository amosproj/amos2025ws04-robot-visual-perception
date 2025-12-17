# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

import asyncio
import os
import threading
import cv2
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

from common.core.camera import _shared_cam


class CameraVideoTrack(VideoStreamTrack):
    """
    WebRTC video track that streams raw camera frames.
    """

    kind = "video"

    def __init__(self) -> None:
        super().__init__()

    async def recv(self) -> VideoFrame:
        """Return the next raw camera frame as WebRTC VideoFrame."""

        # get next WebRTC timestamp
        pts, time_base = await self.next_timestamp()

        # wait for new frame from shared camera
        frame = None
        tries = 0
        while frame is None:
            frame = _shared_cam.latest()  # RAW Frame: BGR, numpy
            if frame is not None:
                break

            tries += 1
            # wait for a bit if camera is not sending
            await asyncio.sleep(0.005 if tries < 100 else 0.008)
            if tries >= 100:
                tries = 0

        # Horizontally flip the WebCam
        frame = frame[:, ::-1]

        # numpy (BGR) → WebRTC-Frame
        # aiortc expect a video frame object
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame


class VideoFileTrack(VideoStreamTrack):
    """
    WebRTC video track that streams frames from an MP4 file.
    Loops the video when it reaches the end.
    """

    kind = "video"

    def __init__(self, video_path: str) -> None:
        super().__init__()
        self.video_path = video_path
        self.cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()
        self._video_fps: float = 30.0  # Default FPS
        self._open_video()

    def _open_video(self) -> None:
        """Open the video file and extract FPS."""
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {self.video_path}")

        # Get the video's native FPS
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            self._video_fps = fps

    def _read_frame(self) -> np.ndarray | None:
        """Read a frame from the video file, loop if at end."""
        with self._lock:
            if self.cap is None:
                return None

            ret, frame = self.cap.read()

            # If we've reached the end of the video, loop back to the beginning
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()

            if not ret:
                return None

            return frame

    async def recv(self) -> VideoFrame:
        """Return the next video frame as WebRTC VideoFrame."""
        # Calculate delay to match video's native FPS
        frame_duration = 1.0 / self._video_fps
        await asyncio.sleep(frame_duration)

        # Get next WebRTC timestamp with proper time_base for the video FPS
        pts, time_base = await self.next_timestamp()

        # Read frame in executor to avoid blocking
        loop = asyncio.get_running_loop()
        frame = await loop.run_in_executor(None, self._read_frame)

        if frame is None:
            raise RuntimeError("Failed to read frame from video file")

        # numpy (BGR) → WebRTC-Frame
        # aiortc expects a video frame object
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

    def __del__(self) -> None:
        """Clean up video capture on deletion."""
        if self.cap is not None:
            self.cap.release()
