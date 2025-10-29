# server.py
"""
Webcam → WebRTC backend

Fixes for 405:
- CORS preflight handled (OPTIONS on /offer).
- Accept both /offer and /offer/ paths.
- Wildcard origins without credentials (spec-compliant).

Run:
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import os
import sys
import contextlib
from typing import Optional, List

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

# -----------------------------
# Global camera singleton
# -----------------------------


class _SharedCamera:
    def __init__(self):
        self._refcount = 0
        self._lock = asyncio.Lock()
        self._cap = None
        self._frame = None
        self._running = False
        self._reader_task: Optional[asyncio.Task] = None

    async def acquire(self):
        async with self._lock:
            self._refcount += 1
            if self._cap is None:
                idx = int(os.getenv("CAMERA_INDEX", "0"))
                self._cap = _open_camera(idx)
                self._running = True
                self._reader_task = asyncio.create_task(self._read_loop())

    async def release(self):
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

    async def _read_loop(self):
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

    def latest(self):
        return self._frame

_shared_cam = _SharedCamera()

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
        cap = cv2.VideoCapture(idx, backend) if backend != cv2.CAP_ANY else cv2.VideoCapture(idx)
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

    def __init__(self):
        super().__init__()

    async def recv(self):
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

        from av import VideoFrame
        import cv2 as _cv2

        rgb = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
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

@app.get("/health")
def health():
    return {"status": "ok"}

# Explicit OPTIONS handlers to avoid 405 on preflight in some setups
@app.options("/offer")
@app.options("/offer/")
def options_offer():
    return Response(status_code=204)

# Accept both /offer and /offer/
@app.post("/offer")
@app.post("/offer/")
async def offer(sdp: SDPModel):
    if sdp.type != "offer":
        raise HTTPException(400, "type must be 'offer'")

    cfg = RTCConfiguration(iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])])
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

    if pc.iceGatheringState == "complete":
        if not ice_ready.done():
            ice_ready.set_result(True)

    @pc.on("icegatheringstatechange")
    def on_ice_gathering_state_change():
        if pc.iceGatheringState == "complete" and not ice_ready.done():
            ice_ready.set_result(True)

    @pc.on("iceconnectionstatechange")
    async def on_ice_state_change():
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
async def on_shutdown():
    await asyncio.gather(*[_cleanup_pc(pc) for pc in list(pcs)], return_exceptions=True)

async def _cleanup_pc(pc: RTCPeerConnection):
    if pc in pcs:
        pcs.remove(pc)
    with contextlib.suppress(Exception):
        await pc.close()
    if not pcs:
        with contextlib.suppress(Exception):
            await _shared_cam.release()


def _read_frame(cap: cv2.VideoCapture):
    """Run in a thread to grab frames without blocking asyncio loop."""
    return cap.read()