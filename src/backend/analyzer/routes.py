# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import contextlib
import os
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

from common.core.session import WebcamSession
from common.config import config
from analyzer.tracks import AnalyzedVideoTrack

router = APIRouter()

# Global state for this service
pcs: List[RTCPeerConnection] = []
_data_channels: Dict[int, RTCDataChannel] = {}
_sessions: Dict[int, WebcamSession] = {}


class SDPModel(BaseModel):
    """SDP offer/answer model."""

    sdp: str
    type: str


@router.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "analyzer"}


@router.options("/offer")
@router.options("/offer/")
def options_offer() -> Response:
    """Handle CORS preflight."""
    return Response(status_code=204)


@router.post("/offer")
@router.post("/offer/")
async def offer(sdp: SDPModel) -> dict[str, str]:
    """
    WebRTC signaling endpoint for analyzer service.

    This endpoint:
    1. Connects to upstream webcam service
    2. Receives video stream
    3. Processes with YOLO detection
    4. Returns annotated stream to client
    """
    if sdp.type != "offer":
        raise HTTPException(400, "type must be 'offer'")

    cfg = RTCConfiguration(iceServers=[RTCIceServer(urls=[config.STUN_SERVER])])
    pc = RTCPeerConnection(configuration=cfg)
    pcs.append(pc)

    pc_id = id(pc)
    _data_channels[pc_id] = pc.createDataChannel("meta")
    ice_ready = asyncio.get_event_loop().create_future()

    # Connect to upstream webcam service
    upstream_url = os.getenv("WEBCAM_OFFER_URL", "http://localhost:8000/offer")
    session = WebcamSession(upstream_url)

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

    # Wrap source track with analysis
    processed = AnalyzedVideoTrack(source_track, pc_id)
    pc.addTrack(processed)

    # Prefer H.264 for better compatibility
    try:
        caps = RTCRtpSender.getCapabilities("video").codecs
        h264 = [c for c in caps if getattr(c, "mimeType", "").lower() == "video/h264"]
        if h264:
            for t in pc.getTransceivers():
                if t.kind == "video":
                    t.setCodecPreferences(
                        [c for c in h264 if getattr(c, "name", "") != "avc1.640029"]
                    )
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
    """Clean up a peer connection and associated resources."""
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
