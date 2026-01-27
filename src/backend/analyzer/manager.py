# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional

import numpy as np
from aiortc import MediaStreamTrack
from fastapi import WebSocket
from prometheus_client import Histogram
from pydantic import BaseModel

from analyzer.tracked_object import TrackedObject
from analyzer.tracker import TrackingManager
from common.config import config
from common.core.depth import get_depth_estimator
from common.core.detector import get_detector
from common.core.session import WebcamSession
from common.data.coco_labels import get_coco_label
from common.metrics import (
    get_depth_estimation_duration,
    get_detection_duration,
    get_detections_count,
)
from common.protocols import DepthEstimator, ObjectDetector
from common.typing import Detection, DetectionPayload
from common.utils.camera import compute_camera_intrinsics
from common.utils.detection import (
    normalize_bbox_coordinates,
    unproject_bbox_center_to_camera,
)
from common.utils.transforms import (
    calculate_adaptive_scale,
    resize_frame,
)

logger = logging.getLogger("manager")


class MetadataMessage(BaseModel):
    """Metadata message model."""

    timestamp: float
    frame_id: int
    detections: list[DetectionPayload]
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
    source_track: MediaStreamTrack | None = None

    def __post_init__(self) -> None:
        if self.last_fps_time == 0.0:
            self.last_fps_time = asyncio.get_event_loop().time()


