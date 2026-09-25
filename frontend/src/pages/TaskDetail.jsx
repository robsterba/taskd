import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

const priorityClass = (priority) => {
  const map = {
    urgent: 'priority-urgent',
    high: 'priority-high',
    medium: 'priority-medium',
    low: 'priority-low'
  }
  return map[priority] || ''
}

const statusClass = (status) => {
  const map = {
    todo: 'status-todo',
    in_progress: 'status-in_progress',
    done: 'status-done',
    archived: 'status-archived'
  }
  return map[status] || ''
}

const priorityLabel = (priority) => {
  const map = {
    urgent: 'Urgent',
    high: 'High',
    medium: 'Medium',
    low: 'Low'
  }
  return map[priority] || priority
}

const statusLabel = (status) => {
  const map = {
    todo: 'Todo',
    in_progress: 'In Progress',
    done: 'Done',
    archived: 'Archived'
  }
  return map[status] || status
}

const statusOptions = [
  { value: 'todo', label: 'Todo' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'done', label: 'Done' },
  { value: 'archived', label: 'Archived' }
]

const priorityOptions = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' }
]

const isOverdue = (dueDate) => {
  if (!dueDate) return false
  const now = new Date()
  const due = new Date(dueDate)
  return due < now && !isSameDay(due, now)
}

const isSameDay = (date1, date2) => {
  return date1.getFullYear() === date2.getFullYear() &&
         date1.getMonth() === date2.getMonth() &&
         date1.getDate() === date2.getDate()
}

const formatDueDate = (dueDate) => {
  if (!dueDate) return ''
  const date = new Date(dueDate)
  const now = new Date()
  
  if (isSameDay(date, now)) {
    return 'Today'
  }
  if (isSameDay(date, new Date(now.getTime() + 24 * 60 * 60 * 1000))) {
    return 'Tomorrow'
  }
  
  return date.toLocaleDateString(undefined, { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: date.getHours() || date.getMinutes() ? '2-digit' : undefined,
    minute: date.getHours() || date.getMinutes() ? '2-digit' : undefined
  })
}

