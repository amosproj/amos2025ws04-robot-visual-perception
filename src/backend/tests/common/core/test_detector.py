# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from pathlib import Path
import types
from typing import Optional

import numpy as np
import pytest
from tests.test_utils import DummyBoxes, DummyResult

import common.core.detector as det
from .conftest import DummySession, DummySessionOptions


@pytest.fixture
def torch_detector(monkeypatch, tmp_path):
    weights = tmp_path / "dummy.pt"
    weights.write_text("fake")

    class DummyYOLO:
        def __init__(self, *_args, **_kwargs):
            self.calls = 0

        def predict(self, *_args, **_kwargs):
            self.calls += 1
            boxes = DummyBoxes(
                xyxy=[[10, 20, 50, 60]],
                cls=[1],
                conf=[0.9],
            )
            return [DummyResult(boxes)]

    monkeypatch.setattr(det, "YOLO", DummyYOLO)
    monkeypatch.setattr(det.config, "MODEL_PATH", weights)
    monkeypatch.setattr(det.config, "TORCH_DEVICE", "cpu")
    monkeypatch.setattr(det.config, "TORCH_HALF_PRECISION", "false")
    monkeypatch.setattr(det.config, "DETECTOR_BACKEND", "torch")

    detector = det._Detector(backend="torch")
    return detector


@pytest.mark.asyncio
async def test_infer_returns_detections(torch_detector):
    """infer() should return tuples (x1,y1,x2,y2,class_id,conf) with correct types."""
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    assert torch_detector._last_det is None
    assert torch_detector._last_time == 0.0
    detections = await torch_detector.infer(frame)
    assert isinstance(detections, list)
    assert len(detections) == 1
    x1, y1, x2, y2, cls_id, conf = detections[0]

    assert (x1, y1, x2, y2) == (10, 20, 50, 60)
    assert cls_id == 1
    assert pytest.approx(conf, rel=1e-3) == 0.9

    # cache hit path should not run extra inference
    detections_cached = await torch_detector.infer(frame)
    assert detections_cached == detections
    assert torch_detector._engine._model.calls == 1


@pytest.mark.asyncio
async def test_infer_with_onnx_backend(monkeypatch, tmp_path):
    import common.core.detector as det

    onnx_path = tmp_path / "dummy.onnx"
    onnx_path.write_text("fake")

    dummy_output = np.array([[[2.0, 2.0, 2.0, 2.0, 0.95]]], dtype=np.float32)

    dummy_ort = types.SimpleNamespace(
        SessionOptions=lambda: DummySessionOptions(enable_mem_pattern=True),
        GraphOptimizationLevel=types.SimpleNamespace(ORT_ENABLE_ALL="all"),
        InferenceSession=lambda *_args, **_kwargs: DummySession(
            dummy_output, input_name="images", output_name="output"
        ),
        get_available_providers=lambda: ["CPUExecutionProvider"],
    )

    monkeypatch.setattr(det, "ort", dummy_ort)
    monkeypatch.setattr(det.config, "DETECTOR_BACKEND", "onnx")
    monkeypatch.setattr(det.config, "ONNX_MODEL_PATH", onnx_path)
    monkeypatch.setattr(det.config, "DETECTOR_IMAGE_SIZE", 4)
    monkeypatch.setattr(det.config, "DETECTOR_CONF_THRESHOLD", 0.5)
    monkeypatch.setattr(det.config, "DETECTOR_IOU_THRESHOLD", 0.5)
    monkeypatch.setattr(det.config, "DETECTOR_MAX_DETECTIONS", 10)
    monkeypatch.setattr(det.config, "DETECTOR_NUM_CLASSES", 1)
    monkeypatch.setattr(det.config, "ONNX_PROVIDERS", [])

    detector = det._Detector(backend="onnx")
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    detections = await detector.infer(frame)

    assert len(detections) == 1
    x1, y1, x2, y2, cls_id, conf = detections[0]
    assert (x1, y1, x2, y2) == (1, 1, 3, 3)
    assert cls_id == 0
    assert pytest.approx(conf, rel=1e-3) == 0.95


@pytest.mark.asyncio
async def test_register_detector_backend():
    import common.core.detector as det

    class DummyBackend(det._DetectorEngine):
        def __init__(self, model_path: Optional[Path] = None) -> None:
            pass

        def predict(self, frame_rgb):
            return [(1, 2, 3, 4, 5, 0.8)]

    det.register_detector_backend("dummy", DummyBackend)
    detector = det._Detector(backend="dummy")

    detections = await detector.infer(np.zeros((2, 2, 3), dtype=np.uint8))
    assert detections == [(1, 2, 3, 4, 5, 0.8)]
