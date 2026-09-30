"""Tests for webhook registration, event dispatch, and delivery."""
import hashlib
import hmac
import json

import pytest

from app.services import webhook_service
import conftest  # the same module instance pytest loads (owns the test engine)


@pytest.fixture(autouse=True)
def isolated_dispatcher(monkeypatch):
    """Keep the worker thread out of tests and record deliveries in the test DB."""
    # Never start the real worker thread during tests
    monkeypatch.setattr("app.main.start_worker", lambda: None)
    # Worker sessions must hit the in-memory test database
    monkeypatch.setattr(webhook_service, "_session_factory", conftest.TestingSessionLocal)
    # No real HTTP, no retry delay
    monkeypatch.setattr(webhook_service, "RETRY_DELAY_SECONDS", 0.0)
    # Clear any leftover jobs from earlier tests
    with webhook_service._job_queue.mutex:
        webhook_service._job_queue.queue.clear()
    yield


class CapturedDelivery:
    def __init__(self, url, secret, body):
        self.url = url
        self.secret = secret
        self.body = body


@pytest.fixture
def capture_sends(monkeypatch):
    """Replace HTTP sends with a recorder returning 200."""
    captured = []

    def fake_send(url, secret, body):
        captured.append(CapturedDelivery(url, secret, body))
        return 200

    monkeypatch.setattr(webhook_service, "_send_webhook", fake_send)
    return captured


def register_webhook(client, url="http://receiver.example/hook", events=None, **kwargs):
    payload = {"url": url, "events": events or ["task.created"]}
    payload.update(kwargs)
    response = client.post("/api/v1/webhooks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- Registration CRUD ---


def test_create_webhook_generates_secret(client):
    webhook = register_webhook(client)
    assert webhook["url"] == "http://receiver.example/hook"
    assert webhook["active"] is True
    assert len(webhook["secret"]) >= 16


def test_create_webhook_with_explicit_secret(client):
    webhook = register_webhook(client, secret="my-secret-123")
    assert webhook["secret"] == "my-secret-123"


def test_create_webhook_rejects_bad_url(client):
    response = client.post("/api/v1/webhooks", json={"url": "ftp://x", "events": ["task.created"]})
    assert response.status_code == 422


def test_create_webhook_rejects_unknown_event(client):
    response = client.post(
        "/api/v1/webhooks",
        json={"url": "http://x", "events": ["task.exploded"]},
    )
    assert response.status_code == 422


def test_create_webhook_rejects_empty_events(client):
    response = client.post("/api/v1/webhooks", json={"url": "http://x", "events": []})
    assert response.status_code == 422


def test_list_update_delete_webhook(client):
    webhook = register_webhook(client, events=["task.created", "task.updated"])

    listed = client.get("/api/v1/webhooks").json()
    assert len(listed["webhooks"]) == 1

    patched = client.patch(
        f"/api/v1/webhooks/{webhook['id']}",
        json={"active": False, "events": ["task.deleted"]},
    )
    assert patched.status_code == 200
    assert patched.json()["active"] is False
    assert patched.json()["events"] == ["task.deleted"]

    deleted = client.delete(f"/api/v1/webhooks/{webhook['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/v1/webhooks").json()["webhooks"] == []
    assert client.get(f"/api/v1/webhooks/{webhook['id']}").status_code == 404


# --- Event dispatch ---


def test_created_event_payload_includes_subtasks(client, capture_sends):
    register_webhook(client, events=["task.created"])
    client.post("/api/v1/tasks", json={
        "name": "Disk failure on pve-2",
        "tags": ["automated", "infra"],
        "subtasks": ["Check SMART data", "Replace drive"],
    })
    webhook_service.drain_queue()

    assert len(capture_sends) == 1
    payload = json.loads(capture_sends[0].body)
    assert payload["event"] == "task.created"
    assert payload["task"]["name"] == "Disk failure on pve-2"
    assert sorted(t["name"] for t in payload["task"]["subtasks"]) == ["Check SMART data", "Replace drive"]
    for subtask in payload["task"]["subtasks"]:
        assert subtask["parent_task_id"] == payload["task"]["id"]


def test_created_event_fires_once_for_task_with_subtasks(client, capture_sends):
    register_webhook(client, events=["task.created"])
    client.post("/api/v1/tasks", json={"name": "Parent", "subtasks": ["A", "B", "C"]})
    webhook_service.drain_queue()
    assert len(capture_sends) == 1


def test_created_event_for_later_subtask(client, capture_sends):
    register_webhook(client, events=["task.created"])
    parent = client.post("/api/v1/tasks", json={"name": "Parent"}).json()
    client.post("/api/v1/tasks", json={"name": "Added later", "parent_task_id": parent["id"]})
    webhook_service.drain_queue()

    assert len(capture_sends) == 2
    second = json.loads(capture_sends[1].body)
    assert second["task"]["name"] == "Added later"
    assert second["task"]["parent_task_id"] == parent["id"]


def test_event_filtering_by_subscription(client, capture_sends):
    create_hook = register_webhook(client, url="http://a/hook", events=["task.created"])
    delete_hook = register_webhook(client, url="http://b/hook", events=["task.deleted"])

    task = client.post("/api/v1/tasks", json={"name": "Temp"}).json()
    client.delete(f"/api/v1/tasks/{task['id']}")
    webhook_service.drain_queue()

    urls = [c.url for c in capture_sends]
    assert urls.count("http://a/hook") == 1
    assert urls.count("http://b/hook") == 1
    events = [json.loads(c.body)["event"] for c in capture_sends]
    # create_hook fired on creation, delete_hook fired on deletion
    assert events[urls.index("http://a/hook")] == "task.created"
    assert events[urls.index("http://b/hook")] == "task.deleted"
    # The webhook ids exist and differ
    assert create_hook["id"] != delete_hook["id"]


def test_inactive_webhook_not_fired(client, capture_sends):
    register_webhook(client, events=["task.created"], active=False)
    client.post("/api/v1/tasks", json={"name": "Ignored"})
    assert webhook_service.drain_queue() == 0
    assert capture_sends == []


def test_patch_to_done_emits_completed_event(client, capture_sends):
    register_webhook(client, events=["task.completed", "task.updated"])
    task = client.post("/api/v1/tasks", json={"name": "T"}).json()
    client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "done"})
    webhook_service.drain_queue()

    assert len(capture_sends) == 1
    payload = json.loads(capture_sends[0].body)
    assert payload["event"] == "task.completed"
    assert payload["task"]["status"] == "done"


