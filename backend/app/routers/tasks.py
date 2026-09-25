"""Task router for FastAPI endpoints."""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    TaskCreate, TaskUpdate, TaskResponse, TaskDetailResponse, 
    TaskListResponse, TaskChangeResponse, HealthResponse
)
from ..services.task_service import (
    create_task, get_task, list_tasks, update_task, delete_task,
    complete_task, get_changed_tasks, get_task_detail_response
)
from ..services.tag_service import get_or_create_tags
from ..models import Task

router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks_endpoint(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    tag: Optional[List[str]] = Query(None, description="Filter by tag names (AND logic)"),
    parent: Optional[str] = Query(None, description="'none' for top-level only, or task ID for subtasks"),
    due_before: Optional[datetime] = Query(None, description="Filter tasks due before this date"),
    due_after: Optional[datetime] = Query(None, description="Filter tasks due after this date"),
    search: Optional[str] = Query(None, description="Search substring in name and description"),
    sort: Optional[str] = Query(None, description="Sort field (prefix '-' for descending)"),
    limit: int = Query(100, ge=1, le=500, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Page offset")
):
    """List tasks with filtering and pagination."""
    tasks, total = list_tasks(
        db=db,
        status=status,
        priority=priority,
        tag=tag,
        parent=parent,
        due_before=due_before,
        due_after=due_after,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset
    )
    
    # Convert tasks to response format (extract tag names)
    task_responses = []
    for task in tasks:
        tag_names = [tag.name for tag in task.tags] if task.tags else []
        task_responses.append(TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            parent_task_id=task.parent_task_id,
            recurrence=task.recurrence,
            source=task.source,
            tags=tag_names,
            created_at=task.created_at,
            updated_at=task.updated_at
        ))
    
    return TaskListResponse(
        tasks=task_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task_endpoint(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    source: Optional[str] = Header(None, description="Source of task creation")
):
    """Create a new task."""
    # Use source from header if provided, otherwise from body, otherwise default to "api"
    effective_source = source or task_data.source or "api"
    
    try:
        task = create_task(db, task_data, source=effective_source)
        return TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            parent_task_id=task.parent_task_id,
            recurrence=task.recurrence,
            source=task.source,
            tags=[tag.name for tag in task.tags] if task.tags else [],
            created_at=task.created_at,
            updated_at=task.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# GET /tasks/changed must come before GET /tasks/{task_id} for proper routing
@router.get("/tasks/changed", response_model=TaskChangeResponse)
def get_changed_tasks_endpoint(
    since: datetime = Query(..., description="ISO datetime to filter from"),
    db: Session = Depends(get_db)
):
    """Get tasks changed since a specific timestamp."""
    if not since.tzinfo:
        since = since.replace(tzinfo=timezone.utc)
    
    tasks = get_changed_tasks(db, since)
    
    # Convert tasks to response format (extract tag names)
    task_responses = []
    for task in tasks:
        tag_names = [tag.name for tag in task.tags] if task.tags else []
        task_responses.append(TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            parent_task_id=task.parent_task_id,
            recurrence=task.recurrence,
            source=task.source,
            tags=tag_names,
            created_at=task.created_at,
            updated_at=task.updated_at
        ))
    
    return TaskChangeResponse(
        tasks=task_responses,
        since=since
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def get_task_endpoint(task_id: str, db: Session = Depends(get_db)):
    """Get a single task with subtasks and tags."""
    task = get_task(db, task_id, include_subtasks=True)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    
    # Convert to detail response
    return get_task_detail_response(db, task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task_endpoint(task_id: str, update_data: TaskUpdate, db: Session = Depends(get_db)):
    """Partially update a task."""
    task = update_task(db, task_id, update_data)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        parent_task_id=task.parent_task_id,
        recurrence=task.recurrence,
        source=task.source,
        tags=[tag.name for tag in task.tags] if task.tags else [],
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task_endpoint(task_id: str, db: Session = Depends(get_db)):
    """Mark a task as done. If recurring, spawns next occurrence."""
    task = complete_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    
    # Add warning header if parent task still has incomplete subtasks
    headers = {}
    if task.parent_task_id:
        parent_task = db.query(Task).filter(Task.id == task.parent_task_id).first()
        if parent_task:
            # Check if parent has incomplete subtasks
            incomplete_subtasks = db.query(Task).filter(
                Task.parent_task_id == parent_task.id,
                Task.status != "done",
                Task.status != "archived"
            ).count()
            if incomplete_subtasks > 0:
                headers["X-Warning"] = "Parent task has incomplete subtasks"
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        parent_task_id=task.parent_task_id,
        recurrence=task.recurrence,
        source=task.source,
        tags=[tag.name for tag in task.tags] if task.tags else [],
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task_endpoint(task_id: str, db: Session = Depends(get_db)):
    """Delete a task and its subtasks."""
    if not delete_task(db, task_id):
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return None
