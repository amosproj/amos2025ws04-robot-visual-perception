# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

from fastapi.testclient import TestClient

from server import app


def test_health_endpoint_reports_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_options_offer_returns_204() -> None:
    client = TestClient(app)
    response = client.options("/offer")
    assert response.status_code == 204
