# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from pathlib import Path
import types

import numpy as np
import pytest
import torch

import common.core.depth as depth


class _DummyDepthEstimator:
    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir
        self.calls = 0

    def estimate_distance_m(self, frame_rgb, detections):
        self.calls += 1
        return [42.0 for _ in detections]


def test_depth_backend_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """DEPTH_BACKEND should map to a registered factory."""
    monkeypatch.setattr(depth, "_backend_registry", {})
    depth.register_depth_backend("dummy", _DummyDepthEstimator)
    monkeypatch.setattr(depth.config, "DEPTH_BACKEND", "dummy")
    monkeypatch.setattr(depth, "_depth_estimator", None)
    monkeypatch.setattr(
        depth,
        "_depth_estimator_factory",
        depth._default_depth_estimator_factory,  # type: ignore[attr-defined]
    )

    estimator = depth.get_depth_estimator(Path("/tmp/cache"))
    assert isinstance(estimator, _DummyDepthEstimator)
    assert estimator.cache_dir == Path("/tmp/cache")
    assert estimator.estimate_distance_m(
        np.zeros((1, 1, 3)), [(0, 0, 0, 0, 0, 0.0)]
    ) == [42.0]


def test_unknown_depth_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown DEPTH_BACKEND should surface a clear error."""
    monkeypatch.setattr(depth.config, "DEPTH_BACKEND", "missing")
    with pytest.raises(ValueError):
        depth._default_depth_estimator_factory()  # type: ignore[attr-defined]


def test_onnx_depth_estimator_runs_with_mock_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dummy_output = np.ones((1, 1, 2, 2), dtype=np.float32)

    class DummySessionOptions:
        def __init__(self) -> None:
            self.enable_mem_pattern = False
            self.graph_optimization_level = None

    class DummySession:
        def __init__(self, *_args, **_kwargs) -> None:
            self._inputs = [types.SimpleNamespace(name="input")]
            self._outputs = [types.SimpleNamespace(name="output")]

        def get_inputs(self):
            return self._inputs

        def get_outputs(self):
            return self._outputs

        def run(self, _output_names, _inputs):
            return [dummy_output]

    dummy_ort = types.SimpleNamespace(
        SessionOptions=DummySessionOptions,
        GraphOptimizationLevel=types.SimpleNamespace(ORT_ENABLE_ALL="all"),
        InferenceSession=DummySession,
        get_available_providers=lambda: ["CPUExecutionProvider"],
    )

    monkeypatch.setattr(depth, "ort", dummy_ort)
    monkeypatch.setattr(depth.config, "MIDAS_ONNX_PROVIDERS", [])
    monkeypatch.setattr(depth.config, "ONNX_PROVIDERS", [])

    def mock_hub_load(repo, what, trust_repo=True):
        if what == "transforms":

            class DummyTransforms:
                def __init__(self) -> None:
                    self.small_transform = self._small_transform
                    self.dpt_transform = self.small_transform

                @staticmethod
                def _small_transform(_image):
                    return torch.ones((1, 3, 2, 2), dtype=torch.float32)

            return DummyTransforms()
        raise AssertionError(f"Unexpected torch.hub.load call: {what}")

    monkeypatch.setattr(depth.torch.hub, "load", mock_hub_load)
    onnx_path = tmp_path / "midas.onnx"
    onnx_path.write_text("fake")

    estimator = depth.OnnxMiDasDepthEstimator(
        onnx_model_path=onnx_path,
        model_type="MiDaS_small",
        midas_model="intel-isl/MiDaS",
    )
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    dets = [(0, 0, 1, 1, 0, 0.9)]

    distances = estimator.estimate_distance_m(frame, dets)
    assert distances and distances[0] == pytest.approx(depth.config.SCALE_FACTOR)
