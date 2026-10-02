"""Tests for parent task status derived from subtask completion.

While a parent task is 'todo' or 'in_progress', its status tracks its
subtasks: any completed subtask makes it 'in_progress', zero completed
subtasks make it 'todo'. A parent manually marked 'done' or 'archived'
keeps its status regardless of subtask changes, and completing ALL
subtasks still leaves the parent 'in_progress' until completed manually.
"""


def create_parent_with_subtasks(client, count=2):
    """Create a parent task with `count` subtasks; return (parent, subtasks)."""
    parent = client.post("/api/v1/tasks", json={"name": "parent"}).json()
    subtasks = [
        client.post(
            "/api/v1/tasks",
            json={"name": f"subtask {i}", "parent_task_id": parent["id"]}
        ).json()
        for i in range(count)
    ]
    return parent, subtasks


def get_status(client, task_id):
    return client.get(f"/api/v1/tasks/{task_id}").json()["status"]


def test_completing_subtask_sets_parent_in_progress(client):
    parent, subtasks = create_parent_with_subtasks(client)

    response = client.patch(
        f"/api/v1/tasks/{subtasks[0]['id']}", json={"status": "done"}
    )
    assert response.status_code == 200
    assert get_status(client, parent["id"]) == "in_progress"


def test_completing_subtask_via_complete_endpoint_sets_parent_in_progress(client):
    parent, subtasks = create_parent_with_subtasks(client)

    response = client.post(f"/api/v1/tasks/{subtasks[0]['id']}/complete")
    assert response.status_code == 200
    assert get_status(client, parent["id"]) == "in_progress"


def test_unchecking_last_subtask_returns_parent_to_todo(client):
    parent, subtasks = create_parent_with_subtasks(client, count=1)

    client.patch(f"/api/v1/tasks/{subtasks[0]['id']}", json={"status": "done"})
    assert get_status(client, parent["id"]) == "in_progress"

    client.patch(f"/api/v1/tasks/{subtasks[0]['id']}", json={"status": "todo"})
    assert get_status(client, parent["id"]) == "todo"


def test_all_subtasks_done_leaves_parent_in_progress(client):
    parent, subtasks = create_parent_with_subtasks(client, count=2)

    for subtask in subtasks:
        client.patch(f"/api/v1/tasks/{subtask['id']}", json={"status": "done"})

    assert get_status(client, parent["id"]) == "in_progress"


def test_manually_done_parent_keeps_done_when_subtask_changes(client):
    parent, subtasks = create_parent_with_subtasks(client)

    client.patch(f"/api/v1/tasks/{parent['id']}", json={"status": "done"})

    client.patch(f"/api/v1/tasks/{subtasks[0]['id']}", json={"status": "done"})
    assert get_status(client, parent["id"]) == "done"

    client.patch(f"/api/v1/tasks/{subtasks[0]['id']}", json={"status": "todo"})
    assert get_status(client, parent["id"]) == "done"


def test_archived_parent_keeps_archived_when_subtask_completed(client):
    parent, subtasks = create_parent_with_subtasks(client)

    client.patch(f"/api/v1/tasks/{parent['id']}", json={"status": "archived"})

    client.patch(f"/api/v1/tasks/{subtasks[0]['id']}", json={"status": "done"})
    assert get_status(client, parent["id"]) == "archived"


def test_subtask_changes_do_not_touch_top_level_tasks(client):
    """A task without a parent must never be status-synced."""
    task = client.post("/api/v1/tasks", json={"name": "standalone"}).json()

    client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "done"})
    assert get_status(client, task["id"]) == "done"
