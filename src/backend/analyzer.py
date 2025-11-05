# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

"""
WebRTC analyzer backend consuming an incoming stream, running YOLO inference,
and returning an annotated stream plus metadata.

Run:
    uv run uvicorn analyzer:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from aiortc import (
    RTCConfiguration,
    RTCDataChannel,
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceServer,
    RTCRtpSender,
    VideoStreamTrack,
)
from aiortc.mediastreams import MediaStreamTrack
from av import VideoFrame
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ultralytics import YOLO  # type: ignore[import-untyped]
import httpx


class _Detector:
    """Singleton YOLOv8 inference helper with throttled execution."""

    def __init__(self) -> None:
        self._model = YOLO("yolov8n.pt")
        self._last_det: Optional[List[Tuple[int, int, int, int, int, float]]] = None
        self._last_time: float = 0.0
        self._lock = asyncio.Lock()
        self._fov_deg: float = float(os.getenv("CAMERA_HFOV_DEG", "60"))

    async def infer(self, frame_bgr: np.ndarray) -> List[Tuple[int, int, int, int, int, float]]:
        """
        Returns list of (x1, y1, x2, y2, class_id, confidence).
        Throttled to ~10 Hz because inference is expensive.
        """
        now = asyncio.get_running_loop().time()
        if self._last_det is not None and (now - self._last_time) < 0.10:
            return self._last_det

        async with self._lock:
            now = asyncio.get_running_loop().time()
            if self._last_det is not None and (now - self._last_time) < 0.10:
                return self._last_det

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            results = self._model.predict(rgb, imgsz=640, conf=0.25, verbose=False)

            detections: List[Tuple[int, int, int, int, int, float]] = []
            if results:
                r = results[0]
                if r.boxes is not None and len(r.boxes) > 0:
                    xyxy = r.boxes.xyxy.cpu().numpy().astype(int)
                    cls = r.boxes.cls.cpu().numpy().astype(int)
                    conf = r.boxes.conf.cpu().numpy()
                    for (x1, y1, x2, y2), c, p in zip(xyxy, cls, conf):
                        detections.append((int(x1), int(y1), int(x2), int(y2), int(c), float(p)))

            self._last_det = detections
            self._last_time = now
            return detections

    def estimate_distance_m(self, bbox: Tuple[int, int, int, int], frame_width: int) -> float:
        """Very rough monocular distance estimate using bbox width and assumed HFOV."""
        x1, _, x2, _ = bbox
        pix_w = max(1, x2 - x1)
        obj_w_m = float(os.getenv("OBJ_WIDTH_M", "0.5"))
        fov_rad = np.deg2rad(self._fov_deg)
        focal_px = (frame_width / 2.0) / np.tan(fov_rad / 2.0)
        dist_m = (obj_w_m * focal_px) / pix_w
        scale = float(os.getenv("DIST_SCALE", "1.5"))
        return float(dist_m * scale)


_detector = _Detector()


class _AnalyzedVideoTrack(VideoStreamTrack):
    """Wrap an inbound track, run YOLO, and send annotated frames."""

    kind = "video"

    def __init__(self, source: MediaStreamTrack, pc_id: int) -> None:
        super().__init__()
        self._source = source
        self._pc_id = pc_id

    async def recv(self) -> VideoFrame:
        frame = await self._source.recv()
        if not isinstance(frame, VideoFrame):
            raise TypeError("Expected VideoFrame from source track")
        base = frame.to_ndarray(format="bgr24")

        detections = await _detector.infer(base)
        overlay = base.copy()
        h, w = overlay.shape[:2]
        meta: List[Dict[str, float | int]] = []

        for (x1, y1, x2, y2, cls_id, conf) in detections:
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 2)
            dist_m = _detector.estimate_distance_m((x1, y1, x2, y2), w)
            label = f"{cls_id}:{conf:.2f} {dist_m:.1f}m"
            cv2.putText(
                overlay,
                label,
                (x1, max(0, y1 - 10)),
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
                    "x1": int(x1),
                    "y1": int(y1),
                    "x2": int(x2),
                    "y2": int(y2),
                    "dist_m": float(dist_m),
                }
            )

        _send_meta(self._pc_id, meta)

        rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB).astype("uint8")
        out = VideoFrame.from_ndarray(rgb, format="rgb24")
        out.pts = frame.pts
        out.time_base = frame.time_base
        return out


app = FastAPI(title="WebRTC Analyzer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class SDPModel(BaseModel):
    sdp: str
    type: str


class _WebcamSession:
    """Manages a peer connection to the webcam service for a single analyzer client."""

    def __init__(self, offer_url: str) -> None:
        self._offer_url = offer_url
        self._pc: Optional[RTCPeerConnection] = None
        self._track: Optional[MediaStreamTrack] = None

    async def connect(self) -> MediaStreamTrack:
        cfg = RTCConfiguration(
            iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
        )
        pc = RTCPeerConnection(configuration=cfg)
        self._pc = pc

        track_future: asyncio.Future[MediaStreamTrack] = asyncio.get_event_loop().create_future()
        ice_ready: asyncio.Future[None] = asyncio.get_event_loop().create_future()

        if pc.iceGatheringState == "complete" and not ice_ready.done():
            ice_ready.set_result(None)

        @pc.on("track")
        def on_track(track: MediaStreamTrack) -> None:
            if track.kind == "video" and not track_future.done():
                track_future.set_result(track)

        @pc.on("icegatheringstatechange")
        def on_ice_gathering_state_change() -> None:
            if pc.iceGatheringState == "complete" and not ice_ready.done():
                ice_ready.set_result(None)

        pc.addTransceiver("video", direction="recvonly")
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(ice_ready, timeout=5)

        payload = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(self._offer_url, json=payload)
            res.raise_for_status()
            answer = res.json()

        await pc.setRemoteDescription(RTCSessionDescription(**answer))
        self._track = await track_future
        return self._track

    async def close(self) -> None:
        if self._track is not None:
            with contextlib.suppress(Exception):
                self._track.stop()
            self._track = None
        if self._pc is not None:
            with contextlib.suppress(Exception):
                await self._pc.close()
            self._pc = None


pcs: List[RTCPeerConnection] = []
_data_channels: Dict[int, RTCDataChannel] = {}
_sessions: Dict[int, _WebcamSession] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.options("/offer")
@app.options("/offer/")
def options_offer() -> Response:
    return Response(status_code=204)


@app.post("/offer")
@app.post("/offer/")
async def offer(sdp: SDPModel) -> dict[str, str]:
    if sdp.type != "offer":
        raise HTTPException(400, "type must be 'offer'")

    cfg = RTCConfiguration(
        iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
    )
    pc = RTCPeerConnection(configuration=cfg)
    pcs.append(pc)

    pc_id = id(pc)
    _data_channels[pc_id] = pc.createDataChannel("meta")
    ice_ready = asyncio.get_event_loop().create_future()

    session = _WebcamSession(
        os.getenv("WEBCAM_OFFER_URL", "http://localhost:8000/offer")
    )
    try:
        source_track = await session.connect()
    except Exception as exc:
        await session.close()
        with contextlib.suppress(Exception):
            await pc.close()
        pcs.remove(pc)
        _data_channels.pop(pc_id, None)
        raise HTTPException(502, f"Webcam upstream error: {exc}") from exc

    _sessions[pc_id] = session
    processed = _AnalyzedVideoTrack(source_track, pc_id)
    pc.addTrack(processed)

    @pc.on("icegatheringstatechange")
    def on_ice_gathering_state_change() -> None:
        if pc.iceGatheringState == "complete" and not ice_ready.done():
            ice_ready.set_result(True)

    @pc.on("iceconnectionstatechange")
    async def on_ice_state_change() -> None:
        if pc.iceConnectionState in ("failed", "closed", "disconnected"):
            await _cleanup_pc(pc)

    try:
        caps = RTCRtpSender.getCapabilities("video").codecs
        h264 = [c for c in caps if getattr(c, "mimeType", "").lower() == "video/h264"]
        if h264:
            for t in pc.getTransceivers():
                if t.kind == "video":
                    t.setCodecPreferences(h264)
    except Exception:
        pass

    if pc.iceGatheringState == "complete" and not ice_ready.done():
        ice_ready.set_result(True)

    offer_desc = RTCSessionDescription(sdp=sdp.sdp, type=sdp.type)
    await pc.setRemoteDescription(offer_desc)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(ice_ready, timeout=5)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await asyncio.gather(*[_cleanup_pc(pc) for pc in list(pcs)], return_exceptions=True)


async def _cleanup_pc(pc: RTCPeerConnection) -> None:
    pc_id = id(pc)
    if pc in pcs:
        pcs.remove(pc)
    with contextlib.suppress(Exception):
        await pc.close()

    channel = _data_channels.pop(pc_id, None)
    if channel is not None:
        with contextlib.suppress(Exception):
            channel.close()

    session = _sessions.pop(pc_id, None)
    if session is not None:
        await session.close()


def _send_meta(pc_id: int, meta: List[Dict[str, float | int]]) -> None:
    channel = _data_channels.get(pc_id)
    if channel is None or channel.readyState != "open":
        return
    payload = json.dumps({"detections": meta})
    with contextlib.suppress(Exception):
        channel.send(payload)
