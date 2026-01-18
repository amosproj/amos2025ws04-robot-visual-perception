# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from typing import Optional
import sys

import math
import cv2
import numpy as np

from common.config import config


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


def compute_camera_intrinsics(
    width: int, height: int
) -> tuple[float, float, float, float]:
    """Compute camera intrinsic parameters (fx, fy, cx, cy).

    Calculates focal lengths and principal point using config values or FOV-based
    fallbacks. Uses pinhole camera model: x_pixel = fx * (X/Z) + cx

    Args:
        width: Image width in pixels (min 1)
        height: Image height in pixels (min 1)

    Returns:
        Tuple of (fx, fy, cx, cy) in pixels where:
            fx, fy: Focal lengths
            cx, cy: Principal point (defaults to image center)

    Priority order:
        1. Explicit config (CAMERA_FX, CAMERA_FY, CAMERA_CX, CAMERA_CY)
        2. FOV-based calculation (CAMERA_FOV_X_DEG, CAMERA_FOV_Y_DEG)
        3. Defaults (cx = width/2, cy = height/2, fy = fx)

    Note:
        If no fx/fy or FOV provided, focal lengths will be 0.0
    """
    fx = getattr(config, "CAMERA_FX", 0.0)
    fy = getattr(config, "CAMERA_FY", 0.0)
    cx = getattr(config, "CAMERA_CX", 0.0)
    cy = getattr(config, "CAMERA_CY", 0.0)
    fov_x = getattr(config, "CAMERA_FOV_X_DEG", 0.0)
    fov_y = getattr(config, "CAMERA_FOV_Y_DEG", 0.0)

    width = max(1, int(width))
    height = max(1, int(height))

    # Derive fx/fy from field of view when not explicitly provided
    if fx <= 0 and fov_x > 0:
        fx = width / (2.0 * math.tan(math.radians(fov_x) / 2.0))
    if fy <= 0:
        if fov_y > 0:
            fy = height / (2.0 * math.tan(math.radians(fov_y) / 2.0))
        else:
            fy = fx

    # Principal point defaults to image center
    if cx <= 0:
        cx = width / 2.0
    if cy <= 0:
        cy = height / 2.0

    return float(fx), float(fy), float(cx), float(cy)
