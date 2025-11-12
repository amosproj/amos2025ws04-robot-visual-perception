# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import pytest

from common.utils.geometry import get_detections, estimate_distance_m, draw_detections
from common.config import config
from tests.test_utils import DummyResult, DummyBoxes


@pytest.mark.parametrize(
    "input_triggering_empty_list",
    [[], None, [DummyResult(None)]],
    ids=["empty_list", "none_value", "result_with_no_bboxes"],
)
def test_get_detections_returns_empty(input_triggering_empty_list) -> None:
    assert get_detections(input_triggering_empty_list) == []


@pytest.mark.parametrize(
    "xyxy, cls_ids, confs, expected",
    [
        (
            [[10, 20, 50, 60]],
            [1],
            [0.9],
            [(10, 20, 50, 60, 1, 0.9)],
        ),
        (
            [[0, 0, 10, 10], [5, 6, 15, 20], [100, 120, 140, 180]],
            [2, 3, 7],
            [0.5, 0.99, 0.42],
            [
                (0, 0, 10, 10, 2, 0.5),
                (5, 6, 15, 20, 3, 0.99),
                (100, 120, 140, 180, 7, 0.42),
            ],
        ),
        (
            np.zeros((0, 4)),
            [],
            [],
            [],
        ),
    ],
    ids=["single_detection", "multiple_detections", "no_detections"],
)
def test_get_detections(xyxy, cls_ids, confs, expected) -> None:
    boxes = DummyBoxes(xyxy=xyxy, cls=cls_ids, conf=confs)
    result = DummyResult(boxes=boxes)
    detections = get_detections([result])
    assert detections == expected


@pytest.mark.parametrize(
    "bbox, expected",
    [
        ((10, 20, 50, 60), 10.392304845413268),
    ],
)
def test_estimate_distance_m(bbox, expected, frame_width: int = 640) -> None:
    result = estimate_distance_m(
        bbox=bbox,
        frame_width=frame_width,
        fov_deg=config.CAMERA_HFOV_DEG,
        obj_width_m=config.OBJ_WIDTH_M,
        scale=config.DIST_SCALE,
    )
    assert np.isclose(result, expected, rtol=1e-6)


@pytest.mark.parametrize(
    "frame_input",
    [(100, 640, 3)],
)
def test_draw_detections_runs_and_returns_same_shape(frame_input) -> None:
    frame = np.zeros(frame_input, dtype=np.uint8)
    detections = [(10, 20, 50, 60, 1, 0.9)]

    result = draw_detections(
        frame=frame.copy(),
        detections=detections,
        fov_deg=config.CAMERA_HFOV_DEG,
        obj_width_m=config.OBJ_WIDTH_M,
        scale=config.DIST_SCALE,
    )

    assert result.shape == frame.shape
    assert result.dtype == frame.dtype
    assert not np.all(result == frame)
