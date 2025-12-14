# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import pytest

from common.utils.geometry import get_detections, draw_detections, calculate_iou
from common.core.contracts import Detection
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
            [Detection(x1=10, y1=20, x2=50, y2=60, cls_id=1, confidence=0.9)],
        ),
        (
            [[0, 0, 10, 10], [5, 6, 15, 20], [100, 120, 140, 180]],
            [2, 3, 7],
            [0.5, 0.99, 0.42],
            [
                Detection(x1=0, y1=0, x2=10, y2=10, cls_id=2, confidence=0.5),
                Detection(x1=5, y1=6, x2=15, y2=20, cls_id=3, confidence=0.99),
                Detection(x1=100, y1=120, x2=140, y2=180, cls_id=7, confidence=0.42),
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
    "frame_input",
    [(100, 640, 3)],
)
def test_draw_detections_runs_and_returns_same_shape(frame_input) -> None:
    frame = np.zeros(frame_input, dtype=np.uint8)
    detections = [Detection(x1=10, y1=20, x2=50, y2=60, cls_id=1, confidence=0.9)]
    distances_m = [1]

    result = draw_detections(
        frame=frame.copy(),
        detections=detections,
        distances_m=distances_m,
    )

    assert result.shape == frame.shape
    assert result.dtype == frame.dtype
    assert not np.all(result == frame)


@pytest.mark.parametrize(
    "box1, box2, expected_iou",
    [
        ((10, 20, 50, 60), (10, 20, 50, 60), 1.0),
        ((10, 20, 50, 60), (100, 100, 150, 160), 0.0),
        ((10, 10, 50, 50), (30, 30, 70, 70), 0.143),
        ((10, 10, 50, 50), (50, 10, 90, 50), 0.0),
        ((10, 10, 10, 10), (20, 20, 20, 20), 0.0),
    ],
    ids=[
        "perfect_overlap",
        "no_overlap",
        "partial_overlap",
        "touching_boxes",
        "zero_area_boxes",
    ],
)
def test_calculate_iou(
    box1: tuple[float, float, float, float],
    box2: tuple[float, float, float, float],
    expected_iou: float,
) -> None:
    result = calculate_iou(box1, box2)
    assert result == pytest.approx(expected_iou, abs=0.01)
