"""Pydantic schemas for request/response validation."""
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator
import uuid


# Enums matching the database enums
class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    archived = "archived"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class RecurrenceInterval(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


# Tag schemas
class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(TagBase):
    id: str
    created_at: datetime
    updated_at: datetime
    task_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)


# Recurrence schema
class RecurrenceRule(BaseModel):
    interval: RecurrenceInterval = Field(..., description="Recurrence interval type")
    interval_count: int = Field(default=1, ge=1, le=365, description="Interval count (e.g., every 2 weeks)")
    
    @field_validator('interval_count')
    @classmethod
    def validate_interval_count(cls, v):
        if v < 1:
            raise ValueError("interval_count must be at least 1")
        if v > 365:
            raise ValueError("interval_count must be at most 365")
        return v


# Task schemas
class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=500, description="Task name/title")
    description: Optional[str] = Field(None, description="Task description (supports markdown)")
    status: Optional[TaskStatus] = Field(default=TaskStatus.todo, description="Task status")
    priority: Optional[TaskPriority] = Field(default=TaskPriority.medium, description="Task priority")
    due_date: Optional[datetime] = Field(None, description="Due date in ISO 8601 format (UTC)")
    recurrence: Optional[RecurrenceRule] = Field(None, description="Recurrence rule")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID for subtasks")
    tags: Optional[List[str]] = Field(default_factory=list, description="List of tag names")
    source: Optional[str] = Field(default="api", max_length=50, description="Source of task creation")


class TaskCreate(TaskBase):
    subtasks: Optional[List[str]] = Field(default_factory=list, description="List of subtask names")


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    recurrence: Optional[RecurrenceRule] = None
    parent_task_id: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = Field(None, max_length=50)


class TaskResponse(TaskBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda dt: dt.isoformat() + "Z" if dt.tzinfo is None else dt.isoformat()
    })


class TaskDetailResponse(TaskResponse):
    subtasks: List["TaskResponse"] = []
    
    model_config = ConfigDict(from_attributes=True)


# Task list response with pagination
class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    limit: int
    offset: int


# Change tracking response
class TaskChangeResponse(BaseModel):
    tasks: List[TaskResponse]
    since: datetime


# Health check response
class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    timestamp: datetime


# Error responses (FastAPI provides these by default, but we define them for consistency)
class ErrorResponse(BaseModel):
    detail: str
