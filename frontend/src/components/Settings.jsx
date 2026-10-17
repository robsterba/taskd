import { useState } from 'react'
import Webhooks from './Webhooks'
import './Settings.css'

const REFRESH_INTERVAL_OPTS = [
  { value: 0, label: 'Off' },
  { value: 10, label: 'Every 10 seconds' },
  { value: 30, label: 'Every 30 seconds' },
  { value: 60, label: 'Every 1 minute' },
  { value: 300, label: 'Every 5 minutes' },
  { value: 900, label: 'Every 15 minutes' }
]

const DARK_THEME_OPTS = [
  { value: 'dark', label: 'Blue (default)' },
  { value: 'amoled', label: 'AMOLED Black' }
]

function Settings({ settings, onChange, sources = [] }) {
  const [open, setOpen] = useState(false)
  const [newSource, setNewSource] = useState('')
  const [newLabel, setNewLabel] = useState('')

  const integrations = settings.integrations || []

  const updateIntegrations = (next) => {
    onChange({ ...settings, integrations: next })
  }

  const updateIntegration = (index, patch) => {
    updateIntegrations(integrations.map((i, idx) => idx === index ? { ...i, ...patch } : i))
  }

  const removeIntegration = (index) => {
    updateIntegrations(integrations.filter((_, idx) => idx !== index))
  }

  const addIntegration = () => {
    const source = newSource.trim()
    if (!source) return
    if (integrations.some(i => i.source === source)) return
    updateIntegrations([
      ...integrations,
      { source, label: newLabel.trim() || source, visible: true }
    ])
    setNewSource('')
    setNewLabel('')
  }

  return (
    <div className="settings">
      <button
        className="settings-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-label="Open settings"
      >
        Settings
      </button>

      {open && (
        <div className="settings-panel">
          <div className="settings-header">
            <h2>Settings</h2>
            <button
              className="settings-close"
              onClick={() => setOpen(false)}
              aria-label="Close settings"
            >
              Close
            </button>
          </div>

          <div className="settings-group">
            <label htmlFor="setting-refresh-interval">Refresh interval</label>
            <select
              id="setting-refresh-interval"
              value={settings.refreshInterval}
              onChange={(e) =>
                onChange({ ...settings, refreshInterval: Number(e.target.value) })
              }
            >
              {REFRESH_INTERVAL_OPTS.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <p className="settings-hint">
              How often the task list refreshes automatically. Set to Off to
              disable auto-refresh.
            </p>
          </div>

          <div className="settings-group">
            <label>Dark theme</label>
            <div className="radio-group" role="radiogroup" aria-label="Dark theme">
              {DARK_THEME_OPTS.map(opt => (
                <label key={opt.value} className="settings-radio">
                  <input
                    type="radio"
                    name="dark-theme"
                    value={opt.value}
                    checked={(settings.darkMode || 'dark') === opt.value}
                    onChange={() => onChange({ ...settings, darkMode: opt.value })}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
            <p className="settings-hint">
              Which dark variant the header button switches to. AMOLED Black
              uses a true black background, ideal for OLED screens. Changing
              this while in dark mode applies immediately.
            </p>
          </div>

          <div className="settings-group">
            <label>Integration views</label>
            {integrations.map((integration, index) => (
              <div key={integration.source} className="integration-row">
                <label className="settings-checkbox">
                  <input
                    type="checkbox"
                    checked={integration.visible !== false}
                    onChange={(e) =>
                      updateIntegration(index, { visible: e.target.checked })
                    }
                  />
                  Show as tab
                </label>
                <input
                  type="text"
                  value={integration.label || ''}
                  placeholder="Tab label"
                  onChange={(e) =>
                    updateIntegration(index, { label: e.target.value })
                  }
                />
                <span className="integration-source">
                  {integration.source}
                  {!sources.includes(integration.source) && ' (no tasks yet)'}
                </span>
                <button
                  className="integration-remove"
                  onClick={() => removeIntegration(index)}
                  aria-label={`Remove ${integration.source} integration`}
                >
                  Remove
                </button>
              </div>
            ))}
            <div className="integration-row integration-add">
              <input
                type="text"
                value={newSource}
                placeholder="Source (e.g. my-tool)"
                onChange={(e) => setNewSource(e.target.value)}
              />
              <input
                type="text"
                value={newLabel}
                placeholder="Tab label"
                onChange={(e) => setNewLabel(e.target.value)}
              />
              <button onClick={addIntegration}>Add</button>
            </div>
            <p className="settings-hint">
              Tasks created by an integration appear in their own tab instead
              of the main list. A tab shows up once the integration has
              created at least one task. Uncheck "Show as tab" to move its
              tasks back into the main list.
            </p>
          </div>

          <Webhooks />
        </div>
      )}
    </div>
  )
}

export default Settings
