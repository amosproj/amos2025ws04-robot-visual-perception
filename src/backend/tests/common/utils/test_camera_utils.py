# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from unittest.mock import MagicMock, patch
import pytest

import cv2

from common.utils.camera import open_camera, compute_camera_intrinsics


@pytest.mark.parametrize(
    "platform,expected_first_backend",
    [
        ("win32", cv2.CAP_DSHOW),
        ("darwin", cv2.CAP_AVFOUNDATION),
        ("linux", cv2.CAP_V4L2),
    ],
    ids=["windows", "macos", "linux"],
)
def test_open_camera_selects_correct_backends(monkeypatch, platform, expected_first_backend):
    """Test that correct backends are selected per platform."""
    monkeypatch.setattr("sys.platform", platform)

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True

    with patch("cv2.VideoCapture", return_value=mock_cap) as mock_vc:
        result = open_camera(0)

        assert result == mock_cap
        # first backend matches expected for platform
        mock_vc.assert_called_once_with(0, expected_first_backend)


def test_open_camera_raises_when_all_backends_fail(monkeypatch):
    """Test RuntimeError when no backend can open camera."""
    monkeypatch.setattr("sys.platform", "linux")

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False  # all backends fail

    with patch("cv2.VideoCapture", return_value=mock_cap):
        with pytest.raises(RuntimeError, match="Cannot open webcam"):
            open_camera(0)

        # release was called for failed attempts
        assert mock_cap.release.called


def test_open_camera_tries_fallback_backend(monkeypatch):
    """Test that fallback backend is tried when first fails."""
    monkeypatch.setattr("sys.platform", "linux")

    # first call fails, second succeeds
    mock_cap_fail = MagicMock()
    mock_cap_fail.isOpened.return_value = False

    mock_cap_success = MagicMock()
    mock_cap_success.isOpened.return_value = True

    with patch("cv2.VideoCapture", side_effect=[mock_cap_fail, mock_cap_success]) as mock_vc:
        result = open_camera(0)

        assert result == mock_cap_success
        assert mock_vc.call_count == 2
        mock_cap_fail.release.assert_called_once()


@pytest.mark.parametrize(
    "width,height,fx,fy,cx,cy,fov_x,fov_y,expected",
    [
        (640, 480, 500.0, 500.0, 320.0, 240.0, 0.0, 0.0, (500.0, 500.0, 320.0, 240.0)),
        (640, 480, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, (0.0, 0.0, 320.0, 240.0)),
        (640, 480, 0.0, 0.0, 0.0, 0.0, 90.0, 0.0, (320.0, 320.0, 320.0, 240.0)),
        (640, 480, 0.0, 0.0, 0.0, 0.0, 90.0, 60.0, (320.0, 415.69, 320.0, 240.0)),
        (640, 480, 600.0, 0.0, 0.0, 0.0, 0.0, 0.0, (600.0, 600.0, 320.0, 240.0)),
        (640, 480, 600.0, 500.0, 0.0, 0.0, 0.0, 0.0, (600.0, 500.0, 320.0, 240.0)),
        (1920, 1080, 0.0, 0.0, 960.0, 540.0, 0.0, 0.0, (0.0, 0.0, 960.0, 540.0)),
        (100, 100, 0.0, 0.0, 0.0, 0.0, 60.0, 60.0, (86.60, 86.60, 50.0, 50.0)),
    ],
    ids=[
        "explicit_all_values",
        "no_fx_fy_defaults_center",
        "fov_x_only_fy_equals_fx",
        "both_fov_values",
        "fx_only_fy_copies_fx",
        "explicit_fx_fy",
        "explicit_cx_cy_only",
        "square_with_fov",
    ],
)
def test_compute_camera_intrinsics(
    width, height, fx, fy, cx, cy, fov_x, fov_y, expected
):
    """Test camera intrinsics computation with various input combinations."""
    result = compute_camera_intrinsics(width, height, fx, fy, cx, cy, fov_x, fov_y)
    assert result[0] == pytest.approx(expected[0], abs=0.1)
    assert result[1] == pytest.approx(expected[1], abs=0.1)
    assert result[2] == pytest.approx(expected[2], abs=0.1)
    assert result[3] == pytest.approx(expected[3], abs=0.1)


def test_compute_camera_intrinsics_min_dimensions():
    """Test that width/height are clamped to minimum of 1."""
    result = compute_camera_intrinsics(0, -5, 100.0, 100.0, 0.0, 0.0, 0.0, 0.0)
    # cx, cy should be 0.5 (1/2) since dimensions clamped to 1
    assert result[2] == 0.5
    assert result[3] == 0.5