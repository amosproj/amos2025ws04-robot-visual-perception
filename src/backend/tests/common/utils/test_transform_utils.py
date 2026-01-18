# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import pytest

from common.utils.transforms import (
    resize_frame,
    calculate_adaptive_scale,
    letterbox,
    scale_boxes,
    lerp,
    lerp_int,
    calculate_interpolation_factor,
)


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


@pytest.mark.parametrize(
    "val1, val2, t, expected",
    [
        (10.8, 20.0, 0.0, 10.8),
        (10.0, 20.0, 1.0, 20.0),
        (10.2, 20.0, 0.5, 15.1),
        (10.0, 20.0, 1.5, 25.0),
        (10.5, 20.0, -0.5, 5.75),
    ],
)
def test_lerp_and_lerp_int(val1: float, val2: float, t: float, expected: float) -> None:
    assert lerp(val1, val2, t) == expected
    assert lerp_int(val1, val2, t) == int(round(expected))


@pytest.mark.parametrize(
    "frame1, frame2, target, clamp_max, expected",
    [
        (10, 10, 15, None, 0.0),
        (10, 20, 15, None, 0.5),
        (10, 20, 25, None, 1.5),
        (10, 20, 5, None, 0.0),
        (10, 20, 30, 2.0, 2.0),
    ],
    ids=[
        "same_frames",
        "midpoint",
        "forward_extrapolation",
        "backward extrapolation",
        "custom_clamp_max",
    ],
)
def test_calculate_interpolation_factor(
    frame1: int,
    frame2: int,
    target: int,
    clamp_max: float | None,
    expected: float,
) -> None:
    if clamp_max is None:
        result = calculate_interpolation_factor(frame1, frame2, target)
    else:
        result = calculate_interpolation_factor(
            frame1, frame2, target, clamp_max=clamp_max
        )

    assert result == expected


@pytest.mark.parametrize(
    "input_shape,new_size,expected_output_shape,expected_scale",
    [
        ((100, 100, 3), 200, (200, 200, 3), 2.0),
        ((100, 200, 3), 200, (200, 200, 3), 1.0),
        ((200, 100, 3), 200, (200, 200, 3), 1.0),
        ((50, 100, 3), 200, (200, 200, 3), 2.0),
        ((400, 300, 3), 200, (200, 200, 3), 0.5),
        ((100, 100, 3), 100, (100, 100, 3), 1.0),
    ],
    ids=[
        "square_upscale",
        "wide_image",
        "tall_image",
        "wide_upscale",
        "downscale",
        "same_size",
    ],
)
def test_letterbox(
    input_shape: tuple[int, int, int],
    new_size: int,
    expected_output_shape: tuple[int, int, int],
    expected_scale: float,
) -> None:
    """Test letterbox resizing with aspect ratio preservation."""
    image = np.zeros(input_shape, dtype=np.uint8)
    result, scale, offset = letterbox(image, new_size)
    assert result.shape == expected_output_shape
    assert scale == pytest.approx(expected_scale, abs=0.01)
    assert isinstance(offset, tuple)
    assert len(offset) == 2


def test_letterbox_padding_color() -> None:
    """Test that letterbox uses correct padding color."""
    image = np.ones((100, 200, 3), dtype=np.uint8) * 255 
    custom_color = (50, 100, 150)
    result, _, (dw, dh) = letterbox(image, 200, color=custom_color)
    # Check padding area has the custom color
    if dh > 0:
        # Top padding row
        assert np.allclose(result[0, int(dw):int(200-dw), :], custom_color)