import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings


@pytest.fixture
def client():
    """
    Test client fixture for sending requests to FastAPI.
    """
    return TestClient(app)


def test_root_endpoint(client):
    """
    Ensure the root endpoint returns 200 OK and valid platform metadata.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "Autonomous AI Agent Platform"
    assert data["status"] == "online"


def test_health_endpoint(client):
    """
    Ensure the health endpoint returns 200 OK and reports expected configuration.
    """
    for path in ("/health", "/api/v1/health"):
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data
        assert "llm_provider" in data
        assert data["max_rework_attempts"] == 3
        assert data["max_steps"] == 15


def test_readiness_endpoint(client):
    """
    Ensure readiness probes verify database and system readiness.
    """
    for path in ("/ready", "/api/v1/ready"):
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ready", "not_ready")
        assert "database" in data


def test_settings_singleton():
    """
    Ensure settings are cached and accessible.
    """
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
