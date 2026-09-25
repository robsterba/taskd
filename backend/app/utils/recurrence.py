"""Recurrence logic for tasks."""
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, Dict, Any


def compute_next_due_date(current_due_date: datetime, recurrence: Dict[str, Any]) -> Optional[datetime]:
    """
    Compute the next due date based on the recurrence rule.
    
    Args:
        current_due_date: The current task's due date
        recurrence: The recurrence rule dict with 'interval' and 'interval_count'
    
    Returns:
        The next due date as a timezone-aware datetime, or None if computation fails
    """
    if not current_due_date or not recurrence:
        return None
    
    interval = recurrence.get("interval", "daily")
    interval_count = recurrence.get("interval_count", 1)
    
    if not current_due_date.tzinfo:
        # Assume UTC if no timezone
        current_due_date = current_due_date.replace(tzinfo=timezone.utc)
    
    try:
        if interval == "daily":
            return current_due_date + timedelta(days=interval_count)
        elif interval == "weekly":
            return current_due_date + timedelta(weeks=interval_count)
        elif interval == "monthly":
            return current_due_date + relativedelta(months=interval_count)
        else:
            # Unknown interval, default to daily
            return current_due_date + timedelta(days=interval_count)
    except Exception:
        # If date computation fails, return None
        return None


def should_spawn_next_occurrence(task) -> bool:
    """
    Determine if a new occurrence should be spawned when a task is completed.
    
    Spawn if:
    - Task has a recurrence rule
    - Task is not archived
    
    Args:
        task: The task model instance
    
    Returns:
        True if a new occurrence should be spawned
    """
    return task.recurrence is not None and task.status != "archived"
