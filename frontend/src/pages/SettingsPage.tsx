import { useEffect, useState } from 'react'
import { api } from '../api'

export function SettingsPage() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .systemInfo()
      .then(setInfo)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  const app = (info?.app as Record<string, unknown> | undefined) ?? {}

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-desc">
            Effective configuration (read-only in Phase 1). Paths come from environment variables —
            never hardcode this machine&apos;s absolute paths into source.
          </p>
        </div>
      </div>
      {error && <p className="error-text">{error}</p>}
      {app.remote_bind_warning ? <div className="callout">{String(app.remote_bind_warning)}</div> : null}
      <section className="panel">
        <div className="grid-3">
          <div className="stat">
            <div className="label">Bind</div>
            <div className="value">
              {String(app.host)}:{String(app.port)}
            </div>
          </div>
          <div className="stat">
            <div className="label">Run mode</div>
            <div className="value">{String(info?.run_mode)}</div>
          </div>
          <div className="stat">
            <div className="label">ComfyUI URL</div>
            <div className="value mono">{String(app.comfyui_url)}</div>
          </div>
          <div className="stat">
            <div className="label">Max concurrent GPU tasks</div>
            <div className="value">{String(app.max_concurrent_gpu_tasks)}</div>
          </div>
          <div className="stat">
            <div className="label">GPU memory reserve</div>
            <div className="value">{String(app.gpu_memory_reserve_mb)} MB</div>
          </div>
          <div className="stat">
            <div className="label">App version</div>
            <div className="value">{String(app.version)}</div>
          </div>
        </div>
      </section>
    </>
  )
}
