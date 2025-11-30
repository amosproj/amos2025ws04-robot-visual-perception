# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

from fastapi.testclient import TestClient

from analyzer.main import app


def test_health_endpoint() -> None:
    """Test analyzer service health endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "analyzer"}