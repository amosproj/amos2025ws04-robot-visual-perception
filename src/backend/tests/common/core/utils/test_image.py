# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import pytest

from common.utils.image import resize_frame


@pytest.fixture
def sample_frame() -> np.ndarray:
    """Create a sample frame for testing."""
    return np.zeros((100, 200, 3), dtype=np.uint8)


@pytest.mark.parametrize(
    "scale, expected_shape, should_be_same_object",
    [
        (0.5, (50, 100, 3), False),
        (0.1, (10, 20, 3), False),
        (0.97, (97, 194, 3), False),
        (0.98, (100, 200, 3), True),
        (1.0, (100, 200, 3), True),
    ],
    ids=[
        "resize",
        "small_scale",
        "just_below_threshold",
        "at_threshold",
        "above_threshold",
    ],
)
def test_resize_frame(
    sample_frame: np.ndarray,
    scale: float,
    expected_shape: tuple[int, int, int],
    should_be_same_object: bool,
) -> None:
    result = resize_frame(sample_frame, scale=scale)

    assert result.shape == expected_shape
    if should_be_same_object:
        assert result is sample_frame
    else:
        assert result is not sample_frame
        assert result.dtype == np.uint8


@pytest.mark.parametrize(
    "original_shape, scale, expected_shape",
    [
        ((50, 75, 3), 0.4, (20, 30, 3)),
        ((100, 200), 0.5, (50, 100)),
        ((200, 400, 3), 0.25, (50, 100, 3)),
    ],
)
def test_resize_frame_different_dimensions(
    original_shape: tuple[int, ...],
    scale: float,
    expected_shape: tuple[int, ...],
) -> None:
    frame = np.zeros(original_shape, dtype=np.uint8)
    result = resize_frame(frame, scale=scale)

    assert result.shape == expected_shape
    assert result.dtype == np.uint8
