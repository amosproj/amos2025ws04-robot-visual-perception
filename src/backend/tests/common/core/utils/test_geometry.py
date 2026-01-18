# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import pytest

from common.utils.geometry import get_detections, calculate_iou, normalize_bbox_coordinates
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


@pytest.mark.parametrize(
    "x1, y1, x2, y2, width, height, expected",
    [
        (10, 20, 50, 80, 100, 100, (0.1, 0.2, 0.4, 0.6)),
        (0, 0, 50, 50, 100, 100, (0.0, 0.0, 0.5, 0.5)),
        (50, 50, 150, 150, 100, 100, (0.5, 0.5, 1.0, 1.0)),
        (50, 50, 50, 100, 100, 100, (0.0, 0.0, 0.0, 0.0)),
    ],
    ids=["normal", "at_origin", "exceeds_bounds", "invalid_box"],
)
def test_normalize_bbox_coordinates(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    width: int,
    height: int,
    expected: tuple[float, float, float, float],
) -> None:
    result = normalize_bbox_coordinates(x1, y1, x2, y2, width, height)
    assert result == expected