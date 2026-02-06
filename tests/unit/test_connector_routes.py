"""Tests for connector management API routes."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app


class TestConnectorRoutes:
    @pytest.fixture
    def client(self):
        app = create_app()
        return TestClient(app)

    def test_list_connectors(self, client):
        response = client.get("/api/v1/connectors")
        assert response.status_code == 200
        data = response.json()
        assert "connectors" in data
        assert len(data["connectors"]) >= 5
        names = [c["name"] for c in data["connectors"]]
        assert "salesforce" in names
        assert "zendesk" in names
        assert "slack" in names

    def test_get_connector(self, client):
        response = client.get("/api/v1/connectors/salesforce")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "salesforce"
        assert "Account" in data["supported_record_types"]

    def test_get_unknown_connector(self, client):
        response = client.get("/api/v1/connectors/unknown")
        assert response.status_code == 200
        data = response.json()
        assert data["connector_type"] == "unknown"
        assert not data["is_healthy"]

    def test_health_check(self, client):
        response = client.post("/api/v1/connectors/salesforce/health")
        assert response.status_code == 200
        data = response.json()
        assert data["connector"] == "salesforce"
        assert not data["healthy"]

    def test_trigger_sync(self, client):
        response = client.post(
            "/api/v1/connectors/sync",
            json={"connector_name": "salesforce", "record_type": "Account"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connector_name"] == "salesforce"
        assert data["status"] == "not_configured"
