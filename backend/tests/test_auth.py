"""Tests for optional API key authentication (TASKD_API_KEY)."""
import asyncio

import pytest

from app.auth import require_api_key


@pytest.fixture
def auth_client(client, monkeypatch):
    """Client with TASKD_API_KEY set to 'test-secret-123'."""
    monkeypatch.setenv("TASKD_API_KEY", "test-secret-123")
    return client


def test_requests_rejected_without_key(auth_client):
    res = auth_client.get("/api/v1/tasks")
    assert res.status_code == 401


def test_requests_rejected_with_wrong_key(auth_client):
    res = auth_client.get("/api/v1/tasks", headers={"X-API-Key": "wrong"})
    assert res.status_code == 401


def test_requests_accepted_with_correct_key(auth_client):
    res = auth_client.get(
        "/api/v1/tasks", headers={"X-API-Key": "test-secret-123"}
    )
    assert res.status_code == 200
    assert res.json()["tasks"] == []


def test_health_and_version_bypass_auth(auth_client):
    assert auth_client.get("/api/v1/health").status_code == 200
    assert auth_client.get("/api/v1/version").status_code == 200


def test_webhooks_and_tags_protected(auth_client):
    assert auth_client.get("/api/v1/tags").status_code == 401
    assert auth_client.get("/api/v1/webhooks").status_code == 401


def test_write_endpoints_protected(auth_client):
    res = auth_client.post(
        "/api/v1/tasks", json={"name": "sneaky"}, headers={"X-API-Key": "nope"}
    )
    assert res.status_code == 401


def test_auth_disabled_when_env_unset(client, monkeypatch):
    monkeypatch.delenv("TASKD_API_KEY", raising=False)
    assert client.get("/api/v1/tasks").status_code == 200


def test_compare_digest_used(monkeypatch):
    """The dependency must use constant-time comparison."""
    import secrets

    original = secrets.compare_digest
    called = {}

    def spy(a, b):
        called["yes"] = True
        return original(a, b)

    monkeypatch.setattr(secrets, "compare_digest", spy)
    monkeypatch.setenv("TASKD_API_KEY", "k")
    asyncio.run(require_api_key(api_key="k"))
    assert called.get("yes") is True