def test_patch_rename_emits_updated_event(client, capture_sends):
    register_webhook(client, events=["task.updated"])
    task = client.post("/api/v1/tasks", json={"name": "T"}).json()
    client.patch(f"/api/v1/tasks/{task['id']}", json={"name": "Renamed"})
    webhook_service.drain_queue()

    assert len(capture_sends) == 1
    payload = json.loads(capture_sends[0].body)
    assert payload["event"] == "task.updated"
    assert payload["task"]["name"] == "Renamed"


def test_complete_endpoint_emits_completed(client, capture_sends):
    register_webhook(client, events=["task.completed"])
    task = client.post("/api/v1/tasks", json={"name": "T"}).json()
    client.post(f"/api/v1/tasks/{task['id']}/complete")
    webhook_service.drain_queue()

    assert len(capture_sends) == 1
    payload = json.loads(capture_sends[0].body)
    assert payload["event"] == "task.completed"
    assert payload["task"]["status"] == "done"


def test_complete_recurring_emits_completed_and_created(client, capture_sends):
    task = client.post("/api/v1/tasks", json={
        "name": "Water plants",
        "recurrence": {"interval": "daily", "interval_count": 1},
        "due_date": "2026-09-28T00:00:00Z",
    }).json()
    register_webhook(client, events=["task.completed", "task.created"])
    client.post(f"/api/v1/tasks/{task['id']}/complete")
    webhook_service.drain_queue()

    events = [json.loads(c.body)["event"] for c in capture_sends]
    assert events == ["task.completed", "task.created"]
    spawned = json.loads(capture_sends[1].body)["task"]
    assert spawned["name"] == "Water plants"
    assert spawned["status"] == "todo"
    assert spawned["due_date"].startswith("2026-09-29")


