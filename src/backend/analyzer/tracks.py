# SPDX-FileCopyrightText: 2025 robot-visual-perception
# SPDX-License-Identifier: MIT

import json
import time
import asyncio
from typing import Optional, cast

import cv2
import numpy as np
from aiortc import VideoStreamTrack, RTCDataChannel
from aiortc.mediastreams import MediaStreamTrack
from av import VideoFrame
from common.utils.video import numpy_to_video_frame
from common.core.detector import _get_detector
from common.config import config
from common.utils.geometry import (
    _get_estimator_instance,
    compute_camera_intrinsics,
    draw_detections,
    unproject_bbox_center_to_camera,
)


class AnalyzedVideoTrack(VideoStreamTrack):
    kind = "video"

    def __init__(
        self, source: MediaStreamTrack, pc_id: int, meta_channel: Optional[RTCDataChannel]
    ) -> None:
        super().__init__()
        self._source = source
        self._pc_id = pc_id
        self._meta_channel = meta_channel

        # Cache for latest processed data
        self._latest_frame: Optional[np.ndarray] = None
        self._last_overlay: Optional[np.ndarray] = None
        self._last_detections: Optional[list[tuple[int, int, int, int, int, float]]] = (
            None
        )
        self._last_distances: Optional[list[float]] = None
        self._frame_counter = 0
        self._intrinsics_logged = False

        # Frequency limit for YOLO/overlay processing
        self._infer_interval = 0.12
        self._last_infer_time = 0.0

        # Lock for parallel inference - use asyncio.Lock for async operations
        self._infer_lock = asyncio.Lock()

        # Background task management
        self._inference_task: Optional[asyncio.Task[None]] = None
        self._running = False

        # Start background task
        self._start_inference_loop()

    def _start_inference_loop(self) -> None:
        """Start the background inference task."""
        if self._inference_task is None or self._inference_task.done():
            self._running = True
            self._inference_task = asyncio.create_task(self._inference_loop())

    async def _inference_loop(self) -> None:
        """Background task for running inference."""
        detector = _get_detector()
        estimator = _get_estimator_instance()

        while self._running:
            frame = self._latest_frame
            if frame is not None:
                now = time.time()
                if now - self._last_infer_time >= self._infer_interval:
                    # Use async lock for async operations
                    async with self._infer_lock:
                        try:
                            # Use the detector's infer method for asynchronous inference
                            detections = await detector.infer(frame)

                            # Estimate distances using the estimator
                            distances = await asyncio.to_thread(
                                estimator.estimate_distance_m, frame, detections
                            )

                            # Update detections and distances - these will be used until new ones are available
                            self._last_detections = detections
                            self._last_distances = distances
                            self._send_metadata(frame, detections, distances)
                            self._last_infer_time = now
                        except Exception as e:
                            print("Inference error:", e)
            await asyncio.sleep(0.005)

    async def recv(self) -> VideoFrame:
        frame = await self._source.recv()
        video_frame = cast(VideoFrame, frame)

        # Process this frame (no dropping)
        base = video_frame.to_ndarray(format="bgr24")
        rgb = cv2.cvtColor(base, cv2.COLOR_BGR2RGB)

        # Always store for background task
        self._latest_frame = rgb

        # Apply overlay with last available detections
        overlay = rgb.copy()
        # Use async lock when accessing shared detection data
        if self._last_detections is not None and self._last_distances is not None:
            overlay = draw_detections(
                overlay, self._last_detections, self._last_distances
            )

        return numpy_to_video_frame(overlay, video_frame.pts, video_frame.time_base)

    async def stop(self) -> None:  # type: ignore
        """Stop the track and clean up resources."""
        self._running = False

        # Cancel the inference task if it exists
        if self._inference_task is not None and not self._inference_task.done():
            self._inference_task.cancel()
            try:
                await self._inference_task
            except asyncio.CancelledError:
                pass  # Task cancellation is expected

        # Clean up resources
        self._latest_frame = None
        self._last_detections = None
        self._last_distances = None

        # Call parent stop method - don't await since it returns None
        super().stop()

    def __del__(self) -> None:
        """Ensure cleanup when the object is destroyed."""
        if self._running:
            self._running = False
            if self._inference_task is not None and not self._inference_task.done():
                self._inference_task.cancel()

    def _send_metadata(
        self,
        frame_rgb: np.ndarray,
        detections: list[tuple[int, int, int, int, int, float]],
        distances: list[float],
    ) -> None:
        """Send a metadata payload over the WebRTC data channel."""
        channel = self._meta_channel
        if channel is None or getattr(channel, "readyState", "") != "open":
            return

        try:
            payload = self._build_metadata_payload(frame_rgb, detections, distances)
            channel.send(json.dumps(payload))
        except Exception as exc:
            print(f"Metadata send failed for pc {self._pc_id}: {exc}")

    def _build_metadata_payload(
        self,
        frame_rgb: np.ndarray,
        detections: list[tuple[int, int, int, int, int, float]],
        distances: list[float],
    ) -> dict:
        """Construct metadata message with normalized boxes and camera-space XYZ."""
        h, w = frame_rgb.shape[:2]
        fx, fy, cx, cy = compute_camera_intrinsics(w, h)

        if not self._intrinsics_logged and getattr(config, "LOG_INTRINSICS", False):
            print(
                f"[pc {self._pc_id}] intrinsics fx={fx:.2f} fy={fy:.2f} cx={cx:.2f} cy={cy:.2f} (frame {w}x{h})"
            )
            self._intrinsics_logged = True

        det_payload = []
        for idx, ((x1, y1, x2, y2, cls_id, conf), dist_m) in enumerate(
            zip(detections, distances)
        ):
            box_w = max(0.0, float(x2 - x1))
            box_h = max(0.0, float(y2 - y1))
            if box_w <= 0 or box_h <= 0:
                continue

            norm_x = max(0.0, min(1.0, x1 / w))
            norm_y = max(0.0, min(1.0, y1 / h))
            norm_w = max(0.0, min(1.0, box_w / w))
            norm_h = max(0.0, min(1.0, box_h / h))

            pos_x, pos_y, pos_z = unproject_bbox_center_to_camera(
                x1, y1, x2, y2, dist_m, fx, fy, cx, cy
            )

            det_payload.append(
                {
                    "id": f"{self._pc_id}-{self._frame_counter}-{idx}",
                    "label": str(cls_id),
                    "confidence": float(conf),
                    "box": {
                        "x": norm_x,
                        "y": norm_y,
                        "width": norm_w,
                        "height": norm_h,
                    },
                    "distance": float(dist_m),
                    "position": {"x": pos_x, "y": pos_y, "z": pos_z},
                }
            )

        payload = {
            "timestamp": int(time.time() * 1000),
            "frameId": self._frame_counter,
            "detections": det_payload,
        }
        self._frame_counter += 1
        return payload
