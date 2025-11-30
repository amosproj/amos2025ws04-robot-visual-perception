# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import pytest
from fastapi.testclient import TestClient

from analyzer import main as analyzer_main
from common.core import depth as depth_mod
from common.core import detector as det


class _DummyDetector(det._DetectorEngine):
    def __init__(self) -> None:
        self.predict_calls = 0

    def predict(self, _frame):
        self.predict_calls += 1
        return [(0, 0, 1, 1, 0, 0.5)]


class _DummyDepth:
    def __init__(self) -> None:
        self.calls = 0

    def estimate_distance_m(self, _frame, detections):
        self.calls += 1
        return [1.0 for _ in detections]


def test_analyzer_uses_registered_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    """Analyzer lifespan should instantiate detector/depth from registered factories."""
    # Preserve global registries/singletons so we can restore after the test
    original_registry = det._backend_registry.copy()  # type: ignore[attr-defined]
    original_factory = depth_mod._depth_estimator_factory  # type: ignore[attr-defined]
    original_estimator = depth_mod._depth_estimator  # type: ignore[attr-defined]

    # Point config to custom backend and reset singletons
    monkeypatch.setattr(det.config, "DETECTOR_BACKEND", "dummy")
    det._detector_instance = None  # type: ignore[attr-defined]
    depth_mod._depth_estimator = None  # type: ignore[attr-defined]

    det.register_detector_backend("dummy", _DummyDetector)
    depth_mod.register_depth_estimator(_DummyDepth)

    app = analyzer_main.create_app()

    # TestClient triggers startup/lifespan, which should build our dummy instances
    with TestClient(app):
        detector = det.get_detector()
        depth_estimator = depth_mod.get_depth_estimator()

        assert isinstance(detector._engine, _DummyDetector)  # type: ignore[attr-defined]
        assert isinstance(depth_estimator, _DummyDepth)

    # Restore prior state to avoid leaking test changes
    det._backend_registry.clear()  # type: ignore[attr-defined]
    det._backend_registry.update(original_registry)  # type: ignore[attr-defined]
    det._detector_instance = None  # type: ignore[attr-defined]
    depth_mod.register_depth_estimator(original_factory)  # type: ignore[arg-type]
    depth_mod._depth_estimator = original_estimator  # type: ignore[attr-defined]
