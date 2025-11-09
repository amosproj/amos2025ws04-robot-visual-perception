# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from fractions import Fraction
from typing import Optional
import sys

import cv2
import numpy as np
from av import VideoFrame


def numpy_to_video_frame(
    frame: np.ndarray, pts: Optional[int], time_base: Optional[Fraction]
) -> VideoFrame:
    """
    Convert a numpy array (BGR format) to a WebRTC VideoFrame.

    Args:
        frame: Input frame as numpy array in BGR format
        pts: Presentation timestamp
        time_base: Time base (Fraction)

    Returns:
        VideoFrame ready for WebRTC transmission
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.uint8)
    out = VideoFrame.from_ndarray(rgb, format="rgb24")
    out.pts = pts
    out.time_base = time_base
    return out


def open_camera(idx: int) -> cv2.VideoCapture:
    """Open a webcam using platform-appropriate OpenCV backends.

    Tries multiple backends depending on the operating system (e.g., DirectShow
    on Windows, AVFoundation on macOS, V4L2 on Linux). Returns the first
    successfully opened camera. Raises an error if no backend succeeds.

    Args:
        idx (int): The index of the camera to open.

    Returns:
        cv2.VideoCapture: An opened OpenCV VideoCapture object ready for frame reads.

    Raises:
        RuntimeError: If the camera cannot be opened with any backend.
    """
    backends: list[int] = []
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


def read_frame(cap: cv2.VideoCapture) -> tuple[bool, Optional[np.ndarray]]:
    """Read a single frame from the camera in a separate thread.

    Used with run_in_executor to avoid blocking the asyncio event loop.

    Args:
        cap (cv2.VideoCapture): The opened camera capture object.

    Returns:
        Tuple[bool, Optional[np.ndarray]]: A tuple where the first element
        indicates success, and the second is the captured frame (or None if failed).
    """
    return cap.read()
