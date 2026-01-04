# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from contextlib import contextmanager
from typing import Dict, Iterator
import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

from prometheus_client import Histogram

import numpy as np
from aiortc import MediaStreamTrack
from fastapi import WebSocket
from pydantic import BaseModel
from common.core.session import WebcamSession
from common.config import config
from common.core.detector import get_detector
from common.core.depth import get_depth_estimator
from common.core.contracts import ObjectDetector, DepthEstimator, Detection
from common.utils.geometry import (
    compute_camera_intrinsics,
    unproject_bbox_center_to_camera,
)
from common.utils.image import resize_frame
from common.metrics import (
    get_detection_duration,
    get_depth_estimation_duration,
    get_detections_count,
)
from analyzer.tracking_models import TrackedObject
from analyzer.tracker import TrackingManager


logger = logging.getLogger("manager")


class MetadataMessage(BaseModel):
    """Metadata message model."""

    timestamp: float
    frame_id: int
    detections: list[dict]
    fps: float | None = None


@dataclass
class ProcessingState:
    """Tracks state during frame processing."""

    frame_id: int = 0
    last_fps_time: float = 0.0
    fps_counter: int = 0
    current_fps: float = 30.0
    consecutive_errors: int = 0
    target_scale: float = 0.8
    source_track: Optional[MediaStreamTrack] = None

    def __post_init__(self) -> None:
        if self.last_fps_time == 0.0:
            self.last_fps_time = asyncio.get_event_loop().time()


