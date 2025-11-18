# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

import asyncio
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

        # numpy (BGR) → WebRTC-Frame
        # aiortc expect a video frame object
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame
