import { useState, useEffect, useMemo } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import TaskList from './pages/TaskList'
import TaskDetail from './pages/TaskDetail'
import NotFound from './pages/NotFound'
import Settings from './components/Settings'
import Login from './components/Login'
import { apiFetch, UNAUTHORIZED_EVENT } from './utils/api'
import './App.css'
import './index.css'
import './pages/TaskList.css'
import './pages/TaskDetail.css'
import './pages/NotFound.css'
import './components/Login.css'

const SETTINGS_STORAGE_KEY = 'taskd:settings'
const DEFAULT_SETTINGS = {
  refreshInterval: 30,
  darkMode: 'dark',
  integrations: [
    { source: 'docker-update-checker', label: 'Container Updates', visible: true }
  ]
}

function App() {
  const [tasks, setTasks] = useState([])
  const [tags, setTags] = useState([])
  const [sources, setSources] = useState([])
  const [activeTab, setActiveTab] = useState('main')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [settings, setSettings] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY))
      return saved ? { ...DEFAULT_SETTINGS, ...saved } : DEFAULT_SETTINGS
    } catch {
      return DEFAULT_SETTINGS
    }
  })
  const [theme, setTheme] = useState(() => {
    // Check localStorage first, then system preference
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme) return savedTheme

    // Check system preference for dark mode
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return settings.darkMode
    }
    return 'light'
  })
  const [appVersion, setAppVersion] = useState('')
  const [needsAuth, setNeedsAuth] = useState(false)
  const navigate = useNavigate()

  const API_BASE = '/api/v1'

  // Show the login screen whenever the API rejects our key
  useEffect(() => {
    const onUnauthorized = () => setNeedsAuth(true)
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  const handleLoginSuccess = () => {
    setNeedsAuth(false)
    setError(null)
    fetchTasks()
    fetchTags()
    fetchSources()
  }

  // Apply theme on mount and when theme changes
  useEffect(() => {
    const root = window.document.documentElement
    root.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  // Persist settings on change
  useEffect(() => {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
  }, [settings])

  // Fetch app version on mount
  useEffect(() => {
    apiFetch(`${API_BASE}/version`)
      .then(res => res.json())
      .then(data => setAppVersion(data.version || ''))
      .catch(() => setAppVersion(''))
  }, [API_BASE])

  const toggleTheme = () => {
    // Light <-> the user's preferred dark variant (blue or AMOLED)
    setTheme(prev => prev === 'light' ? settings.darkMode : 'light')
  }

  const handleSettingsChange = (newSettings) => {
    const prevDarkMode = settings.darkMode
    setSettings(newSettings)

    // Apply a changed dark variant immediately when in dark mode
    if (theme !== 'light' && newSettings.darkMode !== prevDarkMode) {
      setTheme(newSettings.darkMode)
    }
  }

  const integrations = settings.integrations ?? DEFAULT_SETTINGS.integrations
  const visibleIntegrations = useMemo(
    () => integrations.filter(i => i.visible !== false && sources.includes(i.source)),
    [integrations, sources]
  )

  const fetchTasks = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (activeTab === 'main') {
        // Keep integration tasks out of the main list
        integrations
          .filter(i => i.visible !== false && sources.includes(i.source))
          .forEach(i => params.append('exclude_source', i.source))
      } else {
        params.set('source', activeTab)
      }
      const response = await apiFetch(`${API_BASE}/tasks?${params.toString()}`)
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

  const fetchSources = async () => {
    try {
      const response = await apiFetch(`${API_BASE}/tasks/sources`)
      if (!response.ok) {
        throw new Error('Failed to fetch task sources')
      }
      const data = await response.json()
      setSources(data.sources || [])
    } catch (err) {
      setError(err.message)
    }
  }

  const refreshData = async () => {
    await Promise.all([fetchTasks(), fetchSources()])
  }

  const fetchTags = async () => {
    try {
      const response = await apiFetch(`${API_BASE}/tags`)
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
    fetchSources()
    fetchTags()
  }, [])

  // Refetch when the active view changes or when the set of integration
  // sources changes (a new integration's tasks must leave the main list).
  // Keyed on the serialized values so a routine refresh that changes
  // nothing does not trigger an extra fetch.
  const sourcesKey = JSON.stringify(sources)
  const integrationsKey = JSON.stringify(integrations)
  useEffect(() => {
    fetchTasks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, sourcesKey, integrationsKey])

  // If the active tab's integration disappears (hidden or all its tasks
  // removed), fall back to the main list
  useEffect(() => {
    if (activeTab !== 'main' && !visibleIntegrations.some(i => i.source === activeTab)) {
      setActiveTab('main')
    }
  }, [activeTab, visibleIntegrations])

  const createTask = async (taskData, source = 'gui') => {
    try {
      const response = await apiFetch(`${API_BASE}/tasks`, {
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
      await refreshData()
      return newTask
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const updateTask = async (taskId, updateData) => {
    try {
      const response = await apiFetch(`${API_BASE}/tasks/${taskId}`, {
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
      await refreshData()
      return await response.json()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const deleteTask = async (taskId) => {
    try {
      const response = await apiFetch(`${API_BASE}/tasks/${taskId}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to delete task')
      }
      await refreshData()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const completeTask = async (taskId) => {
    try {
      const response = await apiFetch(`${API_BASE}/tasks/${taskId}/complete`, {
        method: 'POST'
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to complete task')
      }
      await refreshData()
      return await response.json()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  if (needsAuth) {
    return <Login onSuccess={handleLoginSuccess} />
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1 onClick={() => navigate('/')}>taskd</h1>
          {appVersion && <span className="version-badge">v{appVersion}</span>}
        </div>
        <div className="header-actions">
          <Settings settings={settings} onChange={handleSettingsChange} sources={sources} />
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            <span className="theme-toggle-icon">
              {theme === 'light' ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <circle cx="12" cy="12" r="5" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </span>
          </button>
        </div>
        {error && <div className="error-banner">{error}</div>}
      </header>

      {visibleIntegrations.length > 0 && (
        <nav className="view-tabs" aria-label="Task views">
          <button
            className={`view-tab ${activeTab === 'main' ? 'active' : ''}`}
            onClick={() => setActiveTab('main')}
          >
            Tasks
          </button>
          {visibleIntegrations.map(integration => (
            <button
              key={integration.source}
              className={`view-tab ${activeTab === integration.source ? 'active' : ''}`}
              onClick={() => setActiveTab(integration.source)}
            >
              {integration.label || integration.source}
            </button>
          ))}
        </nav>
      )}

      <main className="app-main">
        <Routes>
          <Route
            path="/"
            element={
              <TaskList
                tasks={tasks}
                tags={tags}
                loading={loading}
                readOnly={activeTab !== 'main'}
                onCreateTask={createTask}
                onUpdateTask={updateTask}
                onDeleteTask={deleteTask}
                onCompleteTask={completeTask}
                onRefresh={refreshData}
                onViewTask={(task) => navigate(`/tasks/${task.id}`)}
                refreshInterval={settings.refreshInterval}
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
