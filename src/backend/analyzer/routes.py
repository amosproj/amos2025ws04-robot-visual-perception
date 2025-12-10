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


class MetadataMessage(BaseModel):
    timestamp: float
    frame_id: int
    detections: list[dict]
    fps: float | None = None


class AnalyzerWebSocketManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self._webcam_session: WebcamSession | None = None
        self._processing_task: asyncio.Task[None] | None = None
        self._intrinsics_logged: bool = False

        self.max_consecutive_errors = 5

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

        if len(self.active_connections) == 1:
            await self._start_processing()

    async def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        if not self.active_connections:
            await self._stop_processing()

    async def handle_message(self, websocket: WebSocket, message: str) -> None:
        try:
            data = json.loads(message)
            if data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
        except Exception:
            pass

    async def _start_processing(self) -> None:
        if self._processing_task and not self._processing_task.done():
            return

        upstream_url = config.WEBCAM_OFFER_URL
        self._webcam_session = WebcamSession(upstream_url)
        source_track = await self._webcam_session.connect()

        self._processing_task = asyncio.create_task(
            self._process_frames(source_track)
        )

    async def _stop_processing(self) -> None:
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
        detector = get_detector()
        estimator = get_depth_estimator()

        frame_id = 0
        last_frame_time = asyncio.get_event_loop().time()
        current_fps = 30.0

        # ---- REAL-TIME BACKPRESSURE STATE ----
        target_fps = 30.0
        frame_budget_s = 1.0 / target_fps
        lag_s = 0.0
        # -------------------------------------

        consecutive_errors = 0

        try:
            while self.active_connections:
                try:
                    frame = await asyncio.wait_for(source_track.recv(), timeout=5.0)
                    consecutive_errors = 0
                except asyncio.TimeoutError:
                    consecutive_errors += 1
                    if consecutive_errors >= self.max_consecutive_errors:
                        raise RuntimeError("Frame receive timeout loop")
                    continue

                try:
                    frame_array = frame.to_ndarray(format="bgr24")  # type: ignore
                except Exception:
                    continue

                frame_id += 1

                now = asyncio.get_event_loop().time()
                dt = now - last_frame_time
                last_frame_time = now
                if dt > 0:
                    current_fps = 1.0 / dt

                # ---- CATCH-UP LOGIC ----
                if lag_s > 0.016:
                    lag_s = max(0.0, lag_s - frame_budget_s)
                    continue
                # ------------------------

                if not self.active_connections:
                    continue

                loop = asyncio.get_running_loop()

                # ---- TIMED DETECTION ----
                start_processing = loop.time()

                h, w, _ = frame_array.shape

                
                detections, depths = await asyncio.gather(
                    detector.infer(frame_array),
                    estimator.predict_depth_map(frame_array, output_shape=(h, w)),
                )

                if detections:
                    distances = estimator.estimate_distance_m(
                        depths, detections
                    )
                else:
                    distances = []


                end_processing = loop.time()

                processing_time = end_processing - start_processing
                overrun = processing_time - frame_budget_s
                if overrun > 0:
                    lag_s += overrun
                    print(
                        f"Overrun {overrun*1000:.1f}ms → lag {lag_s*1000:.1f}ms"
                    )
                # -------------------------

                if not detections:
                    continue

                metadata = self._build_metadata_message(
                    frame_rgb=frame_array,
                    detections=detections,
                    distances=distances,
                    timestamp=now,
                    frame_id=frame_id,
                    current_fps=current_fps,
                )

                await self._send_metadata(metadata)

                if finish := frame_budget_s - processing_time > 0:
                    await asyncio.sleep(0)

        except asyncio.CancelledError:
            logging.info("Frame processing cancelled")
        except Exception as e:
            logging.error(f"Processing error: {e}")

    async def _send_metadata(self, metadata: MetadataMessage) -> None:
        message = json.dumps(metadata.model_dump())
        dead = set()

        for ws in self.active_connections.copy():
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        self.active_connections -= dead

    def _build_metadata_message(
        self,
        frame_rgb: np.ndarray,
        detections: list[tuple[int, int, int, int, int, float]],
        distances: list[float],
        timestamp: float,
        frame_id: int,
        current_fps: float,
    ) -> MetadataMessage:
        h, w = frame_rgb.shape[:2]
        fx, fy, cx, cy = compute_camera_intrinsics(w, h)

        det_payload = []

        for ((x1, y1, x2, y2, cls, conf), dist) in zip(detections, distances):
            box_w = max(0.0, x2 - x1)
            box_h = max(0.0, y2 - y1)
            if box_w == 0 or box_h == 0:
                continue

            pos_x, pos_y, pos_z = unproject_bbox_center_to_camera(
                x1, y1, x2, y2, dist, fx, fy, cx, cy
            )

            det_payload.append(
                {
                    "box": {
                        "x": x1 / w,
                        "y": y1 / h,
                        "width": box_w / w,
                        "height": box_h / h,
                    },
                    "label": cls,
                    "confidence": float(conf),
                    "distance": float(dist),
                    "position": {"x": pos_x, "y": pos_y, "z": pos_z},
                }
            )

        return MetadataMessage(
            timestamp=timestamp * 1000,
            frame_id=frame_id,
            detections=det_payload,
            fps=current_fps if frame_id % 30 == 0 else None,
        )

    async def shutdown(self) -> None:
        await self._stop_processing()
        for ws in self.active_connections.copy():
            await ws.close()
        self.active_connections.clear()


websocket_manager = AnalyzerWebSocketManager()
router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "analyzer"}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket_manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            await websocket_manager.handle_message(websocket, msg)
    except WebSocketDisconnect:
        pass
    finally:
        await websocket_manager.disconnect(websocket)


async def on_shutdown() -> None:
    await websocket_manager.shutdown()
