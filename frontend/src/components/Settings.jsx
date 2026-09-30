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

function Settings({ settings, onChange }) {
  const [open, setOpen] = useState(false)

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

          <Webhooks />
        </div>
      )}
    </div>
  )
}

export default Settings
