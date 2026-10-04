import { useState } from 'react'
import { apiFetch, storeApiKey, clearStoredApiKey } from '../utils/api'
import './Login.css'

export default function Login({ onSuccess }) {
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState(null)
  const [checking, setChecking] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!apiKey.trim()) return

    setChecking(true)
    setError(null)
    storeApiKey(apiKey.trim())
    try {
      const res = await apiFetch('/api/v1/tasks?limit=1')
      if (res.ok) {
        onSuccess()
      } else {
        clearStoredApiKey()
        setError('Invalid API key')
      }
    } catch {
      clearStoredApiKey()
      setError('Could not reach taskd')
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="login-overlay">
      <form className="login-card card" onSubmit={handleSubmit}>
        <h2>taskd</h2>
        <p className="login-hint">This server requires an API key.</p>
        <input
          className="login-input"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="API key"
          autoFocus
          aria-label="API key"
        />
        {error && <div className="login-error">{error}</div>}
        <button className="btn login-submit" type="submit" disabled={checking || !apiKey.trim()}>
          {checking ? 'Checking…' : 'Unlock'}
        </button>
      </form>
    </div>
  )
}
