# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import pytest
from fastapi.testclient import TestClient

from analyzer.main import app


def test_health_endpoint() -> None:
    """Test analyzer service health endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "analyzer"}


def test_options_offer() -> None:
    """Test CORS preflight for analyzer service."""
    client = TestClient(app)
    response = client.options("/offer")
    assert response.status_code == 204


def test_offer_returns_502_when_webcam_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that analyzer returns 502 when upstream webcam is unavailable."""
    import analyzer.routes

    class FailingSession:
        def __init__(self, offer_url: str) -> None:
            self.offer_url = offer_url

        async def connect(self):
            raise RuntimeError("upstream offline")

        async def close(self) -> None:
            pass

    monkeypatch.setattr(analyzer.routes, "WebcamSession", FailingSession)

    client = TestClient(app)
    response = client.post("/offer", json={"sdp": "v=0", "type": "offer"})
    assert response.status_code == 502
    assert "webcam" in response.json()["detail"].lower()
