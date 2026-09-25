"""Service layer for tag operations."""
from datetime import datetime, timezone
import re
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..models import Tag, Task, TaskTag
from ..schemas import TagCreate, TagUpdate, TagResponse


def normalize_tag_name(name: str) -> str:
    """Normalize tag name: trim, lowercase."""
    if not name:
        return ""
    return name.strip().lower()


def get_or_create_tag(db: Session, name: str, color: Optional[str] = None) -> Tag:
    """
    Get an existing tag by normalized name, or create a new one.
    
    Args:
        db: Database session
        name: Tag name (will be normalized)
        color: Optional color for new tag
    
    Returns:
        The Tag instance
    """
    normalized = normalize_tag_name(name)
    if not normalized:
        raise ValueError("Tag name cannot be empty after normalization")
    
    # Check if tag exists
    existing = db.query(Tag).filter(func.lower(Tag.name) == normalized).first()
    if existing:
        return existing
    
    # Create new tag
    new_tag = Tag(
        name=normalized,
        color=color,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    return new_tag


def get_tag_by_name(db: Session, name: str) -> Optional[Tag]:
    """Get a tag by its name (case-insensitive)."""
    normalized = normalize_tag_name(name)
    return db.query(Tag).filter(func.lower(Tag.name) == normalized).first()


def get_tag_by_id(db: Session, tag_id: str) -> Optional[Tag]:
    """Get a tag by its ID."""
    return db.query(Tag).filter(Tag.id == tag_id).first()


def get_all_tags(db: Session) -> List[TagResponse]:
    """Get all tags with task counts."""
    # Query tags with their task counts
    tags = db.query(Tag).all()
    
    # Build response with task counts
    results = []
    for tag in tags:
        # Count tasks for this tag
        task_count = db.query(TaskTag).filter(TaskTag.tag_id == tag.id).count()
        results.append(TagResponse(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            task_count=task_count
        ))
    
    return results


def update_tag(db: Session, name: str, update_data: TagUpdate) -> Optional[TagResponse]:
    """
    Update a tag by name.
    
    Args:
        db: Database session
        name: Current tag name
        update_data: Update data
    
    Returns:
        Updated tag response, or None if not found
    """
    tag = get_tag_by_name(db, name)
    if not tag:
        return None
    
    if update_data.name is not None:
        # Check if new name would conflict
        normalized_new = normalize_tag_name(update_data.name)
        existing = db.query(Tag).filter(
            func.lower(Tag.name) == normalized_new,
            Tag.id != tag.id
        ).first()
        if existing:
            raise ValueError(f"Tag with name '{update_data.name}' already exists")
        tag.name = normalized_new
    
    if update_data.color is not None:
        tag.color = update_data.color
    
    tag.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tag)
    
    # Return response with updated task count
    task_count = db.query(TaskTag).filter(TaskTag.tag_id == tag.id).count()
    return TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
        task_count=task_count
    )


def delete_tag(db: Session, name: str) -> bool:
    """
    Delete a tag and remove it from all tasks.
    
    Args:
        db: Database session
        name: Tag name to delete
    
    Returns:
        True if deleted, False if not found
    """
    tag = get_tag_by_name(db, name)
    if not tag:
        return False
    
    # Delete all associations first
    db.query(TaskTag).filter(TaskTag.tag_id == tag.id).delete()
    
    # Delete the tag
    db.delete(tag)
    db.commit()
    return True


def get_or_create_tags(db: Session, tag_names: List[str]) -> List[Tag]:
    """
    Get or create multiple tags from a list of names.
    
    Args:
        db: Database session
        tag_names: List of tag names
    
    Returns:
        List of Tag instances
    """
    tags = []
    for name in tag_names:
        tag = get_or_create_tag(db, name)
        tags.append(tag)
    return tags