class AnalyzerWebSocketManager:
    """Manages WebSocket connections and frame processing for the analyzer service."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self._webcam_session: WebcamSession | None = None
        self._processing_task: asyncio.Task[None] | None = None
        self._inference_task: asyncio.Task[None] | None = None
        self._intrinsics_logged: bool = False
        
        # Dynamic streamer configuration
        self._streamer_url: str | None = None
        self._streamer_url_event = asyncio.Event()

        self.max_consecutive_errors = 5
        # adaptive downscaling parameters
        self.target_scale_init = config.TARGET_SCALE_INIT
        self.smooth_factor = config.SMOOTH_FACTOR
        self.min_scale = config.MIN_SCALE
        self.max_scale = config.MAX_SCALE
        # adaptive frame dropping parameters
        self.fps_threshold = config.FPS_THRESHOLD
        # interpolation/ tracking params
        self._tracked_objects: dict[int, TrackedObject] = {}
        self._next_track_id = 0
        self._tracking_manager = TrackingManager(
            iou_threshold=config.TRACKING_IOU_THRESHOLD,
            max_frames_without_detection=config.TRACKING_MAX_FRAMES_WITHOUT_DETECTION,
            early_termination_iou=config.TRACKING_EARLY_TERMINATION_IOU,
            confidence_decay=config.TRACKING_CONFIDENCE_DECAY,
            max_history_size=config.TRACKING_MAX_HISTORY_SIZE,
            detection_threshold=config.DETECTION_THRESHOLD,
        )

        self._detection_duration = get_detection_duration()
        self._depth_estimation_duration = get_depth_estimation_duration()
        self._detections_count = get_detections_count()

        self._intrinsics_cache: dict[
            tuple[int, int], tuple[float, float, float, float]
        ] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

        # Start processing if this is the first client
        if len(self.active_connections) == 1:
            await self._start_processing()

    async def set_streamer_url(self, streamer_url: str) -> None:
        """Set the streamer URL and trigger processing startup if needed."""
        self._streamer_url = streamer_url
        logger.info(f"Streamer URL configured: {streamer_url}")
        self._streamer_url_event.set()

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
            # Wait for streamer URL to be configured if not already set
            if not self._streamer_url:
                logger.info("Waiting for streamer URL configuration...")
                await asyncio.wait_for(self._streamer_url_event.wait(), timeout=30.0)
            
            if not self._streamer_url:
                raise Exception("Streamer URL was not configured")

            # Connect to webcam service
            self._webcam_session = WebcamSession(self._streamer_url)
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

        # Clear intrinsics cache when stopping
        self._intrinsics_cache.clear()

    def _get_compute_intrinsics(
        self, width: int, height: int
    ) -> tuple[float, float, float, float]:
        """Get cached camera intrinsics for resolution or compute if new.

        Camera intrinsics are resolution-dependent but constant for a given size.
        This caches them to avoid redundant trigonometry calculations.

        Args:
            width: Frame width in pixels
            height: Frame height in pixels

        Returns:
            Tuple of (fx, fy, cx, cy) camera intrinsic parameters
        """
        cache_key = (width, height)
        if cache_key not in self._intrinsics_cache:
            self._intrinsics_cache[cache_key] = compute_camera_intrinsics(
                width=width,
                height=height,
                fx=config.CAMERA_FX,
                fy=config.CAMERA_FY,
                cx=config.CAMERA_CX,
                cy=config.CAMERA_CY,
                fov_x_deg=config.CAMERA_FOV_X_DEG,
                fov_y_deg=config.CAMERA_FOV_Y_DEG,
            )
        return self._intrinsics_cache[cache_key]

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
            target_scale=self.target_scale_init, source_track=source_track
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

                    # Smart Frame Dropping
                    if self._inference_task and not self._inference_task.done():
                        continue

                    self._inference_task = asyncio.create_task(
                        self._run_inference_pipeline(
                            frame_small, state, detector, estimator, current_time
                        )
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
        track = state.source_track
        if track is None:
            logger.warning("No source track available, skipping frame")
            return None

        try:
            frame = await asyncio.wait_for(track.recv(), timeout=5.0)
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

            state.target_scale = calculate_adaptive_scale(
                current_fps=state.current_fps,
                current_scale=state.target_scale,
                smooth_factor=self.smooth_factor,
                min_scale=self.min_scale,
                max_scale=self.max_scale,
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
    ) -> tuple[list[Detection], list[float], list[bool]]:
        with self._measure_time(
            self._detection_duration, labels={"backend": config.DETECTOR_BACKEND}
        ):
            # YOLO detection (async)
            raw_detections = await detector.infer(frame_small)

        if not raw_detections:
            return [], [], []

        with self._measure_time(
            self._depth_estimation_duration,
            labels={"model_type": estimator.model_type},
        ):
            # Distance estimation (sync) -> run in executor
            raw_distances = await asyncio.get_running_loop().run_in_executor(
                None, estimator.estimate_distance_m, frame_small, raw_detections
            )

        # Tracking logic
        updated_track_ids, track_assignments = (
            self._tracking_manager.match_detections_to_tracks(
                raw_detections, raw_distances, state.frame_id, state.last_fps_time
            )
        )

        # drop detections that have not reached activation threshold
        filtered_detections: list[Detection] = []
        filtered_distances: list[float] = []
        active_track_ids: set[int] = set()
        for det, dist, track_id in zip(
            raw_detections, raw_distances, track_assignments
        ):
            track = self._tracking_manager._tracked_objects.get(track_id)
            if track and track.is_active(self._tracking_manager.detection_threshold):
                filtered_detections.append(det)
                filtered_distances.append(dist)
                active_track_ids.add(track_id)

        track_ids_to_exclude = updated_track_ids | active_track_ids
        interpolated_detections, interpolated_distances = (
            self._tracking_manager.get_interpolated_detections_and_distances(
                state.frame_id,
                state.last_fps_time,
                track_ids_to_exclude=track_ids_to_exclude,
            )
        )

        self._record_detection_count(filtered_detections, interpolated_detections)

        all_detections = filtered_detections + interpolated_detections
        all_distances = filtered_distances + interpolated_distances
        is_interpolated = [False] * len(filtered_detections) + [True] * len(
            interpolated_detections
        )

        # cleanup every frame, regardless of detections
        self._tracking_manager._remove_stale_tracks(state.frame_id)

        return all_detections, all_distances, is_interpolated

    async def _run_inference_pipeline(
        self,
        frame_small: np.ndarray,
        state: ProcessingState,
        detector: ObjectDetector,
        estimator: DepthEstimator,
        current_time: float,
    ) -> None:
        """Run ML inference detection and tracking pipeline in background."""

        # Check active connections
        if not self.active_connections:
            return

        # Check sample rate (skip frames to save compute if FPS is low)
        sample_rate = 2 if state.current_fps < self.fps_threshold else 4
        should_detect = state.frame_id % sample_rate == 0

        if not should_detect:
            return

        try:
            (
                all_detections,
                all_distances,
                is_interpolated,
            ) = await self._process_detection(
                frame_small=frame_small,
                state=state,
                detector=detector,
                estimator=estimator,
            )

            if all_detections:
                await self._send_frame_metadata(
                    frame_small,
                    all_detections,
                    all_distances,
                    is_interpolated,
                    current_time,
                    state,
                )

        except Exception as e:
            logger.error("Inference pipeline error", extra={"error": str(e)})

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
        is_interpolated: list[bool],
        timestamp: float,
        frame_id: int,
        current_fps: float,
    ) -> MetadataMessage:
        """Construct metadata message with normalized boxes and camera-space XYZ."""
        h, w = frame_rgb.shape[:2]
        fx, fy, cx, cy = self._get_compute_intrinsics(w, h)

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
        for det, dist_m, is_interp in zip(detections, distances, is_interpolated):
            norm_x, norm_y, norm_w, norm_h = normalize_bbox_coordinates(
                det.x1, det.y1, det.x2, det.y2, w, h
            )

            pos_x, pos_y, pos_z = unproject_bbox_center_to_camera(
                det.x1, det.y1, det.x2, det.y2, dist_m, fx, fy, cx, cy
            )

            detection_dic: DetectionPayload = {
                "box": {
                    "x": norm_x,
                    "y": norm_y,
                    "width": norm_w,
                    "height": norm_h,
                },
                "label": det.cls_id,
                "label_text": get_coco_label(det.cls_id),
                "confidence": float(det.confidence),
                "distance": float(dist_m),
                "position": {"x": pos_x, "y": pos_y, "z": pos_z},
                "interpolated": is_interp,
            }
            det_payload.append(detection_dic)

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
        is_interpolated: list[bool],
        current_time: float,
        state: ProcessingState,
    ) -> None:
        """Build and send metadata message for current frame."""
        metadata = self._build_metadata_message(
            frame_rgb=frame_small,
            detections=detections,
            distances=distances,
            is_interpolated=is_interpolated,
            timestamp=current_time,
            frame_id=state.frame_id,
            current_fps=state.current_fps,
        )
        await self._send_metadata(metadata)
