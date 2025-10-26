"""
Webcam → WebRTC backend (Windows-friendly)

- FastAPI endpoint /offer handles SDP from the viewer and returns an answer.
- Uses OpenCV to capture webcam frames.
- Supports multiple viewers; a single shared camera is used.
- STUN: Google public STUN (for local dev it works fine).
- ENV:
    CAMERA_INDEX (default: 0)
    FRAME_WIDTH  (e.g., 1280)
    FRAME_HEIGHT (e.g., 720)
    FPS          (e.g., 30)
Run:
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import os
import time
from typing import Optional, List
import contextlib

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, MediaStreamTrack

# -----------------------------
# Global camera singleton
# -----------------------------
class _SharedCamera:
    """OpenCV camera shared across all connections (prevents device contention)."""
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
                self._cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                # Optional tuning
                w = int(os.getenv("FRAME_WIDTH", "0"))
                h = int(os.getenv("FRAME_HEIGHT", "0"))
                fps = int(os.getenv("FPS", "0"))
                if w > 0: self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                if h > 0: self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                if fps > 0: self._cap.set(cv2.CAP_PROP_FPS, fps)

                if not self._cap.isOpened():
                    self._cap.release()
                    self._cap = None
                    raise RuntimeError("Cannot open webcam. Try CAMERA_INDEX=1 (or another). Check permissions.")

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
        # Read frames on a dedicated loop
        try:
            while self._running and self._cap:
                ok, frame = self._cap.read()
                if ok:
                    self._frame = frame
                else:
                    await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass

    def latest(self):
        return self._frame

_shared_cam = _SharedCamera()

# -----------------------------
# Media track
# -----------------------------
class CameraVideoTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()
        self._last_ts = 0
        self._fps = int(os.getenv("FPS", "30") or 30)

    async def recv(self):
        # Ensure camera running
        # (acquire is called by caller)
        pts, time_base = await self.next_timestamp()

        # Pull last frame; if none yet, wait briefly
        frame = _shared_cam.latest()
        tries = 0
        while frame is None and tries < 50:
            await asyncio.sleep(0.01)
            frame = _shared_cam.latest()
            tries += 1
        if frame is None:
            # still nothing
            await asyncio.sleep(1 / self._fps)
            return await self.recv()

        # Convert OpenCV BGR → RGB for aiortc VideoFrame
        from av import VideoFrame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI(title="WebRTC Webcam Streamer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local dev; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SDPModel(BaseModel):
    sdp: str
    type: str  # "offer"

# Keep references so connections don’t get GC’d
pcs: List[RTCPeerConnection] = []

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/offer")
async def offer(sdp: SDPModel):
    if sdp.type != "offer":
        raise HTTPException(400, "type must be 'offer'")

    # STUN for NAT traversal (fine on LAN/dev too)
    cfg = RTCConfiguration(
        iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
    )
    pc = RTCPeerConnection(configuration=cfg)
    pcs.append(pc)

    # Prepare camera and video track
    try:
        await _shared_cam.acquire()
    except Exception as e:
        await pc.close()
        pcs.remove(pc)
        raise HTTPException(500, f"Camera error: {e}")

    local_video = CameraVideoTrack()
    pc.addTrack(local_video)
    
    @pc.on("iceconnectionstatechange")
    async def _():
        print("ICE:", pc.iceConnectionState)



    @pc.on("iceconnectionstatechange")
    async def on_ice_state_change():
        if pc.iceConnectionState in ("failed", "closed", "disconnected"):
            await _cleanup_pc(pc)

    # Set remote description and create answer
    offer_desc = RTCSessionDescription(sdp=sdp.sdp, type=sdp.type)
    await pc.setRemoteDescription(offer_desc)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

@app.on_event("shutdown")
async def on_shutdown():
    # Close all peer connections and release camera
    await asyncio.gather(*[_cleanup_pc(pc) for pc in list(pcs)], return_exceptions=True)

async def _cleanup_pc(pc: RTCPeerConnection):
    if pc in pcs:
        pcs.remove(pc)
    with contextlib.suppress(Exception):
        await pc.close()
    # If no more peers, release camera
    if not pcs:
        with contextlib.suppress(Exception):
            await _shared_cam.release()

