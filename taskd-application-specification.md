# taskd — Application Specification

## 1. Overview

taskd is a lightweight, self-hosted task management application with a REST API and a web GUI. It serves two use cases:

1. A day-to-day personal todo list used through the GUI.
2. An automation endpoint for n8n workflows, which create tasks via the API and react to task state changes.

Deployment target: single Docker container (`taskd`) on a homelab host. All clients are on the same LAN behind a firewall. Security (authentication, TLS) is explicitly out of scope for v1.

## 2. Recommended Stack

Recommendation: Python FastAPI backend + SQLite database + React frontend, all in one container.

- FastAPI gives automatic OpenAPI docs (`/docs`), which makes the n8n HTTP Request node configuration trivial.
- SQLite keeps the container stateless except for one file; mount it as a volume for persistence. No database server to run.
- The React app is built to static files at image build time and served by FastAPI. One container, one port, no separate frontend service, no CORS issues, no Node runtime in production.
- Recommendation rationale over alternatives: Postgres is unnecessary at this scale; a server-rendered Python template GUI would be faster to build but much harder to evolve into a polished todo UI; a two-container split adds orchestration overhead for zero benefit here.

## 3. Architecture

- Single container, single port (default 8000, configurable via `PORT` env var).
- FastAPI serves:
  - `/api/*` — REST endpoints.
  - `/*` — built React static files (SPA with client-side routing; unknown paths fall back to `index.html`).
- SQLite database at `/data/tasks.db` (configurable via `DATA_DIR` env var). `/data` is a bind-mounted volume.
- Alembic (or a lightweight migration script) for schema migrations on startup.

```
[n8n workflows] --HTTP--> /api/*   [ FastAPI + static React build ] --SQL--> SQLite volume
[Browser / GUI]  ----HTTP--> /*
```

## 4. Data Model

### 4.1 Task

| Field | Type | Required | Notes |
|---|---|---|---|
| id | UUID (string) | auto | Generated server-side; stable across restarts |
| name | string, max 500 | yes | Short title |
| description | string, no limit | no | Long-form notes; supports markdown rendering in GUI |
| status | enum | yes | `todo`, `in_progress`, `done`, `archived`. Default `todo` |
| priority | enum | no | `low`, `medium`, `high`, `urgent`. Default `medium` |
| due_date | ISO 8601 datetime, nullable | no | Optional |
| parent_task_id | UUID, nullable | no | Set to create a subtask |
| recurrence | object, nullable | no | Recurring task rule (see 4.2) |
| source | string | auto | `gui` or `api` (or free-form label supplied by caller). Distinguishes automated vs. manual tasks |
| tags | list of tag names | no | Many-to-many; tags auto-created on first use (see 4.3) |
| created_at | datetime | auto | UTC |
| updated_at | datetime | auto | UTC, updated on every mutation |

### 4.2 Recurring Tasks

- Recurrence rule stored as a simple JSON object: `{ "interval": "daily" | "weekly" | "monthly", "interval_count": n }` (e.g. every 2 weeks). Keep this deliberately simple; no full RFC 5545 RRULE in v1.
- When a recurring task is marked `done`, the server generates the next occurrence (clone with new due date computed from the rule, status `todo`) instead of the caller doing it.
- Recurrence is disabled permanently by clearing the rule or archiving the task.

### 4.3 Tags

- Tag = `{ id, name, color (optional) }`.
- Tags are created implicitly: assigning an unknown tag name to a task creates it. Explicit create/update/delete endpoints exist for renaming and setting colors.
- Tag names are unique, case-insensitive, normalized (trimmed, lowercased) on write.
- Intended usage: `automated`, `household`, `homelab`, `project:<name>`.

### 4.4 Subtasks

- A subtask references `parent_task_id`. One nesting level only (subtasks may not themselves have subtasks — reject with 422).
- A parent task is not `done` until all non-archived subtasks are `done` (GUI enforces client-side; API returns a warning header; parent completion is still allowed to keep automation flows simple).

## 5. API Specification

All endpoints under `/api/v1`. No authentication in v1. JSON request/response bodies. Standard errors: 400 validation, 404 not found, 422 unprocessable entity, 500 server error, with a consistent `{ "detail": "..." }` error shape (FastAPI default).

### 5.1 Tasks

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/tasks` | List/filter tasks |
| POST | `/api/v1/tasks` | Create task |
| GET | `/api/v1/tasks/{id}` | Get single task (includes subtasks and tags) |
| PATCH | `/api/v1/tasks/{id}` | Partial update (name, description, status, priority, due_date, tags, recurrence) |
| DELETE | `/api/v1/tasks/{id}` | Delete task and its subtasks |

List endpoint query parameters (all optional, combinable):

- `status`, `priority` — exact match
- `tag` — repeatable; multiple values are ANDed
- `parent` — `none` for top-level only, `{id}` for subtasks of a task
- `due_before`, `due_after` — ISO 8601 range filter
- `search` — substring match on name and description
- `sort` — `created_at`, `updated_at`, `due_date`, `priority`, `name`; prefix `-` for descending
- `limit` (default 100, max 500), `offset` — pagination; response includes `total`

POST `/api/v1/tasks` also accepts an optional `subtasks: [string]` array of names for one-shot creation of subtasks — convenient for n8n flows.

### 5.2 Tags

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/tags` | List all tags, with task counts |
| PATCH | `/api/v1/tags/{name}` | Rename / set color |
| DELETE | `/api/v1/tags/{name}` | Delete tag; removes it from all tasks |

