"""Webhook registration and management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Webhook, WebhookDelivery
from ..schemas import (
    WebhookCreate, WebhookUpdate, WebhookResponse,
    WebhookListResponse, WebhookDeliveryResponse
)
from ..services.webhook_service import generate_secret, send_test_ping

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


def _get_webhook_or_404(db: Session, webhook_id: str) -> Webhook:
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook with id {webhook_id} not found")
    return webhook


@router.get("", response_model=WebhookListResponse)
def list_webhooks_endpoint(db: Session = Depends(get_db)):
    """List all registered webhooks."""
    webhooks = db.query(Webhook).order_by(Webhook.created_at).all()
    return WebhookListResponse(webhooks=[WebhookResponse.model_validate(w) for w in webhooks])


@router.post("", response_model=WebhookResponse, status_code=201)
def create_webhook_endpoint(webhook_data: WebhookCreate, db: Session = Depends(get_db)):
    """Register a new webhook. A secret is generated if not provided."""
    webhook = Webhook(
        url=webhook_data.url,
        events=webhook_data.events,
        secret=webhook_data.secret or generate_secret(),
        active=webhook_data.active
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return WebhookResponse.model_validate(webhook)


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook_endpoint(webhook_id: str, db: Session = Depends(get_db)):
    """Get a single webhook."""
    return WebhookResponse.model_validate(_get_webhook_or_404(db, webhook_id))


@router.patch("/{webhook_id}", response_model=WebhookResponse)
def update_webhook_endpoint(webhook_id: str, update_data: WebhookUpdate, db: Session = Depends(get_db)):
    """Update a webhook registration."""
    webhook = _get_webhook_or_404(db, webhook_id)

    if update_data.url is not None:
        webhook.url = update_data.url
    if update_data.events is not None:
        webhook.events = update_data.events
    if update_data.secret is not None:
        webhook.secret = update_data.secret
    if update_data.active is not None:
        webhook.active = update_data.active

    db.commit()
    db.refresh(webhook)
    return WebhookResponse.model_validate(webhook)


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook_endpoint(webhook_id: str, db: Session = Depends(get_db)):
    """Delete a webhook and its delivery log."""
    webhook = _get_webhook_or_404(db, webhook_id)
    db.delete(webhook)
    db.commit()
    return None


@router.post("/{webhook_id}/test")
def test_webhook_endpoint(webhook_id: str, db: Session = Depends(get_db)):
    """Send a webhook.test event to the registered URL (single attempt)."""
    webhook = _get_webhook_or_404(db, webhook_id)
    return send_test_ping(db, webhook)


@router.get("/{webhook_id}/deliveries")
def list_deliveries_endpoint(
    webhook_id: str,
    db: Session = Depends(get_db),
    limit: int = 20
):
    """List recent deliveries for a webhook, newest first."""
    _get_webhook_or_404(db, webhook_id)
    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "deliveries": [WebhookDeliveryResponse.model_validate(d).model_dump(mode="json") for d in deliveries]
    }
