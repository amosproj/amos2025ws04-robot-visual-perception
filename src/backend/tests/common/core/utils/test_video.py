# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from fractions import Fraction
from av import VideoFrame
import numpy as np
import pytest

from common.utils.video import numpy_to_video_frame


def test_numpy_to_video_frame_basic():
    frame_bgr = np.zeros((2, 2, 3), dtype=np.uint8)
    frame_bgr[0, 0] = [255, 0, 0]  # (BGR)

    pts = 42
    time_base = Fraction(1, 30)

    result = numpy_to_video_frame(frame_bgr, pts, time_base)

    assert isinstance(result, VideoFrame)

    assert result.pts == pts
    assert result.time_base == time_base

    result_array = result.to_ndarray(format="rgb24")
    assert result_array.shape == frame_bgr.shape


@pytest.mark.parametrize(
    ("platform", "first_backend_attr"),
    [
        ("win32", "CAP_DSHOW"),
        ("darwin", "CAP_AVFOUNDATION"),
        ("linux", "CAP_V4L2"),
    ],
)
@pytest.mark.skip("TODO: propery test camera opening")
def test_open_camera(monkeypatch, platform, first_backend_attr) -> None:
    return
