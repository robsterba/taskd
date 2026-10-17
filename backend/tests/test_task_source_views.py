"""Tests for source-based task views.

GET /api/v1/tasks supports `source` and `exclude_source` filters, and
GET /api/v1/tasks/sources returns the distinct creation sources. The GUI
uses these to move integration tasks (e.g. docker-update-checker) into a
separate tab and out of the main task list.
"""


def seed_tasks(client):
    """Create tasks from a mix of sources."""
    client.post("/api/v1/tasks", json={"name": "manual task"})
    client.post(
        "/api/v1/tasks",
        json={"name": "update parent", "source": "docker-update-checker"},
    )
    # Subtask created with the parent id, carrying the same source
    parent = client.get(
        "/api/v1/tasks", params={"source": "docker-update-checker"}
    ).json()["tasks"][0]
    client.post(
        "/api/v1/tasks",
        json={
            "name": "update subtask",
            "parent_task_id": parent["id"],
            "source": "docker-update-checker",
        },
    )
    client.post(
        "/api/v1/tasks",
        json={"name": "workflow task", "source": "n8n"},
    )


def names(response):
    return sorted(t["name"] for t in response.json()["tasks"])


def test_source_filter_returns_only_that_source(client):
    seed_tasks(client)
    response = client.get(
        "/api/v1/tasks", params={"source": "docker-update-checker"}
    )
    assert response.status_code == 200
    assert names(response) == ["update parent", "update subtask"]
    assert response.json()["total"] == 2


def test_exclude_source_hides_integration_tasks(client):
    seed_tasks(client)
    response = client.get(
        "/api/v1/tasks", params={"exclude_source": "docker-update-checker"}
    )
    assert response.status_code == 200
    assert names(response) == ["manual task", "workflow task"]
    assert response.json()["total"] == 2


def test_exclude_source_accepts_multiple_values(client):
    seed_tasks(client)
    response = client.get(
        "/api/v1/tasks",
        params={"exclude_source": ["docker-update-checker", "n8n"]},
    )
    assert response.status_code == 200
    assert names(response) == ["manual task"]


def test_no_filters_returns_everything(client):
    seed_tasks(client)
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert names(response) == [
        "manual task",
        "update parent",
        "update subtask",
        "workflow task",
    ]


def test_unknown_source_returns_no_tasks(client):
    seed_tasks(client)
    response = client.get("/api/v1/tasks", params={"source": "no-such-source"})
    assert response.status_code == 200
    assert response.json()["tasks"] == []
    assert response.json()["total"] == 0


def test_sources_endpoint_lists_distinct_sources(client):
    seed_tasks(client)
    response = client.get("/api/v1/tasks/sources")
    assert response.status_code == 200
    assert response.json()["sources"] == [
        "api",
        "docker-update-checker",
        "n8n",
    ]


def test_sources_endpoint_empty_db(client):
    response = client.get("/api/v1/tasks/sources")
    assert response.status_code == 200
    assert response.json()["sources"] == []


def test_sources_endpoint_not_shadowed_by_task_id_route(client):
    """/tasks/sources must not be captured by GET /tasks/{task_id}."""
    seed_tasks(client)
    response = client.get("/api/v1/tasks/sources")
    assert response.status_code == 200
    assert "sources" in response.json()