function TaskDetail({
  tasks,
  tags,
  onUpdateTask,
  onDeleteTask,
  onCompleteTask,
  onNavigateBack
}) {
  const navigate = useNavigate()
  const { taskId } = useParams()
  const [task, setTask] = useState(null)
  const [editing, setEditing] = useState(false)
  const [editData, setEditData] = useState({})
  const [newSubtask, setNewSubtask] = useState('')
  const [loading, setLoading] = useState(false)

  const API_BASE = '/api/v1'

  // Fetch full task details
  useEffect(() => {
    const fetchFullTask = async () => {
      // Always fetch from API to get full details including subtasks
      if (taskId) {
        try {
          const response = await fetch(`${API_BASE}/tasks/${taskId}`)
          if (response.ok) {
            const data = await response.json()
            setTask(data)
            setEditData(data)
            return
          }
        } catch (err) {
          console.error('Failed to fetch task details:', err)
        }
        
        // Fallback: try to find in the tasks array
        if (tasks) {
          const foundTask = tasks.find(t => t.id === taskId)
          if (foundTask) {
            setTask(foundTask)
            setEditData(foundTask)
          }
        }
      }
    }
    fetchFullTask()
  }, [taskId, tasks])

  const handleSave = useCallback(async () => {
    if (!task || !task.id) return
    
    setLoading(true)
    try {
      const updated = await onUpdateTask(task.id, editData)
      setTask(updated)
      setEditing(false)
    } catch (err) {
      console.error('Failed to update task:', err)
    } finally {
      setLoading(false)
    }
  }, [task, editData, onUpdateTask])

  const handleCancel = useCallback(() => {
    setEditing(false)
    setEditData({ ...task })
  }, [task])

  const handleDelete = useCallback(async () => {
    if (!task || !task.id) return
    
    if (window.confirm(`Are you sure you want to delete "${task.name}"? This will also delete all subtasks.`)) {
      setLoading(true)
      try {
        await onDeleteTask(task.id)
        onNavigateBack()
      } catch (err) {
        console.error('Failed to delete task:', err)
      } finally {
        setLoading(false)
      }
    }
  }, [task, onDeleteTask, onNavigateBack])

  const handleComplete = useCallback(async () => {
    if (!task || !task.id) return
    
    setLoading(true)
    try {
      await onCompleteTask(task.id)
      if (onNavigateBack) {
        onNavigateBack()
      }
    } catch (err) {
      console.error('Failed to complete task:', err)
    } finally {
      setLoading(false)
    }
  }, [task, onCompleteTask, onNavigateBack])

  const handleAddSubtask = useCallback(async () => {
    if (!task || !task.id || !newSubtask.trim()) return
    
    setLoading(true)
    try {
      const subtaskData = {
        name: newSubtask.trim(),
        parent_task_id: task.id,
        status: 'todo',
        priority: 'medium',
        source: 'gui'
      }
      
      const response = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'source': 'gui'
        },
        body: JSON.stringify(subtaskData)
      })
      
      if (response.ok) {
        setNewSubtask('')
        // Refresh the task
        const updatedResponse = await fetch(`${API_BASE}/tasks/${task.id}`)
        if (updatedResponse.ok) {
          const updatedTask = await updatedResponse.json()
          setTask(updatedTask)
        }
      }
    } catch (err) {
      console.error('Failed to add subtask:', err)
    } finally {
      setLoading(false)
    }
  }, [task, newSubtask, API_BASE])

  const handleSubtaskComplete = useCallback(async (subtask) => {
    if (!subtask.id) return
    
    try {
      await onUpdateTask(subtask.id, { 
        status: subtask.status === 'done' ? 'todo' : 'done' 
      })
      // Refresh the task
      const response = await fetch(`${API_BASE}/tasks/${task.id}`)
      if (response.ok) {
        const updatedTask = await response.json()
        setTask(updatedTask)
      }
    } catch (err) {
      console.error('Failed to update subtask:', err)
    }
  }, [task, onUpdateTask, API_BASE])

  const handleDeleteSubtask = useCallback(async (subtask) => {
    if (!subtask.id) return
    
    if (window.confirm(`Are you sure you want to delete "${subtask.name}"?`)) {
      try {
        await onDeleteTask(subtask.id)
        // Refresh the task
        const response = await fetch(`${API_BASE}/tasks/${task.id}`)
        if (response.ok) {
          const updatedTask = await response.json()
          setTask(updatedTask)
        }
      } catch (err) {
        console.error('Failed to delete subtask:', err)
      }
    }
  }, [task, onDeleteTask, API_BASE])

  const handleTagChange = useCallback((tagName) => {
    const currentTags = editData.tags || []
    if (currentTags.includes(tagName)) {
      setEditData({ 
        ...editData, 
        tags: currentTags.filter(t => t !== tagName) 
      })
    } else {
      setEditData({ 
        ...editData, 
        tags: [...currentTags, tagName] 
      })
    }
  }, [editData])

  if (!task) {
    return (
      <div className="task-detail loading">
        <div className="spinner"></div>
        <span>Loading task...</span>
      </div>
    )
  }

  return (
    <div className="task-detail">
      <div className="task-detail-header">
        <button onClick={onNavigateBack} className="back-button">
          ← Back
        </button>
        <div className="task-detail-title">
          {editing ? (
            <input
              type="text"
              value={editData.name || ''}
              onChange={(e) => setEditData({ ...editData, name: e.target.value })}
              className="edit-input"
              autoFocus
            />
          ) : (
            <h1 className={priorityClass(task.priority)}>{task.name}</h1>
          )}
        </div>
        
        <div className="task-detail-actions">
          {editing ? (
            <>
              <button onClick={handleSave} disabled={loading} className="save-button">
                {loading ? 'Saving...' : 'Save'}
              </button>
              <button onClick={handleCancel} disabled={loading} className="cancel-button">
                Cancel
              </button>
            </>
          ) : (
            <>
              <button onClick={() => setEditing(true)} className="edit-button">
                Edit
              </button>
              <button onClick={handleComplete} disabled={loading} className="complete-button">
                Mark Complete
              </button>
              <button onClick={handleDelete} disabled={loading} className="delete-button">
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      <div className="task-detail-body">
        <div className="task-detail-section">
          <h2>Description</h2>
          {editing ? (
            <textarea
              value={editData.description || ''}
              onChange={(e) => setEditData({ ...editData, description: e.target.value })}
              className="edit-textarea"
              rows={5}
            />
          ) : (
            <div className="task-description markdown">
              {task.description ? (
                <ReactMarkdown>{task.description}</ReactMarkdown>
              ) : (
                <p className="no-description">No description</p>
              )}
            </div>
          )}
        </div>

        <div className="task-detail-meta">
          <div className="meta-group">
            <label>Status:</label>
            {editing ? (
              <select
                value={editData.status || ''}
                onChange={(e) => setEditData({ ...editData, status: e.target.value })}
              >
                {statusOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            ) : (
              <span className={`status-badge ${task.status}`}>
                {statusLabel(task.status)}
              </span>
            )}
          </div>

          <div className="meta-group">
            <label>Priority:</label>
            {editing ? (
              <select
                value={editData.priority || ''}
                onChange={(e) => setEditData({ ...editData, priority: e.target.value })}
              >
                {priorityOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            ) : (
              <span className={`priority-badge ${task.priority}`}>
                {priorityLabel(task.priority)}
              </span>
            )}
          </div>

          <div className="meta-group">
            <label>Due Date:</label>
            {editing ? (
              <input
                type="datetime-local"
                value={editData.due_date ? new Date(editData.due_date).toISOString().slice(0, 16) : ''}
                onChange={(e) => setEditData({ 
                  ...editData, 
                  due_date: e.target.value ? new Date(e.target.value).toISOString() : null 
                })}
              />
            ) : (
              <span className={`due-date ${isOverdue(task.due_date) ? 'overdue' : ''}`}>
                {formatDueDate(task.due_date) || 'None'}
              </span>
            )}
          </div>

          <div className="meta-group">
            <label>Source:</label>
            <span>{task.source || 'api'}</span>
          </div>
        </div>

        <div className="task-detail-section">
          <h2>Tags</h2>
          {editing ? (
            <div className="tags-editor">
              {tags.map(tag => (
                <label key={tag.name} className="tag-checkbox">
                  <input
                    type="checkbox"
                    checked={(editData.tags || []).includes(tag.name)}
                    onChange={() => handleTagChange(tag.name)}
                  />
                  <span style={{ backgroundColor: tag.color || '#ccc' }}>
                    {tag.name}
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <div className="task-tags">
              {task.tags && task.tags.length > 0 ? (
                task.tags.map(tag => {
                  const tagObj = tags.find(t => t.name === tag)
                  return (
                    <span 
                      key={tag} 
                      className="tag-chip" 
                      style={{ backgroundColor: tagObj?.color || '#ccc' }}
                    >
                      {tag}
                    </span>
                  )
                })
              ) : (
                <p className="no-tags">No tags</p>
              )}
            </div>
          )}
        </div>

        <div className="task-detail-section">
          <h2>Subtasks ({(task.subtasks || []).filter(s => s.status === 'done').length}/{(task.subtasks || []).length})</h2>
          
          {task.subtasks && task.subtasks.length > 0 && (
            <div className="subtasks-list">
              {task.subtasks.map(subtask => (
                <div key={subtask.id} className={`subtask-item ${subtask.status === 'done' ? 'done' : ''}`}>
                  <input
                    type="checkbox"
                    checked={subtask.status === 'done'}
                    onChange={() => handleSubtaskComplete(subtask)}
                  />
                  <span className="subtask-name">{subtask.name}</span>
                  <div className="subtask-meta">
                    <span className={`subtask-priority ${subtask.priority}`}>
                      {priorityLabel(subtask.priority)}
                    </span>
                    {subtask.due_date && (
                      <span className="subtask-due">
                        {formatDueDate(subtask.due_date)}
                      </span>
                    )}
                  </div>
                  <button 
                    onClick={() => handleDeleteSubtask(subtask)}
                    className="delete-subtask"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="add-subtask">
            <input
              type="text"
              placeholder="Add subtask..."
              value={newSubtask}
              onChange={(e) => setNewSubtask(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddSubtask()}
            />
            <button onClick={handleAddSubtask} disabled={!newSubtask.trim() || loading}>
              Add
            </button>
          </div>
        </div>

        {task.recurrence && (
          <div className="task-detail-section">
            <h2>Recurrence</h2>
            <div className="recurrence-info">
              <span className="recurrence-badge">
                {task.recurrence.interval} (every {task.recurrence.interval_count})
              </span>
              <p>
                {task.recurrence.interval_count === 1 
                  ? `This task repeats ${task.recurrence.interval}.`
                  : `This task repeats every ${task.recurrence.interval_count} ${task.recurrence.interval}s.`}
              </p>
            </div>
          </div>
        )}

        <div className="task-detail-section">
          <h2>Metadata</h2>
          <div className="metadata-grid">
            <div className="meta-item">
              <label>Created:</label>
              <span>{new Date(task.created_at).toLocaleString()}</span>
            </div>
            <div className="meta-item">
              <label>Last Updated:</label>
              <span>{new Date(task.updated_at).toLocaleString()}</span>
            </div>
            <div className="meta-item">
              <label>ID:</label>
              <span className="task-id">{task.id}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TaskDetail
