# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

import time
import asyncio
from typing import Optional, cast

import cv2
import numpy as np
from aiortc import VideoStreamTrack
from aiortc.mediastreams import MediaStreamTrack
from av import VideoFrame
from common.utils.video import numpy_to_video_frame
from common.core.detector import _get_detector
from common.utils.geometry import _get_estimator_instance, draw_detections


class AnalyzedVideoTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, source: MediaStreamTrack, pc_id: int) -> None:
        super().__init__()
        self._source = source
        self._pc_id = pc_id

        # Cache for latest processed data
        self._latest_frame: Optional[np.ndarray] = None
        self._last_overlay: Optional[np.ndarray] = None
        self._last_detections: Optional[list[tuple[int, int, int, int, int, float]]] = (
            None
        )
        self._last_distances: Optional[list[float]] = None

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

    async def _stop_async(self) -> None:
        """Async cleanup for stopping the track. Can be scheduled from a sync stop()."""
        # Ensure background loop stops
        self._running = False

        # Cancel the inference task if it exists and wait for its cancellation
        if self._inference_task is not None and not self._inference_task.done():
            self._inference_task.cancel()
            try:
                await self._inference_task
            except asyncio.CancelledError:
                pass  # Task cancellation is expected

        # Clean up resources
        self._inference_task = None
        self._latest_frame = None
        self._last_detections = None
        self._last_distances = None

    def stop(self) -> None:  # type: ignore
        """Synchronous stop called by aiortc; schedule async cleanup.

        aiortc expects VideoStreamTrack.stop to be a regular (non-async) method.
        Schedule the async cleanup on the running loop if available; otherwise
        run a temporary loop to perform cleanup synchronously.
        """
        # Mark as not running immediately so background loop quickly exits
        self._running = False

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Schedule background cleanup without awaiting so stop remains sync
            try:
                asyncio.create_task(self._stop_async())
            except Exception:
                # Fallback: run synchronously if scheduling failed
                loop.run_until_complete(self._stop_async())
        else:
            # No running loop available: create one to run cleanup synchronously
            _loop = asyncio.new_event_loop()
            try:
                _loop.run_until_complete(self._stop_async())
            finally:
                _loop.close()

        # Call parent stop method (synchronous)
        super().stop()

    def __del__(self) -> None:
        """Ensure cleanup when the object is destroyed."""
        if self._running:
            self._running = False
            if self._inference_task is not None and not self._inference_task.done():
                self._inference_task.cancel()
