# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import contextlib
import os
import sys
from typing import List, Optional, Tuple

import cv2
import numpy as np


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


def _read_frame(cap: cv2.VideoCapture) -> Tuple[bool, Optional[np.ndarray]]:
    """Run in a thread to grab frames without blocking asyncio loop."""
    return cap.read()
