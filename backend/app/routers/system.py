"""System router for unauthenticated endpoints (health, version)."""
from datetime import datetime, timezone

from fastapi import APIRouter

from ..schemas import HealthResponse
from ..version import get_version

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=get_version(),
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/version")
def get_version_endpoint():
    """Get the application version."""
    return {"version": get_version()}
