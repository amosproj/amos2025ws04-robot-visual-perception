# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

import asyncio
import os
import threading
from typing import Optional
import cv2
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame


class VideoFileTrack(VideoStreamTrack):
    """
    WebRTC video track that streams frames from an MP4 file.
    Loops the video when it reaches the end.
    """

    kind = "video"

    def __init__(self, video_path: str) -> None:
        super().__init__()
        self.video_path = video_path
        self.cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._open_video()

    def _open_video(self) -> None:
        """Open the video file."""
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {self.video_path}")

    def _read_frame(self) -> Optional[np.ndarray]:
        """Read a frame from the video file, loop if at end."""
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
        # get next WebRTC timestamp
        pts, time_base = await self.next_timestamp()

        # Read frame in executor to avoid blocking
        loop = asyncio.get_running_loop()
        with self._lock:
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
