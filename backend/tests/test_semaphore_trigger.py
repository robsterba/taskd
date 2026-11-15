"""Semaphore trigger integration for docker-update-checker completions."""

import pytest

from app.services import semaphore_service

DUC = "docker-update-checker"
MOXY_PARENT = "Container updates: moxy"
RXPS_PARENT = "Container updates: rxps"


@pytest.fixture
def semaphore_env(monkeypatch):
    """Enable the Semaphore integration against a fake endpoint."""
    monkeypatch.setenv("SEMAPHORE_URL", "http://semaphore.test")
    monkeypatch.setenv("SEMAPHORE_API_TOKEN", "test-token")
    monkeypatch.setenv("SEMAPHORE_PROJECT", "1")
    monkeypatch.setenv("SEMAPHORE_HOSTS", "boxy,moxy,foxy")


@pytest.fixture
def duc_family(client):
    """A DUC parent for moxy with one image subtask; returns (parent, sub)."""
    parent = client.post(
        "/api/v1/tasks",
        json={
            "name": MOXY_PARENT,
            "description": "Host: moxy\nOutdated images: 1",
            "source": DUC,
        },
        headers={"source": DUC},
    ).json()
    sub = client.post(
        "/api/v1/tasks",
        json={
            "name": "Update ghcr.io/immich-app/immich-server:release",
            "description": (
                "Image: ghcr.io/immich-app/immich-server:release\n"
                "Local digest: aaaa\nRemote digest: bbbb\n"
                "Stacks: immich\nCompose files: immich/docker-compose.yml"
            ),
            "parent_task_id": parent["id"],
            "source": DUC,
        },
        headers={"source": DUC},
    ).json()
    return parent, sub


class FakeSemaphore:
    """Records trigger calls; template list is configurable per test."""

    def __init__(self, templates):
        self.templates = templates
        self.created = []

    def fetch(self, settings):
        return self.templates

    def create(self, settings, template_id):
        self.created.append(template_id)
        return {"id": 900 + len(self.created)}


@pytest.fixture
def patch_transport(monkeypatch):
    """Return a setter that wires a FakeSemaphore into the service."""

    def install(templates):
        fake = FakeSemaphore(templates)

        def fetch(settings):
            return fake.fetch(settings)

        def create(settings, template_id):
            return fake.create(settings, template_id)

        monkeypatch.setattr(semaphore_service, "_fetch_templates", fetch)
        monkeypatch.setattr(semaphore_service, "_create_task", create)
        return fake

    return install


STACK_TEMPLATES = [
    {"id": 11, "name": "Stack update - moxy"},
    {"id": 21, "name": "Stack update - moxy:immich"},
    {"id": 22, "name": "Stack update - moxy:n8n"},
]


def test_gui_subtask_completion_triggers_per_stack_template(
    client, semaphore_env, duc_family, patch_transport
):
    fake = patch_transport(STACK_TEMPLATES)
    parent, sub = duc_family

    response = client.patch(f"/api/v1/tasks/{sub['id']}", json={"status": "done"})

    assert response.status_code == 200
    assert fake.created == [21]


def test_duc_initiated_completion_does_not_trigger(
    client, duc_family, patch_transport, semaphore_env
):
    fake = patch_transport(STACK_TEMPLATES)
    parent, sub = duc_family

    response = client.post(
        f"/api/v1/tasks/{sub['id']}/complete", headers={"source": DUC}
    )

    assert response.status_code == 200
    assert fake.created == []


def test_unconfigured_integration_completes_without_trigger(
    client, monkeypatch, duc_family
):
    # No SEMAPHORE_* env vars: integration disabled entirely
    monkeypatch.delenv("SEMAPHORE_URL", raising=False)
    monkeypatch.delenv("SEMAPHORE_API_TOKEN", raising=False)

    parent, sub = duc_family

    response = client.patch(f"/api/v1/tasks/{sub['id']}", json={"status": "done"})

    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_trigger_failure_blocks_completion(
    client, semaphore_env, duc_family, patch_transport
):
    parent, sub = duc_family

    # Semaphore reachable but has no matching template -> 502
    patch_transport([])
    response = client.patch(f"/api/v1/tasks/{sub['id']}", json={"status": "done"})

    assert response.status_code == 502
    assert "No Semaphore template" in response.json()["detail"]

    # The task must still be open
    detail = client.get(f"/api/v1/tasks/{sub['id']}").json()
    assert detail["status"] != "done"


