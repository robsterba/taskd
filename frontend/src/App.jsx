import { useState, useEffect } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import TaskList from './pages/TaskList'
import TaskDetail from './pages/TaskDetail'
import NotFound from './pages/NotFound'
import './App.css'
import './pages/TaskList.css'
import './pages/TaskDetail.css'
import './pages/NotFound.css'

function App() {
  const [tasks, setTasks] = useState([])
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const API_BASE = '/api/v1'

  const fetchTasks = async (params = {}) => {
    setLoading(true)
    setError(null)
    try {
      const queryString = new URLSearchParams(params).toString()
      const response = await fetch(`${API_BASE}/tasks?${queryString}`)
      if (!response.ok) {
        throw new Error('Failed to fetch tasks')
      }
      const data = await response.json()
      setTasks(data.tasks || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchTags = async () => {
    try {
      const response = await fetch(`${API_BASE}/tags`)
      if (!response.ok) {
        throw new Error('Failed to fetch tags')
      }
      const data = await response.json()
      setTags(data || [])
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    fetchTasks()
    fetchTags()
  }, [])

  const createTask = async (taskData, source = 'gui') => {
    try {
      const response = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'source': source
        },
        body: JSON.stringify(taskData)
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create task')
      }
      const newTask = await response.json()
      await fetchTasks()
      return newTask
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const updateTask = async (taskId, updateData) => {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update task')
      }
      await fetchTasks()
      return await response.json()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const deleteTask = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to delete task')
      }
      await fetchTasks()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const completeTask = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}/complete`, {
        method: 'POST'
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to complete task')
      }
      await fetchTasks()
      return await response.json()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const getTask = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}`)
      if (!response.ok) {
        throw new Error('Failed to fetch task')
      }
      return await response.json()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 onClick={() => navigate('/')}>taskd</h1>
        {error && <div className="error-banner">{error}</div>}
      </header>
      
      <main className="app-main">
        <Routes>
          <Route
            path="/"
            element={
              <TaskList
                tasks={tasks}
                tags={tags}
                loading={loading}
                onCreateTask={createTask}
                onUpdateTask={updateTask}
                onDeleteTask={deleteTask}
                onCompleteTask={completeTask}
                onRefresh={fetchTasks}
                onViewTask={(task) => navigate(`/tasks/${task.id}`)}
              />
            }
          />
          <Route
            path="/tasks/:taskId"
            element={
              <TaskDetail
                tasks={tasks}
                tags={tags}
                onUpdateTask={updateTask}
                onDeleteTask={deleteTask}
                onCompleteTask={completeTask}
                onNavigateBack={() => navigate('/')}
              />
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
