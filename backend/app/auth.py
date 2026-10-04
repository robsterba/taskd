"""API key authentication for taskd.

Opt-in: when the TASKD_API_KEY environment variable is set, all API
endpoints (except health and version) require it in the X-API-Key
header. When unset, the app behaves as before with no authentication.
"""
import os
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_configured_api_key():
    """Return the expected API key, or None when auth is disabled."""
    return os.getenv("TASKD_API_KEY") or None


async def require_api_key(api_key: str = Security(_api_key_header)) -> None:
    """Dependency that enforces the X-API-Key header when configured."""
    expected = get_configured_api_key()
    if expected is None:
        return
    if api_key is None or not secrets.compare_digest(
        api_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
