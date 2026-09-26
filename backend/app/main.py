"""Main FastAPI application for taskd."""
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path

from .database import init_db
from .routers.tasks import router as tasks_router
from .routers.tags import router as tags_router
from .version import VERSION

# Create FastAPI app
app = FastAPI(
    title="taskd",
    description="A lightweight, self-hosted task management application with REST API and web GUI",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Add CORS middleware (even though not strictly needed in same-container setup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks_router)
app.include_router(tags_router)


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database on application startup."""
    init_db()


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
async def serve_spa(request: Request):
    """Serve the React SPA for all non-API routes."""
    # Check if the path is for API, docs, or static files
    path = request.url.path
    if path.startswith("/api") or path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
        raise HTTPException(status_code=404, detail="Not found")

    # Serve index.html for SPA routing
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text())

    # For development, return a simple message
    return {"message": "taskd API is running. Frontend not built yet."}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
