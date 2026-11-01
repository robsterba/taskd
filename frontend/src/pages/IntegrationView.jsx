import { useState, useEffect, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import { tagChipStyle } from '../utils/tagColors'
import { priorityLabel, formatDueDate, isOverdue, relativeTime } from '../utils/format'
import './IntegrationView.css'

// docker-update-checker conventions used for display only, with graceful
// fallback to the raw names when a task does not match them.
const DUC_SOURCE = 'docker-update-checker'
const DUC_TITLE_PREFIX = 'Container updates: '
const DUC_UPDATE_PREFIX = 'Update '

const STATUS_OPTS = [
  { value: 'pending', label: 'Pending' },
  { value: 'updated', label: 'Updated' },
  { value: 'all', label: 'All' }
]

const SORT_OPTS = [
  { value: 'updated', label: 'Recently updated' },
  { value: 'created', label: 'Newest' },
  { value: 'name', label: 'Name (A-Z)' },
  { value: 'pending', label: 'Most pending' }
]

const isOpen = (status) => status === 'todo' || status === 'in_progress'

function IntegrationView({
  source,
  label,
  tasks,
  tags,
  loading,
  truncated = false,
  onUpdateTask,
  onRefresh,
  onViewTask,
  refreshInterval = 30
}) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('pending')
  const [sort, setSort] = useState('updated')
  const [collapsed, setCollapsed] = useState(() => new Set())

  const isDuc = source === DUC_SOURCE

  // Group tasks: one card per top-level task with its subtasks.
  const groups = useMemo(() => {
    const subsByParent = {}
    tasks.forEach(t => {
      if (t.parent_task_id) {
        if (!subsByParent[t.parent_task_id]) subsByParent[t.parent_task_id] = []
        subsByParent[t.parent_task_id].push(t)
      }
    })
    return tasks
      .filter(t => !t.parent_task_id)
      .map(parent => {
        const subs = (subsByParent[parent.id] || [])
          .slice()
          .sort((a, b) => a.name.localeCompare(b.name))
        const open = subs.filter(s => isOpen(s.status)).length
        return { task: parent, subs, open, done: subs.length - open }
      })
  }, [tasks])

  const filteredGroups = useMemo(() => {
    const q = search.trim().toLowerCase()
    return groups
      .map(group => {
        let subs = group.subs
        if (statusFilter === 'pending') subs = subs.filter(s => isOpen(s.status))
        else if (statusFilter === 'updated') subs = subs.filter(s => s.status === 'done')

        let hostMatch = true
        if (q) {
          hostMatch =
            group.task.name.toLowerCase().includes(q) ||
            (group.task.description || '').toLowerCase().includes(q)
          if (!hostMatch) subs = subs.filter(s => s.name.toLowerCase().includes(q))
        }

        let visible
        if (group.subs.length > 0) {
          visible = subs.length > 0
        } else {
          const statusOk = statusFilter === 'all'
            ? true
            : statusFilter === 'pending' ? isOpen(group.task.status) : group.task.status === 'done'
          visible = statusOk && hostMatch
        }
        return { ...group, filteredSubs: subs, visible }
      })
      .filter(group => group.visible)
  }, [groups, statusFilter, search])

  const sortedGroups = useMemo(() => {
    const list = [...filteredGroups]
    switch (sort) {
      case 'created':
        list.sort((a, b) => new Date(b.task.created_at) - new Date(a.task.created_at))
        break
      case 'name':
        list.sort((a, b) => a.task.name.localeCompare(b.task.name))
        break
      case 'pending':
        list.sort((a, b) => b.open - a.open || a.task.name.localeCompare(b.task.name))
        break
      default:
        list.sort((a, b) => new Date(b.task.updated_at) - new Date(a.task.updated_at))
    }
    return list
  }, [filteredGroups, sort])

  // Summary counts. Parents with subtasks are excluded from the item
  // counts: their status is derived from the subtasks, so counting both
  // would double-report.
  const summary = useMemo(() => {
    const parentIds = new Set(tasks.filter(t => t.parent_task_id).map(t => t.parent_task_id))
    const countable = tasks.filter(t => t.parent_task_id || !parentIds.has(t.id))
    return {
      pending: countable.filter(t => isOpen(t.status)).length,
      done: countable.filter(t => t.status === 'done').length,
      hosts: tasks.filter(t => !t.parent_task_id).length
    }
  }, [tasks])

  // Poll for changes based on the configured refresh interval (0 = off)
  useEffect(() => {
    if (!refreshInterval) return
    const interval = setInterval(() => {
      onRefresh()
    }, refreshInterval * 1000)
    return () => clearInterval(interval)
  }, [refreshInterval, onRefresh])

  const toggleCollapsed = (taskId) => {
    setCollapsed(prev => {
      const next = new Set(prev)
      if (next.has(taskId)) next.delete(taskId)
      else next.add(taskId)
      return next
    })
  }

  const handleToggleStatus = (task, e) => {
    e.stopPropagation()
    onUpdateTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' })
  }

  const hostLabel = (task) => {
    if (isDuc && task.name.startsWith(DUC_TITLE_PREFIX)) {
      return task.name.slice(DUC_TITLE_PREFIX.length)
    }
    return task.name
  }

  const rowLabel = (sub) => {
    if (isDuc && sub.name.startsWith(DUC_UPDATE_PREFIX)) {
      return sub.name.slice(DUC_UPDATE_PREFIX.length)
    }
    return sub.name
  }

  const renderHostCard = (group) => {
    const task = group.task
    const isCollapsed = collapsed.has(task.id)
    const progress = isDuc
      ? (group.subs.length === 0 ? 'up to date' : `${group.open} pending`)
      : `${group.done}/${group.subs.length}`

    return (
      <div key={task.id} className={`iv-card ${isCollapsed ? 'iv-collapsed' : ''}`}>
        <div className="iv-host-header" onClick={() => toggleCollapsed(task.id)}>
          <span className="iv-chevron" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </span>
          <div className="iv-host-title">
            {isDuc && <span className="iv-overline">Container updates</span>}
            <span className="iv-host-name">{hostLabel(task)}</span>
          </div>
          <span className="iv-progress">{progress}</span>
          <button
            className="iv-open"
            onClick={(e) => {
              e.stopPropagation()
              onViewTask(task)
            }}
          >
            Open
          </button>
        </div>

        {!isCollapsed && (
          <>
            {isDuc ? (
              <div className="iv-host-meta">
                Managed by docker-update-checker &middot; Updated {relativeTime(task.updated_at)}
              </div>
            ) : (
              <>
                {task.description && (
                  <div className="task-description iv-host-description">
                    <ReactMarkdown>{task.description}</ReactMarkdown>
                  </div>
                )}
                {task.tags && task.tags.length > 0 && (
                  <div className="iv-host-tags">
                    {task.tags.map(tag => {
                      const tagObj = tags.find(t => t.name === tag)
                      return (
                        <span key={tag} className="tag-chip" style={tagChipStyle(tagObj?.color)}>
                          {tag}
                        </span>
                      )
                    })}
                  </div>
                )}
              </>
            )}

            <div className="iv-rows">
              {group.filteredSubs.map(sub => (
                <div
                  key={sub.id}
                  className={`iv-row ${sub.status === 'done' ? 'done' : ''}`}
                  onClick={() => onViewTask(sub)}
                  title="Open details"
                >
                  <input
                    type="checkbox"
                    className="task-checkbox"
                    checked={sub.status === 'done'}
                    onClick={(e) => handleToggleStatus(sub, e)}
                    onChange={() => {}}
                  />
                  <span className="iv-row-name">{rowLabel(sub)}</span>
                  {sub.status === 'done' && (
                    <span className="iv-row-state">{isDuc ? 'updated' : 'done'}</span>
                  )}
                </div>
              ))}
              {group.filteredSubs.length === 0 && (
                <div className="iv-row-empty">No matching items</div>
              )}
            </div>
          </>
        )}
      </div>
    )
  }

  const renderPlainCard = (group) => {
    const task = group.task
    return (
      <div key={task.id} className="task-card" onClick={() => onViewTask && onViewTask(task)}>
        <div className="task-header">
          <input
            type="checkbox"
            className="task-checkbox"
            checked={task.status === 'done'}
            onClick={(e) => handleToggleStatus(task, e)}
            onChange={() => {}}
          />
          <h3 className="task-name">{task.name}</h3>
        </div>
        {task.description && (
          <div className="task-description">
            <ReactMarkdown>{task.description}</ReactMarkdown>
          </div>
        )}
        <div className="task-meta">
          {task.priority && (
            <span className={`priority-badge ${task.priority}`}>
              {priorityLabel(task.priority)}
            </span>
          )}
          {task.due_date && (
            <span className={`due-date ${isOverdue(task.due_date) ? 'overdue' : ''}`}>
              {formatDueDate(task.due_date)}
            </span>
          )}
          {task.tags && task.tags.length > 0 && (
            <div className="task-tags">
              {task.tags.map(tag => {
                const tagObj = tags.find(t => t.name === tag)
                return (
                  <span key={tag} className="tag-chip" style={tagChipStyle(tagObj?.color)}>
                    {tag}
                  </span>
                )
              })}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="integration-view">
      <div className="iv-summary">
        <span className="iv-stat">
          <strong>{summary.pending}</strong> {isDuc ? 'pending updates' : 'open'}
        </span>
        <span className="iv-stat">
          <strong>{summary.done}</strong> {isDuc ? 'updated' : 'done'}
        </span>
        <span className="iv-stat">
          <strong>{summary.hosts}</strong> {isDuc ? 'hosts' : 'tasks'}
        </span>
        {truncated && (
          <span className="iv-truncated">Showing the first 500 tasks</span>
        )}
      </div>

      <div className="iv-controls">
        <input
          type="text"
          className="iv-search"
          placeholder={`Search ${label || 'tasks'}...`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUS_OPTS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)}>
          {SORT_OPTS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <button onClick={onRefresh} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
          <span>Loading tasks...</span>
        </div>
      ) : (
        <>
          {sortedGroups.length === 0 ? (
            <div className="empty-state">
              <p>No integration tasks right now. They appear here once the integration creates them.</p>
            </div>
          ) : (
            <div className="iv-cards">
              {sortedGroups.map(group =>
                group.subs.length > 0 ? renderHostCard(group) : renderPlainCard(group)
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default IntegrationView
