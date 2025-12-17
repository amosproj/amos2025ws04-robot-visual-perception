# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import json
import cv2
import logging

import numpy as np
from aiortc import MediaStreamTrack
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from common.core.session import WebcamSession
from common.config import config
from common.core.detector import get_detector
from common.core.depth import get_depth_estimator
from common.utils.geometry import (
    compute_camera_intrinsics,
    unproject_bbox_center_to_camera,
)
from typing import Any


class MetadataMessage(BaseModel):
    """Metadata message model."""

    timestamp: float
    frame_id: int
    detections: list[dict]
    fps: float | None = None


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
            logging.error(f"Error starting processing: {e}")
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

    async def _process_frames(self, source_track: MediaStreamTrack) -> None:
        """Process frames from webcam and send metadata to all WebSocket clients."""
        detector = get_detector()
        estimator = get_depth_estimator()

        # Shared state between frame receiver and processor
        frame_id = 0
        latest_frame: tuple[int, Any] | None = None  # (frame_id, frame_array)
        frame_lock = asyncio.Lock()
        frame_ready = asyncio.Event()
        
        last_fps_time = asyncio.get_event_loop().time()
        fps_counter = 0
        current_fps = 30.0
        consecutive_errors = 0

        target_scale = self.target_scale_init

        # Separate task for continuously receiving frames
        async def frame_receiver():
            nonlocal frame_id, latest_frame, consecutive_errors, source_track
            
            while self.active_connections:
                try:
                    # Always receive frames to keep frame_id in sync with video stream
                    frame = await asyncio.wait_for(source_track.recv(), timeout=5.0)
                    frame_id += 1
                    consecutive_errors = 0
                    
                    # Convert to numpy array
                    try:
                        frame_array = frame.to_ndarray(format="bgr24")  # type: ignore[union-attr]
                    except AttributeError:
                        logging.warning(f"Received frame without to_ndarray method: {type(frame)}")
                        continue
                    
                    # Store latest frame with its frame_id
                    async with frame_lock:
                        latest_frame = (frame_id, frame_array)
                        frame_ready.set()
                    
                except asyncio.TimeoutError:
                    logging.warning("Frame receive timeout, skipping...")
                    consecutive_errors += 1
                    if consecutive_errors >= self.max_consecutive_errors:
                        logging.error("Too many consecutive timeouts, reconnecting...")
                        raise Exception("WebRTC connection appears unstable")
                    continue
                except Exception as e:
                    logging.warning(f"Frame receiver error: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= self.max_consecutive_errors:
                        # full reconnect
                        if self._webcam_session is not None:
                            await self._webcam_session.close()
                        await asyncio.sleep(1.0)
                        try:
                            logging.info("Reconnecting webcam session...")
                            if self._webcam_session is not None:
                                new_track = await self._webcam_session.connect()
                                source_track = new_track
                                consecutive_errors = 0
                                continue
                        except Exception as conn_err:
                            logging.error(f"Reconnect failed: {conn_err}")
                            raise
                    await asyncio.sleep(0.1)
                    continue

        # Start frame receiver task
        receiver_task = asyncio.create_task(frame_receiver())

        try:
            while self.active_connections:
                try:
                    # Wait for new frame from receiver
                    await frame_ready.wait()
                    frame_ready.clear()
                    
                    async with frame_lock:
                        if latest_frame is None:
                            continue
                        current_frame_id, frame_array = latest_frame

                    fps_counter += 1

                    # Calculate FPS every second
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_fps_time >= 1.0:
                        current_fps = fps_counter / (current_time - last_fps_time)
                        fps_counter = 0
                        last_fps_time = current_time

                        if current_fps < 10:
                            target_scale -= self.smooth_factor
                        elif current_fps < 18:
                            target_scale -= self.smooth_factor * 0.5
                        else:
                            target_scale += self.smooth_factor * 0.8

                        target_scale = max(
                            self.min_scale, min(self.max_scale, target_scale)
                        )
                        print(
                            f"[Adaptive Res] Scale={target_scale:.2f} | FPS={current_fps:.1f}"
                        )

                    # Resize frame for processing
                    if target_scale < 0.98:
                        new_w = int(frame_array.shape[1] * target_scale)
                        new_h = int(frame_array.shape[0] * target_scale)
                        frame_small = cv2.resize(frame_array, (new_w, new_h))
                    else:
                        frame_small = frame_array

                    sample_rate = 2 if current_fps < self.fps_threshold else 4

                    # Run ML inference with adaptive frame dropping
                    if not self.active_connections or current_frame_id % sample_rate != 0:
                        continue

                    # YOLO detection
                    detections = await detector.infer(frame_small)

                    if not detections:
                        continue

                    # Distance estimation
                    distances = estimator.estimate_distance_m(frame_small, detections)

                    metadata = self._build_metadata_message(
                        frame_rgb=frame_small,
                        detections=detections,
                        distances=distances,
                        timestamp=current_time,
                        frame_id=current_frame_id,
                        current_fps=current_fps,
                    )

                    # Create and send metadata message
                    await self._send_metadata(metadata)
                    print(f"Sent metadata for frame {current_frame_id}, {len(detections)} detections")

                    # Small delay to prevent overwhelming
                    # await asyncio.sleep(0.033)  # ~30 FPS processing

                except Exception as e:
                    logging.warning(f"Frame processing error: {e}")
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logging.warning("Frame processing cancelled")
        except Exception as e:
            logging.warning(f"Processing task error: {e}")
        finally:
            # Cancel frame receiver task
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass

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
        detections: list[tuple[int, int, int, int, int, float]],
        distances: list[float],
        timestamp: float,
        frame_id: int,
        current_fps: float,
    ) -> MetadataMessage:
        """Construct metadata message with normalized boxes and camera-space XYZ."""
        h, w = frame_rgb.shape[:2]
        fx, fy, cx, cy = compute_camera_intrinsics(w, h)

        if not self._intrinsics_logged and getattr(config, "LOG_INTRINSICS", False):
            logging.info(
                f"intrinsics fx={fx:.2f} fy={fy:.2f} cx={cx:.2f} cy={cy:.2f} (frame {w}x{h})"
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
                    "box": {
                        "x": norm_x,
                        "y": norm_y,
                        "width": norm_w,
                        "height": norm_h,
                    },
                    "label": cls_id,
                    "confidence": float(conf),
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


# Create a global instance of the WebSocket manager
websocket_manager = AnalyzerWebSocketManager()

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "analyzer"}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for metadata streaming.

    Connects to webcam service, processes frames with ML,
    and sends metadata to clients like the frontend.
    """
    await websocket_manager.connect(websocket)

    try:
        # Keep connection alive
        while True:
            # Wait for client messages (ping/pong or control)
            message = await websocket.receive_text()
            await websocket_manager.handle_message(websocket, message)

    except WebSocketDisconnect:
        pass
    finally:
        await websocket_manager.disconnect(websocket)


async def on_shutdown() -> None:
    """Cleanup on service shutdown."""
    await websocket_manager.shutdown()
