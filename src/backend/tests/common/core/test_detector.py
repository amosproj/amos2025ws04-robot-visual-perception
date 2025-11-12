# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import pytest
from tests.test_utils import DummyResult, DummyBoxes


@pytest.fixture
def detector_mod(monkeypatch, tmp_path):
    class DummyYOLO:
        def __init__(self, *_args, **_kwargs):
            return

        def predict(self, rgb, imgsz=640, conf=0.25, verbose=False):
            boxes = DummyBoxes(
                xyxy=[[10, 20, 50, 60]],
                cls=[1],
                conf=[0.9],
            )
            return [DummyResult(boxes)]

    import common.core.detector as det

    monkeypatch.setattr(det, "YOLO", DummyYOLO)
    det._detector = det._Detector()
    return det


@pytest.mark.asyncio
async def test_infer_returns_detections(detector_mod):
    """infer() should return tuples (x1,y1,x2,y2,class_id,conf) with correct types."""
    frame = np.zeros((100, 200, 3), dtype=np.uint8)  # BGR

    assert detector_mod._detector._last_det is None
    assert detector_mod._detector._last_time == 0.0

    detections = await detector_mod._detector.infer(frame)

    assert isinstance(detections, list)
    assert len(detections) == 1
    x1, y1, x2, y2, cls_id, conf = detections[0]

    # Type checks
    assert all(isinstance(v, int) for v in (x1, y1, x2, y2, cls_id))
    assert isinstance(conf, float)

    # Value checks (from dummy)
    assert (x1, y1, x2, y2) == (10, 20, 50, 60)
    assert cls_id == 1
    assert 0.89 < conf < 0.91

    # Last det and time should be set
    assert detector_mod._detector._last_det == detections
    assert detector_mod._detector._last_time is not None
