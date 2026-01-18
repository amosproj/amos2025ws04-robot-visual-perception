# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import contextlib
from typing import Optional

import cv2
import numpy as np

from common.config import config
from common.utils.camera import open_camera, read_frame


class _SharedCamera:
    def __init__(self) -> None:
        """Initialize shared camera state.

        Sets up internal variables including the reference counter, asyncio lock,
        capture handle, current frame buffer, running flag, and background reader task.
        """
        self._refcount = 0
        self._lock = asyncio.Lock()
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._running = False
        self._reader_task: Optional[asyncio.Task] = None

    async def acquire(self) -> None:
        """Acquire access to the shared camera.

        Increments the reference count and, if this is the first caller,
        opens the camera at the configured index and starts an asynchronous
        background task to continuously read frames without blocking the
        event loop.
        """
        async with self._lock:
            if self._cap is None:
                try:
                    self._cap = open_camera(config.CAMERA_INDEX)
                    self._running = True
                    self._reader_task = asyncio.create_task(self._read_loop())
                    self._refcount = 1  # first successful user
                except Exception:
                    # no leaked +1
                    self._refcount = max(0, self._refcount - 1)
                    raise
            else:
                self._refcount += 1

    async def release(self) -> None:
        """Release access to the shared camera.

        Decrements the reference count and, when no users remain,
        stops the frame reading loop, cancels the background task,
        releases the camera resource, and resets all internal state.
        """
        async with self._lock:
            self._refcount = max(0, self._refcount - 1)
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
        """Continuously read frames in a background task.

        Uses a thread executor to avoid blocking the event loop. On failed reads,
        waits briefly (~30 ms) to prevent busy-waiting and allow the camera to recover.
        Stops gracefully when cancelled or the camera is released.
        """
        loop = asyncio.get_running_loop()
        try:
            while self._running and self._cap:
                ok, frame = await loop.run_in_executor(None, read_frame, self._cap)
                if ok:
                    self._frame = frame
                else:
                    await asyncio.sleep(0.03)
        except asyncio.CancelledError:
            pass

    def latest(self) -> Optional[np.ndarray]:
        """Return the most recently captured frame.

        Returns:
            Optional[np.ndarray]: The latest frame as a NumPy array, or None if
            no frame has been captured yet.
        """
        return self._frame


_shared_cam = _SharedCamera()
