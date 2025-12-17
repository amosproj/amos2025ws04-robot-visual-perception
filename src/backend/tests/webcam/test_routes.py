# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from fastapi.testclient import TestClient

from streamer.main import app


def test_health_endpoint() -> None:
    """Test webcam service health endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "ok"
    assert response_json["service"] == "streamer"
    assert response_json["source_type"] in ("webcam", "file")


def test_options_offer() -> None:
    """Test CORS preflight for webcam service."""
    client = TestClient(app)
    response = client.options("/offer")
    assert response.status_code == 204


def test_offer_requires_offer_type() -> None:
    """Test that /offer endpoint requires type='offer'."""
    client = TestClient(app)
    response = client.post("/offer", json={"sdp": "v=0", "type": "answer"})
    assert response.status_code == 400
    assert "must be 'offer'" in response.json()["detail"].lower()
