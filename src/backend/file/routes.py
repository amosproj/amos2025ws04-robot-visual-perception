# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import contextlib
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
    RTCDataChannel,
)
from aiortc.rtcrtpsender import RTCRtpSender

from common.config import config
from file.tracks import VideoFileTrack

router = APIRouter()

# Global state for this service
pcs: List[RTCPeerConnection] = []
_datachannels: Dict[int, RTCDataChannel] = {}


class SDPModel(BaseModel):
    """SDP offer/answer model."""

    sdp: str
    type: str


@router.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "webcam"}


@router.options("/offer")
@router.options("/offer/")
def options_offer() -> Response:
    """Handle CORS preflight."""
    return Response(status_code=204)


@router.post("/offer")
@router.post("/offer/")
async def offer(sdp: SDPModel) -> dict[str, str]:
    """
    WebRTC signaling endpoint for webcam stream.

    Provides direct access to raw local camera frames.
    """
    if sdp.type != "offer":
        raise HTTPException(400, "type must be 'offer'")

    cfg = RTCConfiguration(iceServers=[RTCIceServer(urls=[config.STUN_SERVER])])
    pc = RTCPeerConnection(configuration=cfg)
    pcs.append(pc)

    ice_ready = asyncio.get_event_loop().create_future()

    # Create video file track
    video_path = config.VIDEO_FILE_PATH
    
    try:
        local_video = VideoFileTrack(video_path)
        pc.addTrack(local_video)
    except Exception as e:
        await pc.close()
        pcs.remove(pc)
        raise HTTPException(500, f"Video file error: {e}")

    # Prefer H.264 for better compatibility
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
        await asyncio.wait_for(ice_ready, timeout=config.ICE_GATHERING_TIMEOUT)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


async def on_shutdown() -> None:
    """Cleanup on service shutdown."""
    await asyncio.gather(*[_cleanup_pc(pc) for pc in list(pcs)], return_exceptions=True)


async def _cleanup_pc(pc: RTCPeerConnection) -> None:
    """Clean up a peer connection."""
    if pc in pcs:
        pcs.remove(pc)
    with contextlib.suppress(Exception):
        await pc.close()
    with contextlib.suppress(KeyError):
        _datachannels.pop(id(pc))
