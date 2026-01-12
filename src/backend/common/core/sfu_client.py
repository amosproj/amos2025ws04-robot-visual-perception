# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import contextlib
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

from aioice import Candidate
import websockets
from aiortc import (
    RTCConfiguration,
    RTCIceCandidate,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
from aiortc.mediastreams import MediaStreamTrack
from aiortc.rtcicetransport import candidate_from_aioice, candidate_to_aioice
from websockets.client import WebSocketClientProtocol

JsonDict = Dict[str, Any]

TARGET_PUBLISHER = 0
TARGET_SUBSCRIBER = 1


def _serialize_description(desc: RTCSessionDescription) -> JsonDict:
    """Convert an aiortc session description to JSON serializable form."""
    return {"sdp": desc.sdp, "type": desc.type}


def _serialize_candidate(candidate: RTCIceCandidate) -> JsonDict:
    """Convert an ICE candidate to the JSON format expected by ion-sfu."""
    sdp_candidate = candidate_to_aioice(candidate).to_sdp()
    return {
        "candidate": sdp_candidate,
        "sdpMid": candidate.sdpMid,
        "sdpMLineIndex": candidate.sdpMLineIndex,
    }


def _candidate_from_json(data: JsonDict) -> RTCIceCandidate:
    """Create an ICE candidate from ion-sfu JSON payload."""
    sdp_candidate = data.get("candidate")
    if sdp_candidate is None:
        raise ValueError("Missing ICE candidate in payload")

    rtc_candidate = candidate_from_aioice(Candidate.from_sdp(sdp_candidate))
    rtc_candidate.sdpMid = data.get("sdpMid")
    rtc_candidate.sdpMLineIndex = data.get("sdpMLineIndex")
    return rtc_candidate


@dataclass
class IonSfuSettings:
    signaling_url: str
    session_id: str
    client_id: str
    ice_servers: list[str]
    no_subscribe: bool = False
    no_auto_subscribe: bool = False


class IonSfuClient:
    """
    Minimal ion-sfu JSON-RPC client for aiortc.

    Handles join/offer/answer/trickle to either publish tracks or receive them
    from the SFU. This is intentionally lightweight to avoid pulling in the
    full ion SDK.
    """

    def __init__(
        self,
        settings: IonSfuSettings,
        on_track: Optional[Callable[[MediaStreamTrack], Awaitable[None] | None]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._settings = settings
        self._logger = logger or logging.getLogger("ion_sfu")
        self._on_track_cb = on_track

        self._pub_pc: RTCPeerConnection | None = None
        self._sub_pc: RTCPeerConnection | None = None
        self._ws: WebSocketClientProtocol | None = None
        self._recv_task: asyncio.Task[None] | None = None
        self._pending: dict[str, asyncio.Future[JsonDict]] = {}
        self._track_future: asyncio.Future[MediaStreamTrack] | None = None
        self._publisher_tracks: list[MediaStreamTrack] = []
        self._closed = False
        self._expected_track_kind = "video"

    def add_publisher_track(self, track: MediaStreamTrack) -> None:
        """Queue a track to be published once the connection is established."""
        self._publisher_tracks.append(track)
        if self._pub_pc is not None:
            self._pub_pc.addTrack(track)

    async def connect(self) -> None:
        """Open signaling channel and join the SFU session."""
        if self._ws is not None:
            return

        rtc_config = RTCConfiguration(
            iceServers=[RTCIceServer(urls=self._settings.ice_servers)]
        )
        self._pub_pc = RTCPeerConnection(configuration=rtc_config)
        if not self._settings.no_subscribe:
            self._sub_pc = RTCPeerConnection(configuration=rtc_config)

        self._setup_peer_connections()
        await self._connect_signal()
        await self._join_session()

    async def wait_for_track(self, kind: str = "video") -> MediaStreamTrack:
        """Wait for the first remote track of the given kind."""
        self._expected_track_kind = kind
        if self._track_future is None:
            loop = asyncio.get_event_loop()
            self._track_future = loop.create_future()
        return await self._track_future

    async def close(self) -> None:
        """Gracefully close WebSocket and peer connections."""
        if self._closed:
            return
        self._closed = True

        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()

        if self._recv_task:
            self._recv_task.cancel()
            with contextlib.suppress(Exception):
                await self._recv_task

        if self._pub_pc:
            with contextlib.suppress(Exception):
                await self._pub_pc.close()
        if self._sub_pc:
            with contextlib.suppress(Exception):
                await self._sub_pc.close()
        if self._ws:
            with contextlib.suppress(Exception):
                await self._ws.close()

    def _setup_peer_connections(self) -> None:
        """Attach handlers for ICE and remote track events."""
        if self._pub_pc is None:
            return

        # Ion expects a control data channel on the publisher connection.
        self._pub_pc.createDataChannel("ion-sfu")
        self._pub_pc.on("icecandidate")(self._candidate_handler(TARGET_PUBLISHER))

        if self._sub_pc is not None:
            self._sub_pc.on("icecandidate")(self._candidate_handler(TARGET_SUBSCRIBER))
            self._sub_pc.on("track")(self._on_remote_track)

        for track in self._publisher_tracks:
            self._pub_pc.addTrack(track)

    def _candidate_handler(self, target: int) -> Callable[[Any], Awaitable[None]]:
        async def handler(event: Any) -> None:
            candidate: RTCIceCandidate | None = getattr(event, "candidate", None)
            if candidate is None or self._ws is None:
                return
            payload = {"candidate": _serialize_candidate(candidate), "target": target}
            await self._notify("trickle", payload)

        return handler

    async def _connect_signal(self) -> None:
        self._ws = await websockets.connect(
            self._settings.signaling_url, ping_interval=20, ping_timeout=20
        )
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def _join_session(self) -> None:
        if self._pub_pc is None:
            raise RuntimeError("Publisher peer connection missing")
        offer = await self._pub_pc.createOffer()
        await self._pub_pc.setLocalDescription(offer)

        join_config = {
            "no_subscribe": self._settings.no_subscribe,
            "no_publish": False,
            "no_auto_subscribe": self._settings.no_auto_subscribe,
        }
        params = {
            "sid": self._settings.session_id,
            "uid": self._settings.client_id,
            "offer": _serialize_description(offer),
            "config": join_config,
        }
        answer = await self._rpc_call("join", params)
        await self._pub_pc.setRemoteDescription(
            RTCSessionDescription(**answer)  # type: ignore[arg-type]
        )

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    message = json.loads(raw)
                except Exception:
                    continue

                if "id" in message and ("result" in message or "error" in message):
                    fut = self._pending.pop(str(message["id"]), None)
                    if fut and not fut.done():
                        fut.set_result(message)
                    continue

                method = message.get("method")
                params = message.get("params", {})
                if method == "offer":
                    await self._handle_remote_offer(params)
                elif method == "trickle":
                    await self._handle_remote_trickle(params)
        except Exception as exc:
            self._logger.warning(
                "ion_sfu signaling loop ended", extra={"error": str(exc)}
            )

    async def _rpc_call(self, method: str, params: JsonDict) -> JsonDict:
        if self._ws is None:
            raise RuntimeError("Signaling channel is not open")

        request_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        fut: asyncio.Future[JsonDict] = loop.create_future()
        self._pending[request_id] = fut

        await self._ws.send(
            json.dumps({"id": request_id, "method": method, "params": params})
        )
        response = await asyncio.wait_for(fut, timeout=15)

        if "error" in response:
            raise RuntimeError(str(response["error"]))
        return response.get("result", response)

    async def _notify(self, method: str, params: JsonDict) -> None:
        if self._ws is None:
            return
        await self._ws.send(json.dumps({"method": method, "params": params}))

    async def _handle_remote_offer(self, params: JsonDict) -> None:
        if self._sub_pc is None:
            return
        desc_json = params.get("desc") or params
        try:
            remote_desc = RTCSessionDescription(
                sdp=desc_json["sdp"], type=desc_json["type"]
            )
            await self._sub_pc.setRemoteDescription(remote_desc)
            answer = await self._sub_pc.createAnswer()
            await self._sub_pc.setLocalDescription(answer)
            await self._notify("answer", {"desc": _serialize_description(answer)})
        except Exception as exc:
            self._logger.error("Failed to handle SFU offer", extra={"error": str(exc)})

    async def _handle_remote_trickle(self, params: JsonDict) -> None:
        target = params.get("target")
        candidate_json = params.get("candidate")
        if candidate_json is None or target is None:
            return

        pc = self._pub_pc if target == TARGET_PUBLISHER else self._sub_pc
        if pc is None:
            return
        try:
            await pc.addIceCandidate(_candidate_from_json(candidate_json))
        except Exception as exc:
            self._logger.debug(
                "Ignoring bad ICE candidate",
                extra={"error": str(exc), "target": target},
            )

    async def _on_remote_track(self, track: MediaStreamTrack) -> None:
        if track.kind == self._expected_track_kind:
            if self._track_future is None:
                loop = asyncio.get_event_loop()
                self._track_future = loop.create_future()
            if not self._track_future.done():
                self._track_future.set_result(track)
        if self._on_track_cb is not None:
            maybe_coro = self._on_track_cb(track)
            if asyncio.iscoroutine(maybe_coro):
                await maybe_coro
