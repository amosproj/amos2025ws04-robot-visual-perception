# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
from typing import Optional

import cv2
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

from .camera import _shared_cam
from .detector import _detector
from .webrtc_utils import _send_meta


class CameraVideoTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self) -> None:
        super().__init__()

    async def recv(self) -> VideoFrame:
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

        dets = await _detector.infer(frame)

        overlay = cv2.flip(frame, 1)
        h, w = overlay.shape[:2]
        meta: list[dict[str, float | int | str]] = []
        for x1, y1, x2, y2, cls_id, conf in dets:
            mx1 = w - x2
            mx2 = w - x1
            dist_m = _detector.estimate_distance_m((x1, y1, x2, y2), w)
            cv2.rectangle(overlay, (mx1, y1), (mx2, y2), (0, 255, 0), 2)
            label = f"{cls_id}:{conf:.2f} {dist_m:.1f}m"
            cv2.putText(
                overlay,
                label,
                (mx1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 255, 0),
                3,
                cv2.LINE_AA,
            )
            meta.append(
                {
                    "cls": int(cls_id),
                    "conf": float(conf),
                    "x1": int(mx1),
                    "y1": int(y1),
                    "x2": int(mx2),
                    "y2": int(y2),
                    "dist_m": float(dist_m),
                }
            )

        _send_meta(meta)

        rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB).astype(np.uint8)
        video_frame = VideoFrame.from_ndarray(rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame
