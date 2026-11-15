"""Semaphore deployment triggers for docker-update-checker tasks.

Completing a DUC task from the GUI triggers the Semaphore job that
applies the update, instead of leaving the deployment as a separate
manual step:

- image subtask ("Update <image>") -> per-stack template
  "Stack update - <host>:<stack>", one per stack listed in the
  "Stacks:" line DUC writes into the subtask description.
- host parent ("Container updates: <host>") -> per-host template
  "Stack update - <host>".

Requests carrying a source header equal to the task's own source are
exempt: DUC completes subtasks itself during reconcile (after verifying
images are up to date), and those completions must not trigger jobs.

Trigger failure raises SemaphoreTriggerError (surfaced as HTTP 502),
so a "done" task always means the job actually fired.

Configuration (read from the environment on every call; unset
SEMAPHORE_URL or SEMAPHORE_API_TOKEN disables triggering):

    SEMAPHORE_URL         base URL, e.g. http://192.168.1.13:3000
    SEMAPHORE_API_TOKEN   bearer token
    SEMAPHORE_PROJECT     project id (default: 1)
    SEMAPHORE_HOSTS       comma-separated host list to trigger for
                          (default: boxy,moxy,foxy); completions on
                          other hosts (rxps dev containers) pass
                          through without triggering
"""

import logging
import os
import re
from typing import List, Optional

import httpx
from sqlalchemy.orm import Session

from ..models import Task

logger = logging.getLogger(__name__)

DUC_SOURCE = "docker-update-checker"
DUC_TITLE_PREFIX = "Container updates: "
STACKS_LINE = re.compile(r"^Stacks:\s*(.+)$", re.MULTILINE)

HTTP_TIMEOUT = 5.0


class SemaphoreTriggerError(Exception):
    """A Semaphore trigger failed; the completion must not go through."""


def get_settings() -> Optional[dict]:
    """Effective trigger settings, or None when the integration is off."""
    url = os.getenv("SEMAPHORE_URL", "").strip().rstrip("/")
    token = os.getenv("SEMAPHORE_API_TOKEN", "").strip()
    if not url or not token:
        return None
    return {
        "url": url,
        "token": token,
        "project": (os.getenv("SEMAPHORE_PROJECT", "1").strip() or "1"),
        # normalized host list, lowcase compare happens at match time
        "hosts": [
            h.strip()
            for h in os.getenv("SEMAPHORE_HOSTS", "boxy,moxy,foxy").split(",")
            if h.strip()
        ],
    }


def host_from_title(name: str) -> Optional[str]:
    """Host name from a DUC parent title, None for anything else."""
    if name.startswith(DUC_TITLE_PREFIX):
        host = name[len(DUC_TITLE_PREFIX) :].strip()
        return host or None
    return None


def stacks_from_description(description: Optional[str]) -> List[str]:
    """Stack names from the DUC-written 'Stacks: a, b' description line."""
    if not description:
        return []
    match = STACKS_LINE.search(description)
    if not match:
        return []
    return [s.strip() for s in match.group(1).split(",") if s.strip()]


def _find_template(
    templates: List[dict], host: str, stack: Optional[str]
) -> Optional[dict]:
    """Match 'Stack update[s] - <host>[:<stack>]' among Semaphore templates.

    The template list is fetched per trigger (IDs are unstable; names are
    the contract). Stack templates are 'Stack update - <host>:<stack>'.
    """
    suffix = f":{stack}" if stack else ""
    pattern = re.compile(
        rf"^stack updates? - {re.escape(host.lower())}{re.escape(suffix.lower())}$"
    )
    for template in templates:
        if pattern.match(template.get("name", "").strip().lower()):
            return template
    return None


def _fetch_templates(settings: dict) -> List[dict]:
    try:
        response = httpx.get(
            f"{settings['url']}/api/project/{settings['project']}/templates",
            headers={"Authorization": f"Bearer {settings['token']}"},
            timeout=HTTP_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise SemaphoreTriggerError(f"Semaphore unreachable: {exc}") from exc
    if response.status_code != 200:
        raise SemaphoreTriggerError(
            f"Semaphore template lookup failed (HTTP {response.status_code})"
        )
    return response.json()


def _create_task(settings: dict, template_id: int) -> dict:
    try:
        response = httpx.post(
            f"{settings['url']}/api/project/{settings['project']}/tasks",
            headers={
                "Authorization": f"Bearer {settings['token']}",
                "Content-Type": "application/json",
            },
            json={"template_id": template_id},
            timeout=HTTP_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise SemaphoreTriggerError(f"Semaphore unreachable: {exc}") from exc
    if response.status_code not in (200, 201):
        raise SemaphoreTriggerError(
            f"Semaphore task creation failed (HTTP {response.status_code})"
        )
    return response.json()


def trigger_for_task(
    db: Session, task: Task, requester_source: Optional[str]
) -> Optional[str]:
    """Fire the Semaphore job implied by completing a DUC task.

    Returns a human-readable trigger summary, or None when the
    completion should not trigger anything (not a DUC task, sender is
    the integration itself, host not in SEMAPHORE_HOSTS, or the
    integration is not configured).

    Raises SemaphoreTriggerError when a trigger was expected but could
    not be delivered — the caller must treat that as a failed completion.
    """
    if task.source != DUC_SOURCE:
        return None

    # The integration completing its own tasks during reconcile is
    # bookkeeping, not a deployment request.
    if requester_source == DUC_SOURCE:
        return None

    settings = get_settings()
    if settings is None:
        # Integration not configured: completions are plain bookkeeping.
        return None

    host = host_from_title(task.name)
    if host is None:
        # Image subtask: the host lives on the parent title.
        if not task.parent_task_id:
            return None
        parent = db.query(Task).filter(Task.id == task.parent_task_id).first()
        if not parent:
            return None
        host = host_from_title(parent.name)
    if host is None or host.lower() not in (h.lower() for h in settings["hosts"]):
        return None

    tasks = _fetch_templates(settings)
    triggered = []

    if task.parent_task_id is None:
        # Host parent completion: one per-host job covers every stack.
        template = _find_template(tasks, host, None)
        if template is None:
            raise SemaphoreTriggerError(
                f"No Semaphore template 'Stack update - {host}' found"
            )
        created = _create_task(settings, template["id"])
        triggered.append(f"{template['name']} (task {created.get('id')})")
    else:
        stacks = stacks_from_description(task.description)
        if not stacks:
            raise SemaphoreTriggerError(
                "No stack metadata in the task description — wait for the next "
                "docker-update-checker scan, then complete it again"
            )
        for stack in stacks:
            template = _find_template(tasks, host, stack)
            if template is None:
                raise SemaphoreTriggerError(
                    f"No Semaphore template 'Stack update - {host}:{stack}' found"
                )
            created = _create_task(settings, template["id"])
            triggered.append(f"{template['name']} (task {created.get('id')})")

    summary = "Semaphore: " + "; ".join(triggered)
    logger.info("task %s completion triggered %s", task.id, summary)
    return summary
