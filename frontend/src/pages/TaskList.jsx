import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

const STATUS_OPTS = [
  { value: null, label: 'All' },
  { value: 'todo', label: 'Todo' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'done', label: 'Done' },
  { value: 'archived', label: 'Archived' }
]

const PRIORITY_OPTS = [
  { value: null, label: 'All' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' }
]

const SORT_OPTS = [
  { value: '-created_at', label: 'Newest' },
  { value: 'created_at', label: 'Oldest' },
  { value: 'due_date', label: 'Due Soon' },
  { value: '-due_date', label: 'Due Later' },
  { value: 'priority', label: 'Priority (Low to High)' },
  { value: '-priority', label: 'Priority (High to Low)' },
  { value: 'name', label: 'Name (A-Z)' },
  { value: '-name', label: 'Name (Z-A)' }
]

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

const parseQuickAdd = (text) => {
  const tags = []
  const priorityMatch = text.match(/!(\w+)/)
  let priority = null

  if (priorityMatch) {
    const p = priorityMatch[1].toLowerCase()
    if (['urgent', 'high', 'medium', 'low'].includes(p)) {
      priority = p
      text = text.replace(priorityMatch[0], '').trim()
    }
  }

  // Extract tags
  const tagRegex = /#(\S+)/g
  let match
  const tagMatches = []
  while ((match = tagRegex.exec(text)) !== null) {
    tagMatches.push(match[1])
    text = text.replace(match[0], '').trim()
  }

  return {
    name: text.trim(),
    tags: tagMatches.length > 0 ? tagMatches : undefined,
    priority
  }
}

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
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
  })
}

const hasRecurrence = (task) => {
  return task.recurrence && Object.keys(task.recurrence).length > 0
}

