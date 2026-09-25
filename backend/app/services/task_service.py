"""Service layer for task operations."""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc, asc, not_
from dateutil.relativedelta import relativedelta

from ..models import Task, Tag, TaskTag
from ..schemas import TaskCreate, TaskUpdate, TaskResponse, TaskDetailResponse, TaskListResponse
from .tag_service import get_or_create_tags, normalize_tag_name
from ..utils.recurrence import compute_next_due_date, should_spawn_next_occurrence


# Status order for sorting
STATUS_ORDER = {
    "urgent": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "todo": 4,
    "in_progress": 5,
    "done": 6,
    "archived": 7
}

# Priority order for sorting
PRIORITY_ORDER = {
    "urgent": 0,
    "high": 1,
    "medium": 2,
    "low": 3
}


def create_task(db: Session, task_data: TaskCreate, source: Optional[str] = None) -> Task:
    """
    Create a new task.
    
    Args:
        db: Database session
        task_data: Task creation data
        source: Source of task creation (defaults to 'api')
    
    Returns:
        The created Task instance
    """
    # Validate parent_task_id exists and is not a subtask itself
    parent_task = None
    if task_data.parent_task_id:
        parent_task = db.query(Task).filter(Task.id == task_data.parent_task_id).first()
        if not parent_task:
            raise ValueError(f"Parent task with id {task_data.parent_task_id} not found")
        # Check if parent is a subtask (would make this a 3rd level task)
        if parent_task.parent_task_id:
            raise ValueError("Subtasks cannot have subtasks (max nesting level is 1)")
    
    # Normalize and get tags
    tags = []
    if task_data.tags:
        tags = get_or_create_tags(db, task_data.tags)
    
    # Create the task
    now = datetime.now(timezone.utc)
    task_dict = task_data.model_dump(exclude={"tags", "subtasks"})
    
    # Override source if provided
    if source:
        task_dict["source"] = source
    elif not task_dict.get("source"):
        task_dict["source"] = "api"
    
    # Handle recurrence
    if task_data.recurrence:
        task_dict["recurrence"] = task_data.recurrence.model_dump()
    
    # Set timestamps
    task_dict["created_at"] = now
    task_dict["updated_at"] = now
    
    task = Task(**task_dict)
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Associate tags with the task
    for tag in tags:
        association = TaskTag(task_id=task.id, tag_id=tag.id)
        db.add(association)
    
    db.commit()
    db.refresh(task)
    
    # Create subtasks if provided
    if hasattr(task_data, 'subtasks') and task_data.subtasks:
        for subtask_name in task_data.subtasks:
            create_task(
                db=db,
                task_data=TaskCreate(
                    name=subtask_name,
                    parent_task_id=task.id,
                    source=source or "api"
                ),
                source=source or "api"
            )
    
    return task


def get_task(db: Session, task_id: str, include_subtasks: bool = True) -> Optional[Task]:
    """
    Get a single task by ID.
    
    Args:
        db: Database session
        task_id: Task ID
        include_subtasks: Whether to eager load subtasks
    
    Returns:
        Task instance or None
    """
    query = db.query(Task).filter(Task.id == task_id)
    if include_subtasks:
        query = query.options(joinedload(Task.subtasks), joinedload(Task.tags))
    return query.first()


