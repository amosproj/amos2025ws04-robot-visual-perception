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
    """Resize image with unchanged aspect ratio using padding."""
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
    """Rescale padded model-output boxes back to the original image dimensions."""
    boxes = boxes.copy()
    boxes[:, [0, 2]] -= dwdh[0]
    boxes[:, [1, 3]] -= dwdh[1]
    boxes[:, :4] /= max(ratio, 1e-6)

    h, w = original_hw
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, max(w - 1, 0))
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, max(h - 1, 0))
    return boxes
