# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

# server.py
"""
Webcam → WebRTC backend

Fixes for 405:
- CORS preflight handled (OPTIONS on /offer).
- Accept both /offer and /offer/ paths.
- Wildcard origins without credentials (spec-compliant).

Run:
    uv run uvicorn server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import os
import sys
import contextlib
from typing import Optional, List, Tuple

import numpy as np
import cv2
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
    VideoStreamTrack,
)
from aiortc.rtcrtpsender import RTCRtpSender
from av import VideoFrame
from ultralytics import YOLO


# -----------------------------
# Global camera singleton
# -----------------------------


class _SharedCamera:
    def __init__(self) -> None:
        self._refcount = 0
        self._lock = asyncio.Lock()
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._running = False
        self._reader_task: Optional[asyncio.Task] = None

    async def acquire(self) -> None:
        async with self._lock:
            self._refcount += 1
            if self._cap is None:
                idx = int(os.getenv("CAMERA_INDEX", "0"))
                self._cap = _open_camera(idx)
                self._running = True
                self._reader_task = asyncio.create_task(self._read_loop())

    async def release(self) -> None:
        async with self._lock:
            self._refcount -= 1
            if self._refcount <= 0:
                self._running = False
                if self._reader_task:
                    self._reader_task.cancel()
                    with contextlib.suppress(Exception):
                        await self._reader_task
                if self._cap is not None:
                    self._cap.release()
                    self._cap = None
                self._frame = None
                self._reader_task = None
                self._refcount = 0

    async def _read_loop(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            while self._running and self._cap:
                ok, frame = await loop.run_in_executor(None, _read_frame, self._cap)
                if ok:
                    self._frame = frame
                else:
                    await asyncio.sleep(0.03)
        except asyncio.CancelledError:
            pass

    def latest(self) -> Optional[np.ndarray]:
        return self._frame


_shared_cam = _SharedCamera()


# -----------------------------
# YOLO detector (singleton)
# -----------------------------


class _Detector:
    def __init__(self) -> None:
        self._model = YOLO("yolov8n.pt")
        self._last_det: Optional[list[tuple[int, int, int, int, int, float]]] = None
        self._last_time: float = 0.0
        self._lock = asyncio.Lock()
        # Approximate camera FOV for distance estimation (degrees)
        self._fov_deg: float = float(os.getenv("CAMERA_HFOV_DEG", "60"))

    async def infer(self, frame_bgr: np.ndarray) -> list[tuple[int, int, int, int, int, float]]:
        """Run (throttled) inference and cache results.

        Returns list of (x1, y1, x2, y2, class_id, conf).
        """
        now = asyncio.get_running_loop().time()
        # Throttle to ~10 Hz
        if self._last_det is not None and (now - self._last_time) < 0.10:
            return self._last_det

        async with self._lock:
            # Re-check inside lock
            now = asyncio.get_running_loop().time()
            if self._last_det is not None and (now - self._last_time) < 0.10:
                return self._last_det

            # Ultralytics expects RGB
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            results = self._model.predict(rgb, imgsz=640, conf=0.25, verbose=False)
            dets: list[tuple[int, int, int, int, int, float]] = []
            if results:
                r = results[0]
                if r.boxes is not None and len(r.boxes) > 0:
                    xyxy = r.boxes.xyxy.cpu().numpy().astype(int)
                    cls = r.boxes.cls.cpu().numpy().astype(int)
                    conf = r.boxes.conf.cpu().numpy()
                    for (x1, y1, x2, y2), c, p in zip(xyxy, cls, conf):
                        dets.append((int(x1), int(y1), int(x2), int(y2), int(c), float(p)))

            self._last_det = dets
            self._last_time = now
            return dets

    def estimate_distance_m(self, bbox: tuple[int, int, int, int], frame_width: int) -> float:
        """Very rough monocular distance estimate based on bbox width and HFOV.
        Uses class-agnostic nominal object width of 0.5 m for stability; override via env OBJ_WIDTH_M.
        """
        x1, y1, x2, y2 = bbox
        pix_w = max(1, x2 - x1)
        obj_w_m = float(os.getenv("OBJ_WIDTH_M", "0.5"))
        fov_rad = np.deg2rad(self._fov_deg)
        focal_px = (frame_width / 2.0) / np.tan(fov_rad / 2.0)
        dist_m = (obj_w_m * focal_px) / pix_w
        scale = float(os.getenv("DIST_SCALE", "1.5"))
        return float(dist_m * scale)


_detector = _Detector()


def _open_camera(idx: int) -> cv2.VideoCapture:
    """Try platform-appropriate backends before giving up."""
    backends: List[int] = []
    if sys.platform.startswith("win"):
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY]
    elif sys.platform == "darwin":
        backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
    else:
        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]

    last_error: Optional[str] = None
    for backend in backends:
        cap = (
            cv2.VideoCapture(idx, backend)
            if backend != cv2.CAP_ANY
            else cv2.VideoCapture(idx)
        )
        if cap.isOpened():
            return cap
        cap.release()
        last_error = f"backend={backend}"

    msg = f"Cannot open webcam at index {idx}"
    if last_error:
        msg += f" (last tried {last_error})"
    msg += ". Try CAMERA_INDEX=1 or ensure camera permissions are granted."
    raise RuntimeError(msg)


# -----------------------------
# Media track
# -----------------------------
class CameraVideoTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self) -> None:
        super().__init__()

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()

        frame = None
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
        # Run (throttled) detection and draw overlays
        dets = await _detector.infer(frame)
        # Mirror the base frame first so any text drawn is readable
        overlay = cv2.flip(frame, 1)
        h, w = overlay.shape[:2]
        meta: list[dict[str, float | int | str]] = []
        for (x1, y1, x2, y2, cls_id, conf) in dets:
            # Mirror bbox coordinates horizontally
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
            meta.append({
                "cls": int(cls_id),
                "conf": float(conf),
                "x1": int(mx1),
                "y1": int(y1),
                "x2": int(mx2),
                "y2": int(y2),
                "dist_m": float(dist_m),
            })

        # Send lightweight metadata if a channel is available
        _send_meta(meta)

        rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB).astype(np.uint8)
        video_frame = VideoFrame.from_ndarray(rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame


# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI(title="WebRTC Webcam Streamer", version="1.0.1")

# Proper CORS (no credentials with wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class SDPModel(BaseModel):
    sdp: str
    type: str  # "offer"


pcs: List[RTCPeerConnection] = []
_datachannels: dict[int, any] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Explicit OPTIONS handlers to avoid 405 on preflight in some setups
@app.options("/offer")
@app.options("/offer/")
def options_offer() -> Response:
    return Response(status_code=204)


# Accept both /offer and /offer/
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

    ice_ready = asyncio.get_event_loop().create_future()

    try:
        await _shared_cam.acquire()
    except Exception as e:
        await pc.close()
        pcs.remove(pc)
        raise HTTPException(500, f"Camera error: {e}")

    local_video = CameraVideoTrack()
    pc.addTrack(local_video)

    # Create a data channel for metadata
    ch = pc.createDataChannel("meta")
    _datachannels[id(pc)] = ch

    # Prefer H.264 to support Safari and improve cross-browser compatibility
    try:
        caps = RTCRtpSender.getCapabilities("video").codecs
        h264 = [c for c in caps if getattr(c, "mimeType", "").lower() == "video/h264"]
        if h264:
            for t in pc.getTransceivers():
                if t.kind == "video":
                    t.setCodecPreferences(h264)
    except Exception:
        pass

    if pc.iceGatheringState == "complete":
        if not ice_ready.done():
            ice_ready.set_result(True)

    @pc.on("icegatheringstatechange")
    def on_ice_gathering_state_change() -> None:
        if pc.iceGatheringState == "complete" and not ice_ready.done():
            ice_ready.set_result(True)

    @pc.on("iceconnectionstatechange")
    async def on_ice_state_change() -> None:
        if pc.iceConnectionState in ("failed", "closed", "disconnected"):
            await _cleanup_pc(pc)

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
    if pc in pcs:
        pcs.remove(pc)
    with contextlib.suppress(Exception):
        await pc.close()
    if not pcs:
        with contextlib.suppress(Exception):
            await _shared_cam.release()
    with contextlib.suppress(KeyError):
        _datachannels.pop(id(pc))


def _read_frame(cap: cv2.VideoCapture) -> Tuple[bool, Optional[np.ndarray]]:
    """Run in a thread to grab frames without blocking asyncio loop."""
    return cap.read()


def _send_meta(meta: list[dict[str, float | int | str]]) -> None:
    """Non-blocking metadata send to all open data channels (best-effort)."""
    if not _datachannels:
        return
    import json
    payload = json.dumps({"detections": meta})
    for ch in list(_datachannels.values()):
        with contextlib.suppress(Exception):
            ch.send(payload)
            