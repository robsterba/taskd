"""Regression tests for tag filtering in GET /api/v1/tasks.

A query for tags must use AND semantics across all requested tags, and
filtering by a tag that does not exist must return NO results — not the
unfiltered task list. (The empty-tag_ids case previously skipped
filtering entirely and returned every task in the database.)
"""


def seed_tasks(client):
    """Create three tasks with distinct tag sets."""
    client.post("/api/v1/tasks", json={"name": "alpha only", "tags": ["alpha"]})
    client.post(
        "/api/v1/tasks", json={"name": "alpha and beta", "tags": ["alpha", "beta"]}
    )
    client.post("/api/v1/tasks", json={"name": "gamma", "tags": ["gamma"]})
    client.post("/api/v1/tasks", json={"name": "untagged"})


def names(response):
    return sorted(t["name"] for t in response.json()["tasks"])


def test_no_tag_filter_returns_all(client):
    seed_tasks(client)
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert names(response) == [
        "alpha and beta",
        "alpha only",
        "gamma",
        "untagged",
    ]


def test_single_tag_filter(client):
    seed_tasks(client)
    response = client.get("/api/v1/tasks", params={"tag": "alpha"})
    assert response.status_code == 200
    assert names(response) == ["alpha and beta", "alpha only"]


def test_multiple_tags_use_and_logic(client):
    seed_tasks(client)
    response = client.get("/api/v1/tasks", params={"tag": ["alpha", "beta"]})
    assert response.status_code == 200
    assert names(response) == ["alpha and beta"]


def test_unknown_tag_returns_no_tasks(client):
    """Regression: an unknown tag must not return the unfiltered list."""
    seed_tasks(client)
    response = client.get("/api/v1/tasks", params={"tag": "does-not-exist"})
    assert response.status_code == 200
    assert response.json()["tasks"] == []
    assert response.json()["total"] == 0


def test_known_and_unknown_tags_return_no_tasks(client):
    """One unknown tag in an AND filter means nothing can match."""
    seed_tasks(client)
    response = client.get(
        "/api/v1/tasks", params={"tag": ["alpha", "does-not-exist"]}
    )
    assert response.status_code == 200
    assert response.json()["tasks"] == []
    assert response.json()["total"] == 0


def test_tag_filter_is_case_insensitive(client):
    seed_tasks(client)
    response = client.get("/api/v1/tasks", params={"tag": "ALPHA"})
    assert response.status_code == 200
    assert names(response) == ["alpha and beta", "alpha only"]
