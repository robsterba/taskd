"""SQLAlchemy database models."""
from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Enum, Table, Boolean, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.sqlite import TEXT

from .database import Base


# Association table for many-to-many relationship between tasks and tags
class TaskTag(Base):
    __tablename__ = "task_tag"
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False, index=True)
    color = Column(String(7), nullable=True)  # Hex color code like #FF0000
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationship to tasks
    tasks = relationship("Task", secondary="task_tag", back_populates="tags", lazy="selectin")
    
    __table_args__ = (
        Index("idx_tag_name", "name"),
    )


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        Enum("todo", "in_progress", "done", "archived", name="task_status"),
        nullable=False,
        default="todo"
    )
    priority = Column(
        Enum("low", "medium", "high", "urgent", name="task_priority"),
        nullable=False,
        default="medium"
    )
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    parent_task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Recurrence rule stored as JSON
    recurrence = Column(JSON, nullable=True)
    
    # Source of task creation
    source = Column(String(50), nullable=False, default="api")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
    subtasks = relationship("Task", back_populates="parent_task", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="task_tag", back_populates="tasks", lazy="selectin")
    
    __table_args__ = (
        Index("idx_task_status", "status"),
        Index("idx_task_priority", "priority"),
        Index("idx_task_parent", "parent_task_id"),
        Index("idx_task_created", "created_at"),
        Index("idx_task_updated", "updated_at"),
    )
    
    def __repr__(self):
        return f"Task(id={self.id}, name={self.name}, status={self.status})"
