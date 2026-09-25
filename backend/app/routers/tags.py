"""Tag router for FastAPI endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import TagResponse, TagCreate, TagUpdate
from ..services.tag_service import (
    get_all_tags, get_tag_by_name, update_tag, delete_tag
)

router = APIRouter(prefix="/api/v1", tags=["tags"])


@router.get("/tags", response_model=List[TagResponse])
def list_tags(db: Session = Depends(get_db)):
    """List all tags with task counts."""
    return get_all_tags(db)


@router.patch("/tags/{name}", response_model=TagResponse)
def update_tag_endpoint(name: str, update_data: TagUpdate, db: Session = Depends(get_db)):
    """Rename a tag or update its color."""
    try:
        result = update_tag(db, name, update_data)
        if not result:
            raise HTTPException(status_code=404, detail=f"Tag '{name}' not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tags/{name}", status_code=204)
def delete_tag_endpoint(name: str, db: Session = Depends(get_db)):
    """Delete a tag and remove it from all tasks."""
    if not delete_tag(db, name):
        raise HTTPException(status_code=404, detail=f"Tag '{name}' not found")
    return None