### 5.3 Convenience Endpoints (for n8n)

- `POST /api/v1/tasks/{id}/complete` — sets status `done` (and spawns next occurrence for recurring tasks); idempotent.
- `GET /api/v1/tasks/changed?since=<ISO datetime>` — returns tasks with `updated_at` > since. Enables polling-based agentic workflows without webhook infrastructure.

### 5.4 Machine-Facing Behavior

- All IDs are UUIDs returned as strings.
- All datetimes are UTC, ISO 8601 with `Z` suffix.
- Unknown fields in request bodies are ignored (forward compatibility).
- `/api/v1/openapi.json` and Swagger UI at `/docs` are always enabled.

## 6. GUI Specification

React SPA, served from the same container. No login screen in v1.

### 6.1 Views

- Task list (default view): grouped or flat list with inline status toggle (click checkbox), priority indicator, due date with overdue highlighting, tag chips, subtask count. Filter bar: status tabs (All / Active / Done / Archived), tag filter dropdown, search box, sort dropdown.
- Task detail: full description (markdown rendered), editable fields, subtask checklist with add/complete/delete, tag editor.
- Quick add: single input at top of list; Enter creates task. Parsed shortcuts: `#tag` tokens in the quick-add text become tags; `!high`/`!urgent` sets priority.

### 6.2 Behavior

- All mutations go through the same REST API the automation uses.
- Optimistic UI updates for status toggles and quick-add.
- Tasks created via GUI get `source: "gui"`.
- Overdue tasks shown with a visual indicator; recurring tasks show a small repeat icon.
- Responsive enough to use on a phone browser on the LAN, but desktop-first.

## 7. n8n Integration

### 7.1 Creating tasks from n8n

- HTTP Request node → `POST /api/v1/tasks` with JSON body.
- Recommended convention: always send `tags: ["automated", ...workflow-specific tags]` and `source: "n8n"` (or workflow name) so GUI users can filter them.

### 7.2 Reacting to tasks (agentic workflows)

v1 deliberately leaves the mechanism open with two supported paths; implement both, since both are cheap:

1. Polling (default): n8n Schedule Trigger → `GET /api/v1/tasks/changed?since={{ $now }}`, filter, act. No app-side state needed.
2. Webhooks (v2 candidate): `POST /api/v1/webhooks` to register a callback URL fired on task create/update/delete. Out of scope for v1 to keep the build small; the `/changed` endpoint covers the same need.

### 7.3 Typical flows enabled

- Agent creates a task when a monitored condition occurs.
- n8n scans for `done` tasks tagged `automated` and triggers follow-up actions (e.g. shutdown a service, send a notification).
- Daily digest workflow pulls tasks due today.

## 8. Container & Deployment

- Multi-stage Dockerfile: stage 1 builds the React app (Node), stage 2 installs Python deps and copies the built static assets. Final image is Python-only, slim base.
- Volumes: `/data` for the SQLite file.
- Environment variables: `PORT` (default 8000), `DATA_DIR` (default `/data`). Nothing else required.
- Healthcheck: `GET /api/v1/health` returning `{"status": "ok"}`.
- Runs as non-root user.
- Image is named `taskd`; docker-compose example with container name `taskd`, `restart: unless-stopped`, port mapping, volume.

## 9. Non-Goals (v1)

- Authentication / authorization / multi-user
- Multi-level task nesting
- Full calendar/RRULE recurrence
- Real-time push (WebSockets); GUI refreshes via polling or manual reload
- File attachments, comments, notifications

## 10. Acceptance Criteria

- Create, read, update, delete tasks via GUI and via API, verified through `/docs`.
- Filter tasks by tag, status, due date via API.
- Tags auto-created on assignment; renaming a tag updates all its tasks.
- Subtask creation one level deep; deeper nesting rejected with 422.
- Completing a recurring task spawns the next occurrence with a computed due date.
- `GET /api/v1/tasks/changed?since=` returns correct delta set.
- Container starts with a fresh volume and works immediately; survives restart with data intact.
- A task created by `curl POST /api/v1/tasks` appears in the GUI without restart.

## 11. Suggested Build Order

1. FastAPI skeleton, SQLite schema, task CRUD endpoints, health endpoint.
2. Tag endpoints and filtering on the list endpoint.
3. Subtasks and recurrence logic.
4. `/changed` endpoint.
5. React GUI: list view, quick add, detail view.
6. Docker multi-stage build, compose file, volume persistence.
7. End-to-end test with n8n HTTP nodes (create task, poll changes).