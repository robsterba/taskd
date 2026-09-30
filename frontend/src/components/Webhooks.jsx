import { useState } from 'react'
import './Webhooks.css'

const EVENT_TYPES = [
  { value: 'task.created', label: 'Task created' },
  { value: 'task.updated', label: 'Task updated' },
  { value: 'task.completed', label: 'Task completed' },
  { value: 'task.deleted', label: 'Task deleted' }
]

const API_BASE = '/api/v1'

function Webhooks() {
  const [webhooks, setWebhooks] = useState(null)
  const [url, setUrl] = useState('')
  const [secret, setSecret] = useState('')
  const [events, setEvents] = useState(['task.created'])
  const [error, setError] = useState(null)
  const [testResults, setTestResults] = useState({})
  const [expanded, setExpanded] = useState(null)
  const [deliveries, setDeliveries] = useState({})

  const loadWebhooks = async () => {
    try {
      const res = await fetch(`${API_BASE}/webhooks`)
      if (!res.ok) throw new Error('Failed to load webhooks')
      const data = await res.json()
      setWebhooks(data.webhooks || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }

  // The component only mounts when the settings panel opens,
  // so this refreshes the list on every open
  useEffect(() => {
    loadWebhooks()
  }, [])

  const addWebhook = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      const body = { url, events }
      if (secret.trim()) body.secret = secret.trim()
      const res = await fetch(`${API_BASE}/webhooks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error(detail.detail || 'Failed to add webhook')
      }
      setUrl('')
      setSecret('')
      setEvents(['task.created'])
      await loadWebhooks()
    } catch (err) {
      setError(err.message)
    }
  }

  const toggleEvent = (value) => {
    setEvents(prev =>
      prev.includes(value) ? prev.filter(e => e !== value) : [...prev, value]
    )
  }

  const toggleActive = async (webhook) => {
    await fetch(`${API_BASE}/webhooks/${webhook.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: !webhook.active })
    })
    loadWebhooks()
  }

  const removeWebhook = async (webhook) => {
    await fetch(`${API_BASE}/webhooks/${webhook.id}`, { method: 'DELETE' })
    loadWebhooks()
  }

  const sendTest = async (webhook) => {
    try {
      const res = await fetch(`${API_BASE}/webhooks/${webhook.id}/test`, { method: 'POST' })
      const data = await res.json()
      setTestResults(prev => ({
        ...prev,
        [webhook.id]: data.status === 'success'
          ? `OK (${data.response_code})`
          : `Failed${data.response_code ? ` (${data.response_code})` : ''}`
      }))
    } catch {
      setTestResults(prev => ({ ...prev, [webhook.id]: 'Failed (connection)' }))
    }
  }

  const loadDeliveries = async (webhook) => {
    if (expanded === webhook.id) {
      setExpanded(null)
      return
    }
    const res = await fetch(`${API_BASE}/webhooks/${webhook.id}/deliveries`)
    const data = await res.json()
    setDeliveries(prev => ({ ...prev, [webhook.id]: data.deliveries || [] }))
    setExpanded(webhook.id)
  }

  return (
    <div className="webhooks">
      <div className="settings-group webhooks-list">
        <label>Webhooks</label>
        {error && <p className="webhooks-error">{error}</p>}
        {webhooks === null && <p className="settings-hint">Loading…</p>}
        {webhooks !== null && webhooks.length === 0 && (
          <p className="settings-hint">
            No webhooks registered. Task events will be POSTed to any URL you add.
          </p>
        )}
        {webhooks !== null && webhooks.map(wh => (
          <div key={wh.id} className={`webhook-item${wh.active ? '' : ' inactive'}`}>
            <div className="webhook-url" title={wh.url}>{wh.url}</div>
            <div className="webhook-events">
              {wh.events.map(ev => (
                <span key={ev} className="webhook-event-chip">{ev}</span>
              ))}
            </div>
            <div className="webhook-actions">
              <button type="button" className="webhook-small-btn" onClick={() => toggleActive(wh)}>
                {wh.active ? 'Disable' : 'Enable'}
              </button>
              <button type="button" className="webhook-small-btn" onClick={() => sendTest(wh)}>
                Test
              </button>
              <button type="button" className="webhook-small-btn danger" onClick={() => removeWebhook(wh)}>
                Delete
              </button>
              <button type="button" className="webhook-small-btn" onClick={() => loadDeliveries(wh)}>
                {expanded === wh.id ? 'Hide log' : 'Log'}
              </button>
            </div>
            {testResults[wh.id] && (
              <div className={`webhook-test-result ${testResults[wh.id].startsWith('OK') ? 'ok' : 'fail'}`}>
                {testResults[wh.id]}
              </div>
            )}
            {expanded === wh.id && (
              <div className="webhook-deliveries">
                {(deliveries[wh.id] || []).length === 0 && (
                  <p className="settings-hint">No deliveries yet.</p>
                )}
                {(deliveries[wh.id] || []).map(d => (
                  <div key={d.id} className="webhook-delivery-row">
                    <span className={d.status === 'success' ? 'ok' : 'fail'}>{d.status}</span>
                    <span className="webhook-delivery-event">{d.event_type}</span>
                    <span className="webhook-delivery-time">
                      {new Date(d.created_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
            <div className="webhook-secret" title={`Secret: ${wh.secret}`}>
              secret: {wh.secret.slice(0, 8)}…
            </div>
          </div>
        ))}
      </div>

      <form className="settings-group webhook-add" onSubmit={addWebhook}>
        <label htmlFor="webhook-url">Add webhook</label>
        <input
          id="webhook-url"
          type="url"
          placeholder="https://n8n.example.com/webhook/…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder="Secret (leave blank to auto-generate)"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
        />
        <div className="webhook-event-picker">
          {EVENT_TYPES.map(ev => (
            <label key={ev.value} className="webhook-event-option">
              <input
                type="checkbox"
                checked={events.includes(ev.value)}
                onChange={() => toggleEvent(ev.value)}
              />
              {ev.label}
            </label>
          ))}
        </div>
        <button type="submit" disabled={!url || events.length === 0}>Add</button>
      </form>
      <p className="settings-hint">
        Events are POSTed with an HMAC-SHA256 signature in the
        <code> X-taskd-Signature </code>
        header, computed with the webhook secret.
      </p>
    </div>
  )
}

export default Webhooks