class AnalyzerWebSocketManager:
    """Manages WebSocket connections and frame processing for the analyzer service."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self._webcam_session: WebcamSession | None = None
        self._processing_task: asyncio.Task[None] | None = None
        self._intrinsics_logged: bool = False

        self.max_consecutive_errors = 5
        # adaptive downscaling parameters
        self.target_scale_init = config.TARGET_SCALE_INIT
        self.smooth_factor = config.SMOOTH_FACTOR
        self.min_scale = config.MIN_SCALE
        self.max_scale = config.MAX_SCALE
        # adaptive frame dropping parameters
        self.fps_threshold = config.FPS_THRESHOLD
        # interpolation/ tracking params
        self._tracked_objects: Dict[int, TrackedObject] = {}
        self._next_track_id = 0
        self._tracking_manager = TrackingManager(
            iou_threshold=config.TRACKING_IOU_THRESHOLD,
            max_frames_without_detection=config.TRACKING_MAX_FRAMES_WITHOUT_DETECTION,
            early_termination_iou=config.TRACKING_EARLY_TERMINATION_IOU,
            confidence_decay=config.TRACKING_CONFIDENCE_DECAY,
            max_history_size=config.TRACKING_MAX_HISTORY_SIZE,
        )

        self._detection_duration = get_detection_duration()
        self._depth_estimation_duration = get_depth_estimation_duration()
        self._detections_count = get_detections_count()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

        # Start processing if this is the first client
        if len(self.active_connections) == 1:
            await self._start_processing()

    async def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection."""
        self.active_connections.discard(websocket)

        # Stop processing if no more clients
        if not self.active_connections:
            await self._stop_processing()

    async def handle_message(self, websocket: WebSocket, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)

            if data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
        except (json.JSONDecodeError, KeyError):
            # Ignore malformed messages
            pass

    async def _start_processing(self) -> None:
        """Start webcam connection and frame processing."""
        if self._processing_task and not self._processing_task.done():
            return  # Already running

        try:
            # Connect to webcam service
            upstream_url = config.WEBCAM_OFFER_URL
            self._webcam_session = WebcamSession(upstream_url)
            source_track = await self._webcam_session.connect()

            # Start processing task
            self._processing_task = asyncio.create_task(
                self._process_frames(source_track)
            )

        except Exception as e:
            logger.error("Error starting processing", extra={"error": str(e)})
            await self._stop_processing()

    async def _stop_processing(self) -> None:
        """Stop webcam connection and frame processing."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None

        if self._webcam_session:
            await self._webcam_session.close()
            self._webcam_session = None

        # Clear tracking manager state when stopping
        self._tracking_manager.clear()

    async def shutdown(self) -> None:
        """Cleanup on service shutdown."""
        await self._stop_processing()

        # Close all WebSocket connections
        for websocket in self.active_connections.copy():
            try:
                await websocket.close()
            except Exception:
                pass
        self.active_connections.clear()

    @contextmanager
    def _measure_time(
        self, metric: Histogram, labels: dict[str, str]
    ) -> Iterator[None]:
        """Generic context manager to measure and record timing for any operation.

        Args:
            metric: The histogram metric to record to (e.g., self._detection_duration)
            labels: Labels to attach to the metric
        """
        start = time.perf_counter()
        yield
        duration = time.perf_counter() - start
        if metric is not None:
            metric.labels(**labels).observe(duration)

    def _record_detection_count(
        self, detections: list[Detection], interpolated_detections: list[Detection]
    ) -> None:
        """Record detection count metrics.

        Args:
            detections: List of detected objects (non-interpolated)
            interpolated_detections: List of interpolated objects
        """
        if self._detections_count is None:
            return

        if detections:
            self._detections_count.labels(interpolated="false").inc(len(detections))
        if interpolated_detections:
            self._detections_count.labels(interpolated="true").inc(
                len(interpolated_detections)
            )

    async def _process_frames(self, source_track: MediaStreamTrack) -> None:
        """Process frames from webcam and send metadata to all clients."""
        detector = get_detector()
        estimator = get_depth_estimator()

        state = ProcessingState(
            target_scale=self.target_scale_init,
            source_track=source_track,
        )

        try:
            while self.active_connections:
                try:
                    frame_array = await self._receive_and_convert_frame(state)
                    if frame_array is None:
                        continue

                    state.frame_id += 1
                    state.fps_counter += 1

                    state, current_time = self._update_fps_and_scaling(state)
                    frame_small = resize_frame(frame_array, state.target_scale)

                    detections, distances = await self._process_detection(
                        frame_small, state, detector, estimator
                    )
                    if detections:
                        await self._send_frame_metadata(
                            frame_small, detections, distances, current_time, state
                        )

                except Exception as e:
                    logger.warning("Frame processing error", extra={"error": str(e)})
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.warning("Frame processing cancelled")
        except Exception as e:
            logger.warning("Processing task error", extra={"error": str(e)})

    async def _receive_and_convert_frame(
        self, state: ProcessingState
    ) -> Optional[np.ndarray]:
        """Receive frame from webcam and convert to numpy array.

        Handles timeouts, reconnection, and frame conversion errors.

        Returns:
            Frame as numpy array, or None if frame couldn't be received/converted.
        """
        try:
            frame = await asyncio.wait_for(state.source_track.recv(), timeout=5.0)  # type: ignore[union-attr]
            state.consecutive_errors = 0
        except asyncio.TimeoutError:
            logger.warning("Frame receive timeout, skipping")
            state.consecutive_errors += 1

            if state.consecutive_errors >= self.max_consecutive_errors:
                logger.error(
                    "Too many consecutive timeouts, reconnecting",
                    extra={"consecutive_errors": state.consecutive_errors},
                )
                raise Exception("WebRTC connection appears unstable")
            return None
        except Exception:
            logger.warning("source_track broke / ended, attempting reconnect...")
            state.consecutive_errors += 1

            if state.consecutive_errors >= self.max_consecutive_errors:
                # full reconnect
                if self._webcam_session is not None:
                    await self._webcam_session.close()
                await asyncio.sleep(1.0)
                try:
                    logger.info(
                        "Reconnecting webcam session",
                        extra={"attempt": state.consecutive_errors},
                    )
                    if self._webcam_session is not None:
                        new_track = await self._webcam_session.connect()
                        state.source_track = new_track
                        state.consecutive_errors = 0
                except Exception as conn_err:
                    logger.exception("Reconnect failed", extra={"error": str(conn_err)})
                    raise
            await asyncio.sleep(0.1)
            return None

        try:
            frame_array = frame.to_ndarray(format="bgr24")  # type: ignore[union-attr]
            return frame_array
        except AttributeError:
            logger.warning(
                "Received frame without to_ndarray method",
                extra={"frame_type": str(type(frame))},
            )
            return None

    def _update_fps_and_scaling(
        self, state: ProcessingState
    ) -> tuple[ProcessingState, float]:
        """Update FPS calculation and adaptive scaling.

        Returns:
            Updated ProcessingState with new FPS and scale values.
            The current_time is the asyncio event loop time used for FPS calculation.
        """
        current_time = asyncio.get_event_loop().time()

        # Calculate FPS every second
        if current_time - state.last_fps_time >= 1.0:
            state.current_fps = state.fps_counter / (current_time - state.last_fps_time)
            state.fps_counter = 0
            state.last_fps_time = current_time

            if state.current_fps < 10:
                state.target_scale -= self.smooth_factor
            elif state.current_fps < 18:
                state.target_scale -= self.smooth_factor * 0.5
            else:
                state.target_scale += self.smooth_factor * 0.8

            state.target_scale = max(
                self.min_scale, min(self.max_scale, state.target_scale)
            )

            logger.info(
                "adaptive_resolution_update",
                extra={
                    "scale": round(state.target_scale, 2),
                    "fps": round(state.current_fps, 1),
                },
            )

        return state, current_time

    async def _process_detection(
        self,
        frame_small: np.ndarray,
        state: ProcessingState,
        detector: ObjectDetector,
        estimator: DepthEstimator,
    ) -> tuple[list[Detection], list[float]]:
        """Process detection for current frame (real or interpolated).

        Returns:
            Tuple of (detections, distances) lists
        """
        sample_rate = 2 if state.current_fps < self.fps_threshold else 4
        should_detect = state.frame_id % sample_rate == 0

        if not self.active_connections or not should_detect:
            return [], []

        detections: list[Detection] = []
        distances: list[float] = []
        updated_track_ids: set[int] = set()

        with self._measure_time(
            self._detection_duration, labels={"backend": config.DETECTOR_BACKEND}
        ):
            detections = await detector.infer(frame_small)

        if detections:
            with self._measure_time(
                self._depth_estimation_duration,
                labels={"model_type": estimator.model_type},
            ):
                distances = estimator.estimate_distance_m(frame_small, detections)

            updated_track_ids = self._tracking_manager.match_detections_to_tracks(
                detections, distances, state.frame_id, state.last_fps_time
            )

        interpolated_detections, interpolated_distances = (
            self._tracking_manager.get_interpolated_detections_and_distances(
                state.frame_id,
                state.last_fps_time,
                track_ids_to_exclude=updated_track_ids,
            )
        )

        all_detections = detections + interpolated_detections
        all_distances = distances + interpolated_distances

        self._record_detection_count(detections, interpolated_detections)

        # cleanup every frame, regardless of detections
        self._tracking_manager._remove_stale_tracks(state.frame_id)

        return all_detections, all_distances

    async def _send_metadata(self, metadata: MetadataMessage) -> None:
        """Send metadata to all active WebSocket clients."""
        message = json.dumps(metadata.model_dump())
        dead_connections = set()

        # Send to all active WebSocket clients
        for websocket in self.active_connections.copy():
            try:
                await websocket.send_text(message)
            except Exception:
                dead_connections.add(websocket)

        # Remove dead connections
        self.active_connections -= dead_connections

    def _build_metadata_message(
        self,
        frame_rgb: np.ndarray,
        detections: list[Detection],
        distances: list[float],
        timestamp: float,
        frame_id: int,
        current_fps: float,
    ) -> MetadataMessage:
        """Construct metadata message with normalized boxes and camera-space XYZ."""
        h, w = frame_rgb.shape[:2]
        fx, fy, cx, cy = compute_camera_intrinsics(w, h)

        if not self._intrinsics_logged and getattr(config, "LOG_INTRINSICS", False):
            logger.info(
                "camera_intrinsics",
                extra={
                    "fx": round(fx, 2),
                    "fy": round(fy, 2),
                    "cx": round(cx, 2),
                    "cy": round(cy, 2),
                    "frame_width": w,
                    "frame_height": h,
                },
            )
            self._intrinsics_logged = True

        det_payload = []
        for det, dist_m in zip(detections, distances):
            box_w = max(0.0, float(det.x2 - det.x1))
            box_h = max(0.0, float(det.y2 - det.y1))
            if box_w <= 0 or box_h <= 0:
                continue

            norm_x = max(0.0, min(1.0, det.x1 / w))
            norm_y = max(0.0, min(1.0, det.y1 / h))
            norm_w = max(0.0, min(1.0, box_w / w))
            norm_h = max(0.0, min(1.0, box_h / h))

            pos_x, pos_y, pos_z = unproject_bbox_center_to_camera(
                det.x1, det.y1, det.x2, det.y2, dist_m, fx, fy, cx, cy
            )

            det_payload.append(
                {
                    "box": {
                        "x": norm_x,
                        "y": norm_y,
                        "width": norm_w,
                        "height": norm_h,
                    },
                    "label": det.cls_id,
                    "confidence": float(det.confidence),
                    "distance": float(dist_m),
                    "position": {"x": pos_x, "y": pos_y, "z": pos_z},
                }
            )

        return MetadataMessage(
            timestamp=timestamp * 1000,  # milliseconds
            frame_id=frame_id,
            detections=det_payload,
            fps=current_fps if frame_id % 30 == 0 else None,  # Send FPS every 30 frames
        )

    async def _send_frame_metadata(
        self,
        frame_small: np.ndarray,
        detections: list[Detection],
        distances: list[float],
        current_time: float,
        state: ProcessingState,
    ) -> None:
        """Build and send metadata message for current frame."""
        metadata = self._build_metadata_message(
            frame_rgb=frame_small,
            detections=detections,
            distances=distances,
            timestamp=current_time,
            frame_id=state.frame_id,
            current_fps=state.current_fps,
        )
        await self._send_metadata(metadata)
