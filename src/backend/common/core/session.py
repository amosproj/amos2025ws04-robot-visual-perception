# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import contextlib
import logging
from typing import Optional

import httpx
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
)
from aiortc.mediastreams import MediaStreamTrack

from common.config import config
from common.core.sfu_client import IonSfuClient, IonSfuSettings


class WebcamSession:
    """Manages a peer connection to the webcam service for a single analyzer client."""

    def __init__(self, offer_url: str) -> None:
        """Initialize a new webcam session.

        Args:
            offer_url (str): The URL endpoint to send the SDP offer to and receive
                an SDP answer from the upstream webcam service.
        """
        self._offer_url = offer_url
        self._pc: Optional[RTCPeerConnection] = None
        self._track: Optional[MediaStreamTrack] = None
        self._sfu_client: IonSfuClient | None = None

    async def connect(self) -> MediaStreamTrack:
        """Connect using configured WebRTC mode."""
        if config.WEBRTC_MODE == "ion-sfu":
            return await self._connect_via_sfu()
        return await self._connect_direct()

    async def _connect_direct(self) -> MediaStreamTrack:
        """Establish a WebRTC connection and retrieve the video track.

        Creates an SDP offer, sends it to the configured webcam service, and waits
        for the SDP answer. Once the connection is established, returns the remote
        video track for downstream processing.

        Returns:
            MediaStreamTrack: The video track received from the upstream service.

        Raises:
            Exception: If the connection or SDP exchange fails.
        """
        cfg = RTCConfiguration(iceServers=[RTCIceServer(urls=[config.STUN_SERVER])])
        pc = RTCPeerConnection(configuration=cfg)
        self._pc = pc

        track_future: asyncio.Future[MediaStreamTrack] = (
            asyncio.get_event_loop().create_future()
        )
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

        # Request to receive video
        pc.addTransceiver("video", direction="recvonly")
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(ice_ready, timeout=config.ICE_GATHERING_TIMEOUT)

        # Send offer to upstream service
        payload = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(self._offer_url, json=payload)
            res.raise_for_status()
            answer = res.json()

        await pc.setRemoteDescription(RTCSessionDescription(**answer))
        self._track = await track_future
        return self._track

    async def _connect_via_sfu(self) -> MediaStreamTrack:
        """Establish a WebRTC connection through ion-sfu and return the video track."""
        settings = IonSfuSettings(
            signaling_url=config.SFU_SIGNALING_URL,
            session_id=config.SFU_SESSION_ID,
            client_id=config.SFU_SUBSCRIBER_ID,
            ice_servers=config.SFU_ICE_SERVERS,
            no_subscribe=False,
            no_auto_subscribe=config.SFU_NO_AUTO_SUBSCRIBE,
        )
        logger = logging.getLogger("ion_sfu.subscriber")
        self._sfu_client = IonSfuClient(settings=settings, logger=logger)
        await self._sfu_client.connect()
        self._track = await self._sfu_client.wait_for_track(kind="video")
        return self._track

    async def close(self) -> None:
        """Close the peer connection and release resources.

        Stops the active video track (if any) and closes the RTCPeerConnection.
        Suppresses exceptions to ensure graceful cleanup.
        """
        if self._track is not None:
            with contextlib.suppress(Exception):
                self._track.stop()
            self._track = None
        if self._pc is not None:
            with contextlib.suppress(Exception):
                await self._pc.close()
            self._pc = None
        if self._sfu_client is not None:
            with contextlib.suppress(Exception):
                await self._sfu_client.close()
            self._sfu_client = None