function TaskList({
  tasks,
  tags,
  loading,
  onCreateTask,
  onUpdateTask,
  onDeleteTask,
  onCompleteTask,
  onRefresh,
  onViewTask
}) {
  const navigate = useNavigate()
  const [quickAdd, setQuickAdd] = useState('')
  const [filters, setFilters] = useState({
    status: ['todo', 'in_progress'],
    priority: [],
    tag: [],
    parent: 'none',
    search: '',
    sort: '-created_at'
  })
  const [showFilters, setShowFilters] = useState(false)
  const [polling, setPolling] = useState(true)

  const filteredTasks = tasks.filter(task => {
    // Filter by status (array)
    if (filters.status.length > 0 && !filters.status.includes(task.status)) return false

    // Filter by priority (array)
    if (filters.priority.length > 0 && !filters.priority.includes(task.priority)) return false

    // Filter by tag (array) - task must have ALL selected tags
    if (filters.tag.length > 0 && (!task.tags || filters.tag.some(tag => !task.tags.includes(tag)))) return false

    if (filters.parent === 'none' && task.parent_task_id) return false
    if (filters.parent && filters.parent !== 'none' && task.parent_task_id !== filters.parent) return false
    if (filters.search && !task.name.toLowerCase().includes(filters.search.toLowerCase()) &&
        !task.description?.toLowerCase().includes(filters.search.toLowerCase())) return false
    return true
  })

  // Sort tasks
  const sortedTasks = [...filteredTasks].sort((a, b) => {
    const sort = filters.sort || '-created_at'
    const descending = sort.startsWith('-')
    const field = sort.replace('-', '')

    let aVal, bVal

    switch(field) {
      case 'created_at':
        aVal = new Date(a.created_at).getTime()
        bVal = new Date(b.created_at).getTime()
        break
      case 'updated_at':
        aVal = new Date(a.updated_at).getTime()
        bVal = new Date(b.updated_at).getTime()
        break
      case 'due_date':
        aVal = a.due_date ? new Date(a.due_date).getTime() : Infinity
        bVal = b.due_date ? new Date(b.due_date).getTime() : Infinity
        break
      case 'priority':
        aVal = Object.keys(PRIORITY_OPTS).indexOf(a.priority)
        bVal = Object.keys(PRIORITY_OPTS).indexOf(b.priority)
        break
      case 'name':
        aVal = a.name.toLowerCase()
        bVal = b.name.toLowerCase()
        break
      default:
        aVal = new Date(a.created_at).getTime()
        bVal = new Date(b.created_at).getTime()
    }

    if (aVal < bVal) return descending ? 1 : -1
    if (aVal > bVal) return descending ? -1 : 1
    return 0
  })

  // Poll for changes every 30 seconds
  useEffect(() => {
    if (!polling) return
    const interval = setInterval(() => {
      onRefresh()
    }, 30000)
    return () => clearInterval(interval)
  }, [polling, onRefresh])

  const handleQuickAdd = useCallback(async (e) => {
    if (e.key === 'Enter' && quickAdd.trim()) {
      e.preventDefault()
      const parsed = parseQuickAdd(quickAdd)

      await onCreateTask({
        name: parsed.name || quickAdd.trim(),
        tags: parsed.tags,
        priority: parsed.priority,
        status: 'todo'
      })

      setQuickAdd('')
    }
  }, [quickAdd, onCreateTask])

  const handleToggleStatus = useCallback(async (task, e) => {
    e.stopPropagation()
    const newStatus = task.status === 'todo' ? 'in_progress' :
                     task.status === 'in_progress' ? 'done' : 'todo'

    // Optimistic update
    const originalTasks = [...tasks]
    const updatedTask = { ...task, status: newStatus, updated_at: new Date().toISOString() }

    try {
      await onUpdateTask(task.id, { status: newStatus })
    } catch (err) {
      // Revert on error
      setTasks(originalTasks)
    }
  }, [tasks, onUpdateTask])

  const handleComplete = useCallback(async (task, e) => {
    e.stopPropagation()
    await onCompleteTask(task.id)
  }, [onCompleteTask])

  const handleToggleSubtaskStatus = useCallback(async (task, subtask, e) => {
    e.stopPropagation()
    await onUpdateTask(subtask.id, {
      status: subtask.status === 'done' ? 'todo' : 'done'
    })
  }, [onUpdateTask])

  const taskCount = sortedTasks.length
  const topLevelTasks = sortedTasks.filter(t => !t.parent_task_id)
  const subtasksByParent = {}
  sortedTasks.forEach(t => {
    if (t.parent_task_id) {
      if (!subtasksByParent[t.parent_task_id]) {
        subtasksByParent[t.parent_task_id] = []
      }
      subtasksByParent[t.parent_task_id].push(t)
    }
  })

  const subtaskCount = (taskId) => {
    const subtasks = subtasksByParent[taskId] || []
    const doneCount = subtasks.filter(s => s.status === 'done').length
    return { total: subtasks.length, done: doneCount }
  }



  return (
    <div className="task-list">
      <div className="task-list-header">
        <input
          type="text"
          placeholder="Quick add task... (#tag !priority)"
          value={quickAdd}
          onChange={(e) => setQuickAdd(e.target.value)}
          onKeyDown={handleQuickAdd}
          className="quick-add-input"
        />

        <div className="task-list-controls">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="filter-toggle"
          >
            {showFilters ? 'Hide Filters' : 'Show Filters'}
          </button>
          <button onClick={onRefresh} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {showFilters && (
        <div className="filters-panel">
          <div className="filter-group">
            <label>Status:</label>
            <div className="checkbox-group">
              {STATUS_OPTS.filter(opt => opt.value !== null).map(opt => (
                <label key={opt.value} className="filter-checkbox">
                  <input
                    type="checkbox"
                    checked={filters.status.includes(opt.value)}
                    onChange={(e) => {
                      const newStatus = e.target.checked
                        ? [...filters.status, opt.value]
                        : filters.status.filter(s => s !== opt.value)
                      setFilters({...filters, status: newStatus})
                    }}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <label>Priority:</label>
            <div className="checkbox-group">
              {PRIORITY_OPTS.filter(opt => opt.value !== null).map(opt => (
                <label key={opt.value} className="filter-checkbox">
                  <input
                    type="checkbox"
                    checked={filters.priority.includes(opt.value)}
                    onChange={(e) => {
                      const newPriority = e.target.checked
                        ? [...filters.priority, opt.value]
                        : filters.priority.filter(p => p !== opt.value)
                      setFilters({...filters, priority: newPriority})
                    }}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <label>Tag:</label>
            <div className="checkbox-group">
              {tags.map(tag => (
                <label key={tag.name} className="filter-checkbox">
                  <input
                    type="checkbox"
                    checked={filters.tag.includes(tag.name)}
                    onChange={(e) => {
                      const newTags = e.target.checked
                        ? [...filters.tag, tag.name]
                        : filters.tag.filter(t => t !== tag.name)
                      setFilters({...filters, tag: newTags})
                    }}
                  />
                  <span style={{ backgroundColor: tag.color || '#ccc' }}>
                    {tag.name}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <label>Sort:</label>
            <select
              value={filters.sort}
              onChange={(e) => setFilters({...filters, sort: e.target.value})}
            >
              {SORT_OPTS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div className="filter-group search-group">
            <label>Search:</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({...filters, search: e.target.value})}
              placeholder="Search tasks..."
            />
          </div>

          <button
            onClick={() => setFilters({
              status: ['todo', 'in_progress'],
              priority: [],
              tag: [],
              parent: 'none',
              search: '',
              sort: '-created_at'
            })}
            className="clear-filters"
          >
            Clear Filters
          </button>
        </div>
      )}

      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
          <span>Loading tasks...</span>
        </div>
      ) : (
        <>
          {taskCount === 0 ? (
            <div className="empty-state">
              <p>No tasks found. Add one using the input above!</p>
            </div>
          ) : (
            <div className="tasks-container">
              {topLevelTasks.map(task => {
                const { total, done } = subtaskCount(task.id)
                const hasSubtasks = total > 0

                return (
                  <div
                    key={task.id}
                    className={`task-card ${priorityClass(task.priority)} ${statusClass(task.status)}`}
                    onClick={() => onViewTask && onViewTask(task)}
                  >
                    <div className="task-header">
                      <input
                        type="checkbox"
                        checked={task.status === 'done'}
                        onClick={(e) => handleToggleStatus(task, e)}
                        onChange={() => {}}
                        className="task-checkbox"
                      />
                      <h3 className="task-name">{task.name}</h3>

                      <div className="task-actions">
                        {hasRecurrence(task) && (
                          <span className="recurrence-icon" title="Recurring">🔄</span>
                        )}
                        {hasSubtasks && (
                          <span className="subtask-count" onClick={(e) => e.stopPropagation()}>
                            {done}/{total}
                          </span>
                        )}
                      </div>
                    </div>

                    {task.description && (
                      <div className="task-description">
                        <ReactMarkdown>{task.description}</ReactMarkdown>
                      </div>
                    )}

                    <div className="task-meta">
                      <span className={`priority-badge ${task.priority}`}>
                        {priorityLabel(task.priority)}
                      </span>

                      {task.due_date && (
                        <span className={`due-date ${isOverdue(task.due_date) ? 'overdue' : ''}`}>
                          {formatDueDate(task.due_date)}
                        </span>
                      )}

                      {task.tags && task.tags.length > 0 && (
                        <div className="task-tags">
                          {task.tags.map(tag => (
                            <span key={tag} className="tag-chip" onClick={(e) => {
                              e.stopPropagation()
                              // Toggle tag: if already selected, remove it; otherwise add it
                              const newTags = filters.tag.includes(tag)
                                ? filters.tag.filter(t => t !== tag)
                                : [...filters.tag, tag]
                              setFilters({...filters, tag: newTags})
                              setShowFilters(true)
                            }}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Render subtasks */}
                    {hasSubtasks && (
                      <div className="subtasks-preview">
                        {(subtasksByParent[task.id] || []).slice(0, 3).map(subtask => (
                          <div
                            key={subtask.id}
                            className={`subtask-item ${subtask.status === 'done' ? 'done' : ''}`}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <input
                              type="checkbox"
                              checked={subtask.status === 'done'}
                              onClick={(e) => handleToggleSubtaskStatus(task, subtask, e)}
                              onChange={() => {}}
                            />
                            <span>{subtask.name}</span>
                          </div>
                        ))}
                        {total > 3 && (
                          <div className="subtask-more">+{total - 3} more</div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      <div className="task-stats">
        <span>{taskCount} {taskCount === 1 ? 'task' : 'tasks'}</span>
      </div>
    </div>
  )
}

export default TaskList