def list_tasks(
    db: Session,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[List[str]] = None,
    parent: Optional[str] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[List[Task], int]:
    """
    List tasks with filtering and pagination.
    
    Args:
        db: Database session
        status: Filter by status
        priority: Filter by priority
        tag: List of tag names to filter by (AND logic)
        parent: 'none' for top-level only, or a task ID for subtasks
        due_before: Filter tasks due before this date
        due_after: Filter tasks due after this date
        search: Substring search on name and description
        sort: Field to sort by (prefix '-' for descending)
        limit: Max results per page
        offset: Page offset
    
    Returns:
        Tuple of (tasks, total_count)
    """
    query = db.query(Task).options(joinedload(Task.tags))
    
    # Build filters
    filters = []
    
    if status:
        filters.append(Task.status == status)
    
    if priority:
        filters.append(Task.priority == priority)
    
    if parent == "none":
        filters.append(Task.parent_task_id.is_(None))
    elif parent and parent != "none":
        filters.append(Task.parent_task_id == parent)
    
    if due_before:
        if not due_before.tzinfo:
            due_before = due_before.replace(tzinfo=timezone.utc)
        filters.append(Task.due_date <= due_before)
    
    if due_after:
        if not due_after.tzinfo:
            due_after = due_after.replace(tzinfo=timezone.utc)
        filters.append(Task.due_date >= due_after)
    
    if search:
        search_pattern = f"%{search}%"
        filters.append(or_(
            Task.name.ilike(search_pattern),
            Task.description.ilike(search_pattern)
        ))
    
    # Tag filtering
    if tag:
        # Get tag IDs for all specified tags
        normalized_tags = [normalize_tag_name(t) for t in tag]
        tag_ids = db.query(Tag.id).filter(
            func.lower(Tag.name).in_(normalized_tags)
        ).all()
        tag_ids = [tid for tid, in tag_ids]
        
        if tag_ids:
            # For each tag, we need to find tasks that have ALL of them
            for tag_id in tag_ids:
                query = query.filter(
                    Task.id.in_(
                        db.query(TaskTag.task_id).filter(TaskTag.tag_id == tag_id)
                    )
                )
    
    # Apply all filters
    if filters:
        query = query.filter(and_(*filters))
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    if sort:
        sort_field = sort.lstrip('-')
        sort_direction = desc if sort.startswith('-') else asc
        
        # Map sort field to actual column
        sort_mapping = {
            "created_at": Task.created_at,
            "updated_at": Task.updated_at,
            "due_date": Task.due_date,
            "priority": Task.priority,
            "name": Task.name
        }
        
        if sort_field in sort_mapping:
            query = query.order_by(sort_direction(sort_mapping[sort_field]))
        elif sort_field == "status":
            # Custom sorting for status
            query = query.order_by(
                sort_direction(
                    func.coalesce(
                        STATUS_ORDER[Task.status],
                        999
                    )
                )
            )
        elif sort_field == "priority_order":
            # Custom sorting for priority
            query = query.order_by(
                sort_direction(
                    func.coalesce(
                        PRIORITY_ORDER[Task.priority],
                        999
                    )
                )
            )
    else:
        # Default sort: created_at descending
        query = query.order_by(desc(Task.created_at))
    
    # Apply pagination
    tasks = query.offset(offset).limit(limit).all()
    
    return tasks, total


def update_task(db: Session, task_id: str, update_data: TaskUpdate) -> Optional[Task]:
    """
    Update a task.
    
    Args:
        db: Database session
        task_id: Task ID
        update_data: Update data
    
    Returns:
        Updated Task instance or None
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None
    
    # Prevent creating subtasks of subtasks
    if update_data.parent_task_id:
        parent_task = db.query(Task).filter(Task.id == update_data.parent_task_id).first()
        if parent_task and parent_task.parent_task_id:
            raise ValueError("Subtasks cannot have subtasks (max nesting level is 1)")
    
    # Update fields
    if update_data.name is not None:
        task.name = update_data.name
    if update_data.description is not None:
        task.description = update_data.description
    if update_data.status is not None:
        task.status = update_data.status
    if update_data.priority is not None:
        task.priority = update_data.priority
    if update_data.due_date is not None:
        task.due_date = update_data.due_date
    if update_data.parent_task_id is not None:
        task.parent_task_id = update_data.parent_task_id
    if update_data.recurrence is not None:
        task.recurrence = update_data.recurrence.model_dump() if update_data.recurrence else None
    if update_data.source is not None:
        task.source = update_data.source
    
    # Update tags
    if update_data.tags is not None:
        # Clear existing tag associations
        db.query(TaskTag).filter(TaskTag.task_id == task.id).delete()
        
        # Add new tags
        tags = get_or_create_tags(db, update_data.tags)
        for tag in tags:
            association = TaskTag(task_id=task.id, tag_id=tag.id)
            db.add(association)
    
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    
    return task


def delete_task(db: Session, task_id: str) -> bool:
    """
    Delete a task and its subtasks.
    
    Args:
        db: Database session
        task_id: Task ID
    
    Returns:
        True if deleted, False if not found
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return False
    
    # Delete the task (cascade will handle subtasks due to relationship config)
    db.delete(task)
    db.commit()
    return True


def complete_task(db: Session, task_id: str) -> Optional[Task]:
    """
    Mark a task as done. If it's recurring, spawn the next occurrence.
    
    Args:
        db: Database session
        task_id: Task ID
    
    Returns:
        The original task (now marked as done)
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None
    
    # Only update if not already done
    if task.status != "done":
        task.status = "done"
        task.updated_at = datetime.now(timezone.utc)
        
        # Spawn next occurrence if recurring
        if should_spawn_next_occurrence(task):
            new_task = clone_task_for_recurrence(db, task)
            db.add(new_task)
        
        db.commit()
        db.refresh(task)
    
    return task


def clone_task_for_recurrence(db: Session, original_task: Task) -> Task:
    """
    Create a new task as the next occurrence of a recurring task.
    
    Args:
        db: Database session
        original_task: The original recurring task
    
    Returns:
        The new task instance
    """
    # Compute new due date
    new_due_date = None
    if original_task.due_date and original_task.recurrence:
        new_due_date = compute_next_due_date(original_task.due_date, original_task.recurrence)
    
    now = datetime.now(timezone.utc)
    
    # Create new task with same properties except status, id, and dates
    new_task = Task(
        name=original_task.name,
        description=original_task.description,
        status="todo",  # Reset to todo
        priority=original_task.priority,
        due_date=new_due_date,
        parent_task_id=original_task.parent_task_id,
        recurrence=original_task.recurrence,  # Keep recurrence rule
        source=original_task.source,
        created_at=now,
        updated_at=now
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Copy tags
    for tag in original_task.tags:
        association = TaskTag(task_id=new_task.id, tag_id=tag.id)
        db.add(association)
    
    db.commit()
    db.refresh(new_task)
    
    return new_task


def get_changed_tasks(db: Session, since: datetime) -> List[Task]:
    """
    Get tasks changed since a specific timestamp.
    
    Args:
        db: Database session
        since: Timestamp to filter from
    
    Returns:
        List of tasks changed since the timestamp
    """
    if not since.tzinfo:
        since = since.replace(tzinfo=timezone.utc)
    
    return db.query(Task).filter(
        Task.updated_at > since
    ).order_by(Task.updated_at).all()


def get_task_detail_response(db: Session, task: Task) -> TaskDetailResponse:
    """
    Convert a task to a detailed response with subtasks.
    
    Args:
        db: Database session
        task: Task instance
    
    Returns:
        TaskDetailResponse
    """
    subtasks = db.query(Task).filter(
        Task.parent_task_id == task.id
    ).options(joinedload(Task.tags)).all()
    
    return TaskDetailResponse(
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
        updated_at=task.updated_at,
        subtasks=[TaskResponse(
            id=st.id,
            name=st.name,
            description=st.description,
            status=st.status,
            priority=st.priority,
            due_date=st.due_date,
            parent_task_id=st.parent_task_id,
            recurrence=st.recurrence,
            source=st.source,
            tags=[tag.name for tag in st.tags] if st.tags else [],
            created_at=st.created_at,
            updated_at=st.updated_at
        ) for st in subtasks]
    )
