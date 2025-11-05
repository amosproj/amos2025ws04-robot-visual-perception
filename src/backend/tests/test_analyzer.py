# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib
import sys
import types

import numpy as np
import pytest
from fastapi.testclient import TestClient


# Pytest fixtures
@pytest.fixture
def analyzer_module(monkeypatch: pytest.MonkeyPatch):
    dummy_module = types.ModuleType("ultralytics")

    class DummyBoxes:
        def __init__(self) -> None:
            self.xyxy = np.zeros((0, 4))
            self.cls = np.zeros((0,), dtype=int)
            self.conf = np.zeros((0,), dtype=float)

    class DummyResult:
        boxes = DummyBoxes()

    class DummyYOLO:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def predict(self, *args, **kwargs):
            return [DummyResult()]

    dummy_module.YOLO = DummyYOLO
    monkeypatch.setitem(sys.modules, "ultralytics", dummy_module)

    sys.modules.pop("analyzer", None)
    analyzer = importlib.import_module("analyzer")
    return analyzer


def test_health_endpoint_returns_ok(analyzer_module) -> None:
    client = TestClient(analyzer_module.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_offer_returns_502_when_webcam_unavailable(
    analyzer_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailingSession:
        def __init__(self, offer_url: str) -> None:
            self.offer_url = offer_url

        async def connect(self):
            raise RuntimeError("upstream offline")

        async def close(self) -> None:
            pass

    monkeypatch.setattr(analyzer_module, "_WebcamSession", FailingSession)

    client = TestClient(analyzer_module.app)
    response = client.post("/offer", json={"sdp": "v=0", "type": "offer"})
    assert response.status_code == 502
    assert "webcam" in response.json()["detail"].lower()
