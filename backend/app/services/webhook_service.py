"""Webhook dispatch and delivery.

Events are enqueued by the task service after commit and delivered by a
background worker thread: HTTP POST with HMAC-SHA256 signature, up to
MAX_ATTEMPTS attempts, each attempt recorded in the webhook_deliveries table.
"""
import hmac
import hashlib
import json
import queue
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from ..models import Webhook, WebhookDelivery
from ..database import SessionLocal

# Session factory used by the worker to record deliveries.
# Module-level so tests can point it at the test database.
_session_factory = SessionLocal

HTTP_TIMEOUT = 5.0
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2.0
MAX_DELIVERY_LOG_PER_WEBHOOK = 50

_job_queue: "queue.Queue" = queue.Queue()
_worker: Optional[threading.Thread] = None
_worker_lock = threading.Lock()


def generate_secret() -> str:
    """Generate a random HMAC secret for a new webhook."""
    return secrets.token_hex(32)


def sign_payload(secret: str, body: bytes) -> str:
    """Compute the HMAC-SHA256 signature hex digest for a request body."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def dispatch_event(db: Session, event_type: str, task_payload: dict, task_id: Optional[str] = None) -> None:
    """Queue deliveries of an event to all active webhooks subscribed to it.

    Called after the database commit so payloads reflect durable state.
    """
    webhooks = db.query(Webhook).filter(Webhook.active.is_(True)).all()
    matching = [w for w in webhooks if event_type in (w.events or [])]
    if not matching:
        return

    for webhook in matching:
        _job_queue.put({
            "webhook_id": webhook.id,
            "url": webhook.url,
            "secret": webhook.secret,
            "payload": {
                "event": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task": task_payload,
            },
            "task_id": task_id,
        })


def _send_webhook(url: str, secret: str, body: bytes) -> Optional[int]:
    """POST the signed body to the webhook URL.

    Returns the HTTP status code, or None if the request failed
    (connection error, timeout, invalid response).
    """
    headers = {
        "Content-Type": "application/json",
        "X-taskd-Event": "true",
        "X-taskd-Signature": sign_payload(secret, body),
    }
    try:
        response = httpx.post(url, content=body, headers=headers, timeout=HTTP_TIMEOUT)
        return response.status_code
    except httpx.HTTPError:
        return None


def _record_delivery(session: Session, job: dict, status: str, response_code: Optional[int], attempts: int) -> None:
    """Persist a delivery attempt result and prune the per-webhook log."""
    session.add(WebhookDelivery(
        webhook_id=job["webhook_id"],
        event_type=job["payload"]["event"],
        task_id=job["task_id"],
        status=status,
        response_code=response_code,
        attempts=attempts,
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()

    # Keep only the most recent deliveries per webhook
    rows = (
        session.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == job["webhook_id"])
        .order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id.desc())
        .all()
    )
    for stale in rows[MAX_DELIVERY_LOG_PER_WEBHOOK:]:
        session.delete(stale)
    if len(rows) > MAX_DELIVERY_LOG_PER_WEBHOOK:
        session.commit()


def _deliver_job(job: dict) -> None:
    """Deliver one job with retries and record the outcome."""
    body = json.dumps(job["payload"]).encode("utf-8")
    attempts = 0
    response_code = None

    for attempt in range(MAX_ATTEMPTS):
        attempts = attempt + 1
        response_code = _send_webhook(job["url"], job["secret"], body)
        if response_code is not None and 200 <= response_code < 300:
            break
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(RETRY_DELAY_SECONDS)

    success = response_code is not None and 200 <= response_code < 300

    session = _session_factory()
    try:
        _record_delivery(session, job, "success" if success else "failed", response_code, attempts)
    finally:
        session.close()


def _worker_loop() -> None:
    """Background worker: drain the job queue until stopped."""
    while True:
        job = _job_queue.get()
        if job is None:
            break
        try:
            _deliver_job(job)
        except Exception:
            # Delivery failures must never kill the worker
            pass


def start_worker() -> None:
    """Start the delivery worker thread (idempotent)."""
    global _worker
    with _worker_lock:
        if _worker is not None and _worker.is_alive():
            return
        _worker = threading.Thread(target=_worker_loop, name="webhook-dispatcher", daemon=True)
        _worker.start()


def stop_worker() -> None:
    """Stop the delivery worker thread (idempotent)."""
    global _worker
    with _worker_lock:
        if _worker is None:
            return
        _job_queue.put(None)
        _worker.join(timeout=10)
        _worker = None


def drain_queue() -> int:
    """Synchronously process all queued jobs. Intended for tests."""
    processed = 0
    while True:
        try:
            job = _job_queue.get_nowait()
        except queue.Empty:
            break
        if job is None:
            continue
        try:
            _deliver_job(job)
        except Exception:
            pass
        processed += 1
    return processed


def send_test_ping(db: Session, webhook: Webhook) -> dict:
    """Deliver a webhook.test event synchronously (single attempt)."""
    payload = {
        "event": "webhook.test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": None,
    }
    body = json.dumps(payload).encode("utf-8")
    response_code = _send_webhook(webhook.url, webhook.secret, body)
    success = response_code is not None and 200 <= response_code < 300

    _record_delivery(db, {
        "webhook_id": webhook.id,
        "payload": payload,
        "task_id": None,
    }, "success" if success else "failed", response_code, 1)

    return {"status": "success" if success else "failed", "response_code": response_code}
