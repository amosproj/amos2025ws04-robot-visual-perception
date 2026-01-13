# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
from typing import Any

import pytest

from common.config import config
from common.core import session


class _FakeTrack:
    def __init__(self, kind: str = "video") -> None:
        self.kind = kind
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class _FakeSfuClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.connected = False
        self.closed = False
        self.wait_kind: str | None = None

    async def connect(self) -> None:
        await asyncio.sleep(0)
        self.connected = True

    async def wait_for_track(self, kind: str = "video") -> _FakeTrack:
        await asyncio.sleep(0)
        self.wait_kind = kind
        return _FakeTrack(kind=kind)

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_webcam_session_uses_sfu_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure WebcamSession connects via Ion-SFU when WEBRTC_MODE is set to ion-sfu."""
    original_mode = config.WEBRTC_MODE
    try:
        config.WEBRTC_MODE = "ion-sfu"
        config.SFU_SIGNALING_URL = "ws://localhost:7000/ws"
        config.SFU_SESSION_ID = "optibot"
        config.SFU_SUBSCRIBER_ID = "analyzer"

        created: dict[str, _FakeSfuClient] = {}

        def _build_client(*args: Any, **kwargs: Any) -> _FakeSfuClient:
            client = _FakeSfuClient(*args, **kwargs)
            created["client"] = client
            return client

        monkeypatch.setattr(session, "IonSfuClient", _build_client)

        webcam_session = session.WebcamSession("http://does-not-matter")
        track = await webcam_session.connect()

        # Track returned from SFU path
        assert isinstance(track, _FakeTrack)
        assert track.kind == "video"

        fake_client = created.get("client")
        assert fake_client is not None
        assert fake_client.connected is True
        assert fake_client.wait_kind == "video"

        await webcam_session.close()
        assert fake_client.closed is True
    finally:
        config.WEBRTC_MODE = original_mode
