# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from fractions import Fraction
from av import VideoFrame
import numpy as np
import pytest


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
