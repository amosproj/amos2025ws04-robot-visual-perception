# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import contextlib

from fastapi import APIRouter, HTTPException, Response
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
)
from aiortc.rtcrtpsender import RTCRtpSender

from .schemas import SDPModel
from .camera import _shared_cam
from .tracks import CameraVideoTrack
from .webrtc_utils import _cleanup_pc
from .state import pcs, _datachannels

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Explicit OPTIONS handlers to avoid 405 on preflight in some setups
@router.options("/offer")
@router.options("/offer/")
def options_offer() -> Response:
    return Response(status_code=204)


# Accept both /offer and /offer/
@router.post("/offer")
@router.post("/offer/")
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


# expose original shutdown hook name; server wires it
async def on_shutdown() -> None:
    # keep same semantics as original
    await asyncio.gather(*[_cleanup_pc(pc) for pc in list(pcs)], return_exceptions=True)
