# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import contextlib

from aiortc import RTCPeerConnection
from .state import pcs, _datachannels


async def _cleanup_pc(pc: RTCPeerConnection) -> None:
    if pc in pcs:
        pcs.remove(pc)
    with contextlib.suppress(Exception):
        await pc.close()
    if not pcs:
        # Lazy import to avoid cycles
        from .camera import _shared_cam  # noqa: WPS433

        with contextlib.suppress(Exception):
            await _shared_cam.release()
    with contextlib.suppress(KeyError):
        _datachannels.pop(id(pc))


def _send_meta(meta: list[dict[str, float | int | str]]) -> None:
    """Non-blocking metadata send to all open data channels (best-effort)."""
    if not _datachannels:
        return
    import json

    payload = json.dumps({"detections": meta})
    for ch in list(_datachannels.values()):
        with contextlib.suppress(Exception):
            ch.send(payload)