def test_deleted_event_payload_has_subtasks(client, capture_sends):
    register_webhook(client, events=["task.deleted"])
    task = client.post("/api/v1/tasks", json={"name": "Parent", "subtasks": ["S1", "S2"]}).json()
    client.delete(f"/api/v1/tasks/{task['id']}")
    webhook_service.drain_queue()

    assert len(capture_sends) == 1
    payload = json.loads(capture_sends[0].body)
    assert payload["event"] == "task.deleted"
    assert payload["task"]["id"] == task["id"]
    assert [s["name"] for s in payload["task"]["subtasks"]] == ["S1", "S2"]


# --- Signature and delivery logging ---


def test_delivery_signature_header(client, capture_sends):
    webhook = register_webhook(client, secret="shared-secret-42")
    client.post("/api/v1/tasks", json={"name": "T"})
    webhook_service.drain_queue()

    assert len(capture_sends) == 1
    sent = capture_sends[0]
    expected = hmac.new(b"shared-secret-42", sent.body, hashlib.sha256).hexdigest()
    assert webhook_service.sign_payload(webhook["secret"], sent.body) == expected


def test_successful_delivery_recorded(client, capture_sends):
    webhook = register_webhook(client, events=["task.created", "task.updated"])
    task = client.post("/api/v1/tasks", json={"name": "T"}).json()
    client.patch(f"/api/v1/tasks/{task['id']}", json={"name": "T2"})
    webhook_service.drain_queue()

    response = client.get(f"/api/v1/webhooks/{webhook['id']}/deliveries")
    deliveries = response.json()["deliveries"]
    assert len(deliveries) == 2
    assert all(d["status"] == "success" for d in deliveries)
    assert all(d["response_code"] == 200 for d in deliveries)
    assert deliveries[0]["event_type"] == "task.updated"
    assert deliveries[1]["event_type"] == "task.created"


def test_failed_delivery_retries_and_records(client, monkeypatch):
    register_webhook(client, events=["task.created"])
    attempts = []

    def failing_send(url, secret, body):
        attempts.append(url)
        return 500

    monkeypatch.setattr(webhook_service, "_send_webhook", failing_send)
    client.post("/api/v1/tasks", json={"name": "T"})
    webhook_service.drain_queue()

    assert len(attempts) == webhook_service.MAX_ATTEMPTS

    webhook_id = client.get("/api/v1/webhooks").json()["webhooks"][0]["id"]
    deliveries = client.get(f"/api/v1/webhooks/{webhook_id}/deliveries").json()["deliveries"]
    assert len(deliveries) == 1
    assert deliveries[0]["status"] == "failed"
    assert deliveries[0]["response_code"] == 500
    assert deliveries[0]["attempts"] == webhook_service.MAX_ATTEMPTS


def test_connection_failure_recorded_without_response_code(client, monkeypatch):
    register_webhook(client, events=["task.created"])

    def unreachable(url, secret, body):
        return None

    monkeypatch.setattr(webhook_service, "_send_webhook", unreachable)
    client.post("/api/v1/tasks", json={"name": "T"})
    webhook_service.drain_queue()

    webhook_id = client.get("/api/v1/webhooks").json()["webhooks"][0]["id"]
    deliveries = client.get(f"/api/v1/webhooks/{webhook_id}/deliveries").json()["deliveries"]
    assert deliveries[0]["status"] == "failed"
    assert deliveries[0]["response_code"] is None


# --- Test ping ---


def test_ping_endpoint(client, capture_sends):
    webhook = register_webhook(client)
    response = client.post(f"/api/v1/webhooks/{webhook['id']}/test")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "response_code": 200}

    assert len(capture_sends) == 1
    payload = json.loads(capture_sends[0].body)
    assert payload["event"] == "webhook.test"
    assert payload["task"] is None


def test_ping_failure_reported(client, monkeypatch):
    webhook = register_webhook(client)

    def failing(url, secret, body):
        return None

    monkeypatch.setattr(webhook_service, "_send_webhook", failing)
    response = client.post(f"/api/v1/webhooks/{webhook['id']}/test")
    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_ping_unknown_webhook(client):
    assert client.post("/api/v1/webhooks/no-such-id/test").status_code == 404
