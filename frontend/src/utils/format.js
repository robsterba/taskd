const isSameDay = (date1, date2) => {
  return date1.getFullYear() === date2.getFullYear() &&
         date1.getMonth() === date2.getMonth() &&
         date1.getDate() === date2.getDate()
}

export const isOverdue = (dueDate) => {
  if (!dueDate) return false
  const now = new Date()
  const due = new Date(dueDate)
  return due < now && !isSameDay(due, now)
}

export const formatDueDate = (dueDate) => {
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

export const relativeTime = (iso) => {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 0) return 'just now'
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  return `${months}mo ago`
}

export const priorityLabel = (priority) => {
  const map = {
    urgent: 'Urgent',
    high: 'High',
    medium: 'Medium',
    low: 'Low'
  }
  return map[priority] || priority
}

export const statusLabel = (status) => {
  const map = {
    todo: 'Todo',
    in_progress: 'In Progress',
    done: 'Done',
    archived: 'Archived'
  }
  return map[status] || status
}
