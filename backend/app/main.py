"""Main FastAPI application for taskd."""
import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from .database import init_db
from .auth import require_api_key
from .routers.tasks import router as tasks_router
from .routers.tags import router as tags_router
from .routers.webhooks import router as webhooks_router
from .routers.system import router as system_router
from .services.webhook_service import start_worker, stop_worker
from .version import VERSION, get_version

# Create FastAPI app
app = FastAPI(
    title="taskd",
    description="A lightweight, self-hosted task management application with REST API and web GUI",
    version=get_version(),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)


# The GUI and API are served from the same origin, and the Vite dev server
# proxies /api to the backend, so no CORS middleware is needed.

# Include routers
# Health and version stay unauthenticated (container healthchecks, HA setup
# validation); everything else requires the X-API-Key header when
# TASKD_API_KEY is set.
app.include_router(system_router)
app.include_router(tasks_router, dependencies=[Depends(require_api_key)])
app.include_router(tags_router, dependencies=[Depends(require_api_key)])
app.include_router(webhooks_router, dependencies=[Depends(require_api_key)])


# Initialize database and start the webhook delivery worker on startup
@app.on_event("startup")
def startup_event():
    """Initialize database on application startup."""
    init_db()
    start_worker()


@app.on_event("shutdown")
def shutdown_event():
    """Stop the webhook delivery worker on shutdown."""
    stop_worker()


# Serve static files for React frontend
# The static files will be mounted at /static in the container
STATIC_DIR = Path("/app/static")

# Mount static files - do this before catch-all routes
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Fallback to index.html for SPA routing
# This must come AFTER static file mounting
@app.get("/")
async def serve_spa_root(request: Request):
    """Serve the React SPA for root path."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text())
    return {"message": "taskd API is running. Frontend not built yet."}


@app.get("/{path:path}")
async def serve_spa(request: Request, path: str):
    """Serve the React SPA for all non-API routes."""
    # Check if the path is for API or docs
    if path.startswith("/api") or path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # For static assets, try to serve the file directly
    if path.startswith("/static/"):
        file_path = STATIC_DIR / path.removeprefix("/static/")
        if file_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(file_path)
    
    # Serve index.html for all other non-API paths (SPA routing)
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text())

    # For development, return a simple message
    return {"message": "taskd API is running. Frontend not built yet."}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
