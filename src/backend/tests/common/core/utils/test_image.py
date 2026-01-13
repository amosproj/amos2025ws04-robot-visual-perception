# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import pytest

from common.utils.image import resize_frame, calculate_adaptive_scale


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


@pytest.mark.parametrize(
    "fps, current_scale, smooth_factor, min_scale, max_scale, expected",
    [
        (5.0, 0.8, 0.1, 0.4, 1.0, 0.7),
        (12.0, 0.8, 0.1, 0.4, 1.0, 0.75),
        (20.0, 0.8, 0.1, 0.4, 1.0, 0.88),
        (5.0, 0.4, 0.1, 0.4, 1.0, 0.4),
        (30.0, 1.0, 0.1, 0.4, 1.0, 1.0),
    ],
    ids=["very_low_fps", "low_fps", "good_fps", "at_min_bound", "at_max_bound"],
)
def test_calculate_adaptive_scale(
    fps: float,
    current_scale: float,
    smooth_factor: float,
    min_scale: float,
    max_scale: float,
    expected: float,
) -> None:    
    result = calculate_adaptive_scale(
        fps, current_scale, smooth_factor, min_scale, max_scale
    )
    assert result == pytest.approx(expected, abs=0.01)
