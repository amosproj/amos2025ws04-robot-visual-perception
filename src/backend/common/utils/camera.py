# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import math
import sys
from typing import Optional

import cv2
import numpy as np


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
    width: int,
    height: int,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    fov_x_deg: float,
    fov_y_deg: float,
) -> tuple[float, float, float, float]:
    """Compute camera intrinsic parameters (fx, fy, cx, cy).

    Pure utility function that calculates focal lengths and principal point.
    Uses pinhole camera model: x_pixel = fx * (X/Z) + cx

    Args:
        width: Image width in pixels (min 1)
        height: Image height in pixels (min 1)
        fx: Focal length in x direction (pixels).
        fy: Focal length in y direction (pixels).
        cx: Principal point x coordinate (pixels).
        cy: Principal point y coordinate (pixels).
        fov_x_deg: Horizontal field of view in degrees.
        fov_y_deg: Vertical field of view in degrees.

    Returns:
        Tuple of (fx, fy, cx, cy) in pixels where:
            fx, fy: Focal lengths
            cx, cy: Principal point (defaults to image center)

    Priority order:
        1. Explicit fx/fy/cx/cy if provided (> 0)
        2. FOV-based calculation for fx/fy
        3. Defaults (cx = width/2, cy = height/2, fy = fx)

    Note:
        If no fx/fy or FOV provided, focal lengths will be 0.0 (see config)
    """
    width = max(1, int(width))
    height = max(1, int(height))

    # Derive fx/fy from field of view when not explicitly provided
    if fx <= 0 and fov_x_deg > 0:
        fx = width / (2.0 * math.tan(math.radians(fov_x_deg) / 2.0))
    if fy <= 0:
        if fov_y_deg > 0:
            fy = height / (2.0 * math.tan(math.radians(fov_y_deg) / 2.0))
        else:
            fy = fx

    # Principal point defaults to image center
    if cx <= 0:
        cx = width / 2.0
    if cy <= 0:
        cy = height / 2.0

    return float(fx), float(fy), float(cx), float(cy)
