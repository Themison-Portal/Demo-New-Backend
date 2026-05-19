"""
Health / status endpoint tests.
"""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_DISABLED", "true")

from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestHealthEndpoints:
    """Test basic health/status endpoints."""

    def test_root_endpoint(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"

    def test_docs_endpoint(self, client: TestClient):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema(self, client: TestClient):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "info" in data
