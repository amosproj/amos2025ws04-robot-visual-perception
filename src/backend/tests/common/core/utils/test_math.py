# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import pytest
from common.utils.transforms import lerp, lerp_int, calculate_interpolation_factor


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