def test_semaphore_unreachable_blocks_completion(client, semaphore_env, duc_family):
    parent, sub = duc_family

    # Real transport against an unresolvable host -> 502, also blocking
    response = client.patch(f"/api/v1/tasks/{sub['id']}", json={"status": "done"})

    assert response.status_code == 502
    assert "unreachable" in response.json()["detail"]
    assert client.get(f"/api/v1/tasks/{sub['id']}").json()["status"] != "done"


def test_multiple_stacks_trigger_each(
    client, semaphore_env, duc_family, patch_transport
):
    parent, sub = duc_family
    client.patch(
        f"/api/v1/tasks/{sub['id']}",
        json={"description": "Stacks: immich, n8n\n"},
    )
    fake = patch_transport(STACK_TEMPLATES)

    response = client.patch(f"/api/v1/tasks/{sub['id']}", json={"status": "done"})

    assert response.status_code == 200
    assert fake.created == [21, 22]


def test_host_parent_completion_triggers_host_template(
    client, semaphore_env, duc_family, patch_transport
):
    fake = patch_transport(STACK_TEMPLATES)
    parent, sub = duc_family

    response = client.patch(f"/api/v1/tasks/{parent['id']}", json={"status": "done"})

    assert response.status_code == 200
    assert fake.created == [11]


def test_unlisted_host_completes_without_trigger(
    client, monkeypatch, semaphore_env, patch_transport
):
    fake = patch_transport(STACK_TEMPLATES)
    monkeypatch.setenv("SEMAPHORE_HOSTS", "boxy,moxy,foxy")

    parent = client.post(
        "/api/v1/tasks",
        json={
            "name": RXPS_PARENT,
            "description": "Host: rxps\nOutdated images: 0",
            "source": DUC,
        },
        headers={"source": DUC},
    ).json()

    response = client.patch(f"/api/v1/tasks/{parent['id']}", json={"status": "done"})

    assert response.status_code == 200
    assert fake.created == []


def test_missing_stacks_metadata_blocked_with_hint(
    client, semaphore_env, patch_transport
):
    patch_transport(STACK_TEMPLATES)
    parent = client.post(
        "/api/v1/tasks",
        json={
            "name": MOXY_PARENT,
            "description": "Host: moxy\nOutdated images: 1",
            "source": DUC,
        },
        headers={"source": DUC},
    ).json()
    sub = client.post(
        "/api/v1/tasks",
        json={
            "name": "Update some/image:latest",
            "description": "Image: some/image:latest\nLocal digest: a",
            "parent_task_id": parent["id"],
            "source": DUC,
        },
        headers={"source": DUC},
    ).json()

    response = client.patch(f"/api/v1/tasks/{sub['id']}", json={"status": "done"})

    assert response.status_code == 502
    assert "stack metadata" in response.json()["detail"]
    assert client.get(f"/api/v1/tasks/{sub['id']}").json()["status"] != "done"


def test_uncompleting_never_triggers(
    client, semaphore_env, duc_family, patch_transport
):
    """Done subtask + PATCH status todo (reopen) must not trigger a job."""
    fake = patch_transport(STACK_TEMPLATES)
    parent, sub = duc_family

    # Seed a done subtask via the exempt path
    client.post(f"/api/v1/tasks/{sub['id']}/complete", headers={"source": DUC})

    response = client.patch(f"/api/v1/tasks/{sub['id']}", json={"status": "todo"})

    assert response.status_code == 200
    assert fake.created == []


def test_non_duc_task_completion_never_triggers(client, semaphore_env, patch_transport):
    """Plain GUI-managed tasks are never deployment triggers."""
    fake = patch_transport(STACK_TEMPLATES)
    task = client.post("/api/v1/tasks", json={"name": "Write the readme"}).json()

    response = client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "done"})

    assert response.status_code == 200
    assert fake.created == []
