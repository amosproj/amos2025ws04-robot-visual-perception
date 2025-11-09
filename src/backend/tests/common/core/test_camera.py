# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import numpy as np
import pytest


@pytest.fixture
def dummy_cap():
    class DummyCap:
        def __init__(self):
            self.opened = True

        def isOpened(self):
            return True

        def read(self):
            return True, np.zeros((8, 8, 3), dtype=np.uint8)

        def release(self):
            self.opened = False

    return DummyCap()


@pytest.fixture
def camera_mod(monkeypatch, dummy_cap):
    import common.core.camera as camera

    camera._shared_cam = camera._SharedCamera()
    monkeypatch.setattr(camera, "open_camera", lambda idx: dummy_cap)
    return camera


@pytest.mark.parametrize(
    "number_of_acquires",
    [1, 2, 3],
)
@pytest.mark.asyncio
async def test_acquire_and_release(camera_mod, number_of_acquires: int):
    """Test that camera's acquire and release methods set/reset attributes correctly."""
    cam = camera_mod._shared_cam
    assert cam.latest() is None

    # Acquire N times
    for _ in range(number_of_acquires):
        await cam.acquire()

    assert cam._running is True
    assert cam._cap is not None
    assert cam._refcount == number_of_acquires
    assert cam._reader_task is not None

    # Let the read loop fetch a frame
    await asyncio.sleep(0.1)
    assert cam.latest() is not None

    # If N > 1, the first N-1 releases should NOT tear down
    for i in range(number_of_acquires - 1):
        await cam.release()
        assert cam._refcount == number_of_acquires - 1 - i
        assert cam._cap is not None
        assert cam._running is True
        assert cam._reader_task is not None

    # Last release tears everything down
    await cam.release()
    assert cam._refcount == 0
    assert cam._cap is None
    assert cam._running is False
    assert cam._reader_task is None


@pytest.mark.asyncio
async def test_acquire_propagates_open_errors(monkeypatch):
    """Test that errors raised by the open camera function are propagated."""
    import common.core.camera as camera

    camera._shared_cam = camera._SharedCamera()

    def raise_funny_error(idx):
        raise RuntimeError("Hohoho")

    monkeypatch.setattr(camera, "open_camera", raise_funny_error)

    with pytest.raises(RuntimeError, match="Hohoho"):
        await camera._shared_cam.acquire()
