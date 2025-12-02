# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import json
import cv2
from typing import Any

from aiortc import MediaStreamTrack
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from common.core.session import WebcamSession
from common.config import config
from common.core.detector import get_detector
from common.core.depth import get_depth_estimator


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
            print(f"Error starting processing: {e}")
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

        frame_id = 0
        last_fps_time = asyncio.get_event_loop().time()
        fps_counter = 0
        current_fps = 30.0
        consecutive_errors = 0

        target_scale = self.target_scale_init

        try:
            while self.active_connections:
                try:
                    # Get frame from webcam
                    try:
                        frame = await asyncio.wait_for(source_track.recv(), timeout=5.0)
                        consecutive_errors = 0  # Reset error counter on success
                    except asyncio.TimeoutError:
                        print("Frame receive timeout, skipping...")
                        consecutive_errors += 1
                        if consecutive_errors >= self.max_consecutive_errors:
                            print("Too many consecutive timeouts, reconnecting...")
                            raise Exception("WebRTC connection appears unstable")
                        continue
                    except Exception:
                        print("source_track broke / ended, attempting reconnect...")
                        consecutive_errors += 1

                        if consecutive_errors >= self.max_consecutive_errors:
                            # full reconnect
                            if self._webcam_session is not None:
                                await self._webcam_session.close()
                            await asyncio.sleep(1.0)
                            try:
                                print("Reconnecting webcam session...")
                                if self._webcam_session is not None:
                                    new_track = await self._webcam_session.connect()
                                    source_track = new_track
                                    consecutive_errors = 0
                                    continue
                            except Exception as conn_err:
                                print("Reconnect failed:", conn_err)
                                raise  # let the outer loop terminate
                        await asyncio.sleep(0.1)
                        continue

                    # Convert frame to numpy array - frame should be VideoFrame from aiortc
                    try:
                        frame_array = frame.to_ndarray(format="bgr24")  # type: ignore[union-attr]
                    except AttributeError:
                        print(
                            f"Received frame without to_ndarray method: {type(frame)}"
                        )
                        continue

                    frame_id += 1
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

                    # Run ML inference on frame and collect detections
                    detections_data = []
                    run_detect = (
                        frame_id % (2 if current_fps < self.fps_threshold else 4) == 0
                    )
                    if run_detect:
                        # YOLO detection
                        detections = await detector.infer(frame_small)

                        if not detections:
                            continue

                        # Distance estimation
                        distances = estimator.estimate_distance_m(
                            frame_small, detections
                        )
                        orig_h, orig_w = frame_array.shape[:2]
                        # Format detection data
                        for i, (x1, y1, x2, y2, cls_id, confidence) in enumerate(
                            detections
                        ):
                            if target_scale < 0.98:
                                x1 = int(x1 / target_scale)
                                y1 = int(y1 / target_scale)
                                x2 = int(x2 / target_scale)
                                y2 = int(y2 / target_scale)
                            detections_data.append(
                                {
                                    "box": {
                                        "x": x1 / orig_w,  # Normalized coordinates
                                        "y": y1 / orig_h,
                                        "width": (x2 - x1) / orig_w,
                                        "height": (y2 - y1) / orig_h,
                                    },
                                    "label": cls_id,
                                    "confidence": float(confidence),
                                    "distance": float(distances[i]),
                                }
                            )

                    if not self.active_connections or not detections_data:
                        continue

                    # Create and send metadata message
                    await self._send_metadata(
                        current_time, frame_id, detections_data, current_fps
                    )

                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.033)  # ~30 FPS processing

                except Exception as e:
                    print(f"Frame processing error: {e}")
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            print("Frame processing cancelled")
        except Exception as e:
            print(f"Processing task error: {e}")

    async def _send_metadata(
        self,
        timestamp: float,
        frame_id: int,
        detections_data: list[dict[str, Any]],
        current_fps: float,
    ) -> None:
        """Send metadata to all active WebSocket clients."""
        metadata = MetadataMessage(
            timestamp=timestamp * 1000,  # milliseconds
            frame_id=frame_id,
            detections=detections_data,
            fps=current_fps if frame_id % 30 == 0 else None,  # Send FPS every 30 frames
        )
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
