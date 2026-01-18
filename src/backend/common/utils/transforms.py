# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import cv2


def letterbox(
    image: np.ndarray,
    new_size: int,
    color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize image to a square (new_size×new_size) while preserving aspect ratio.

    The image is scaled to fit inside the target size, then padded equally on
    both sides (as much as possible) using `color`.

    Args:
        image: Input image (H×W×C).
        new_size: Target square size.
        color: Padding color (BGR for OpenCV).

    Returns:
        padded: Padded image of shape (new_size, new_size, C).
        scale: Scale factor applied to the original image.
        offset: Padding offset (dw/2, dh/2) in pixels.
    """
    shape = image.shape[:2]  # (h, w)
    scale = min(new_size / shape[0], new_size / shape[1])
    new_unpad = (int(round(shape[1] * scale)), int(round(shape[0] * scale)))
    resized = cv2.resize(image, new_unpad, interpolation=cv2.INTER_LINEAR)

    dw = new_size - new_unpad[0]
    dh = new_size - new_unpad[1]
    top = int(np.floor(dh / 2))
    bottom = int(np.ceil(dh / 2))
    left = int(np.floor(dw / 2))
    right = int(np.ceil(dw / 2))

    resized = cv2.copyMakeBorder(
        resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
    )
    return resized, scale, (dw / 2, dh / 2)


def scale_boxes(
    boxes: np.ndarray,
    ratio: float,
    dwdh: tuple[float, float],
    original_hw: tuple[int, int],
) -> np.ndarray:
    """Map bounding boxes from letterboxed image coordinates back to the original image.

    Args:
        boxes: Array of bounding boxes in xyxy format (N×4 or N×M), where the first
            4 columns are [x1, y1, x2, y2] in the letterboxed image coordinate space.
        ratio: Resize scale factor returned by `letterbox()`.
        dwdh: Padding offset (dw/2, dh/2) returned by `letterbox()`, in pixels.
        original_hw: Original image size as (height, width).

    Returns:
        Bounding boxes in the original image coordinate space, with x clipped to
        [0, width-1] and y clipped to [0, height-1].
    """
    boxes = boxes.copy()
    boxes[:, [0, 2]] -= dwdh[0]
    boxes[:, [1, 3]] -= dwdh[1]
    boxes[:, :4] /= max(ratio, 1e-6)

    h, w = original_hw
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, max(w - 1, 0))
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, max(h - 1, 0))
    return boxes


def resize_frame(frame: np.ndarray, scale: float) -> np.ndarray:
    """Resize frame by a scale factor.

    Args:
        frame: Input frame as numpy array
        scale: Scale factor (0.0-1.0). If >= 0.98, returns original frame.

    Returns:
        Resized frame or original if scale >= 0.98
    """
    if scale < 0.98:
        new_w = int(frame.shape[1] * scale)
        new_h = int(frame.shape[0] * scale)
        return cv2.resize(frame, (new_w, new_h))
    return frame


def calculate_adaptive_scale(
    current_fps: float,
    current_scale: float,
    smooth_factor: float,
    min_scale: float,
    max_scale: float,
) -> float:
    """Calculate adaptive scaling based on FPS.

    Args:
        current_fps: Current frames per second
        current_scale: Current scale factor
        smooth_factor: Smoothing factor for scale adjustments
        min_scale, max_scale: Scale bounds

    Returns:
        New scale factor
    """
    if current_fps < 10:
        new_scale = current_scale - smooth_factor
    elif current_fps < 18:
        new_scale = current_scale - smooth_factor * 0.5
    else:
        new_scale = current_scale + smooth_factor * 0.8

    return max(min_scale, min(max_scale, new_scale))


def lerp(val1: float, val2: float, t: float) -> float:
    """Linear interpolation between two values.

    Args:
        value1: Start value
        value2: End value
        t: Interpolation factor (0.0 = value1, 1.0 = value2)

    Returns:
        Interpolated value
    """
    return val1 + (val2 - val1) * t


def lerp_int(value1: int, value2: int, t: float) -> int:
    """Linear interpolation between two integer values, rounded to int.

    Args:
        value1: Start value (int)
        value2: End value (int)
        t: Interpolation factor (0.0 = value1, 1.0 = value2)

    Returns:
        Interpolated value rounded to int
    """
    return int(round(lerp(value1, value2, t)))


def calculate_interpolation_factor(
    frame1: int, frame2: int, target_frame: int, clamp_max: float = 1.5
) -> float:
    """Calculate interpolation factor t between two frames.

    Args:
        frame1: Start frame ID
        frame2: End frame ID
        target_frame: Target frame ID to interpolate for
        clamp_max: Maximum value for t (default 1.5 for extrapolation)

    Returns:
        Interpolation factor t (0.0 = frame1, 1.0 = frame2, >1.0 = extrapolation)
    """
    if frame1 == frame2:
        return 0.0
    t = (target_frame - frame1) / (frame2 - frame1)
    return max(0.0, min(clamp_max, t))
