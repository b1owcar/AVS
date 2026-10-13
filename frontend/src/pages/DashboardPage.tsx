import { useEffect, useState } from 'react'
import { api, type FeatureEntry, type FeatureSummary } from '../api'
import { StatusBadge } from '../components/StatusBadge'

export function DashboardPage() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null)
  const [features, setFeatures] = useState<FeatureEntry[]>([])
  const [summary, setSummary] = useState<FeatureSummary | null>(null)
  const [comfy, setComfy] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [sys, feat, c] = await Promise.all([
          api.systemInfo(),
          api.features(),
          api.comfyStatus(),
        ])
        if (!alive) return
        setInfo(sys)
        setFeatures(feat.features)
        setSummary(feat.summary ?? null)
        setComfy(c)
      } catch (e) {
        if (!alive) return
        setError(e instanceof Error ? e.message : String(e))
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  const gpu = (info?.gpu as Record<string, unknown> | undefined) ?? {}
  const runMode = summary?.run_mode ?? String(info?.run_mode ?? 'unknown')
  const comfyLabel =
    summary?.comfyui ?? (comfy?.reachable ? 'reachable' : comfy ? 'offline' : '…')

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-desc">Live readiness for this PC — adapters, ComfyUI, and workers.</p>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <section className="panel readiness-bar">
        <div className="readiness-stats">
          <div className="stat">
            <div className="label">Mode</div>
            <div className="value">{runMode}</div>
          </div>
          <div className="stat">
            <div className="label">Ready</div>
            <div className="value ok-text">{summary?.ready_count ?? '—'}</div>
          </div>
          <div className="stat">
            <div className="label">Blocked</div>
            <div className={`value ${summary && summary.blocked_count > 0 ? 'warn-text' : ''}`}>
              {summary?.blocked_count ?? '—'}
            </div>
          </div>
          <div className="stat">
            <div className="label">ComfyUI</div>
            <div className={`value ${comfyLabel === 'reachable' ? 'ok-text' : 'warn-text'}`}>
              {comfyLabel}
            </div>
          </div>
          <div className="stat">
            <div className="label">SDXL native</div>
            <div
              className={`value ${summary?.sdxl_native === 'ready' ? 'ok-text' : 'muted'}`}
            >
              {summary?.sdxl_native ?? '—'}
            </div>
          </div>
          <div className="stat">
            <div className="label">FFmpeg</div>
            <div className={`value ${summary?.ffmpeg === 'available' ? 'ok-text' : 'warn-text'}`}>
              {summary?.ffmpeg ?? '—'}
            </div>
          </div>
        </div>
        {summary?.next_steps && summary.next_steps.length > 0 ? (
          <div className="next-steps">
            <div className="label">Next steps</div>
            <ol>
              {summary.next_steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        ) : (
          <p className="muted" style={{ margin: '0.75rem 0 0' }}>
            Core paths look ready. Open a studio to run a task.
          </p>
        )}
      </section>

      <div className="grid-2" style={{ marginTop: '1rem' }}>
        <section className="panel">
          <h2>System probe</h2>
          {!info ? (
            <div className="empty">Loading…</div>
          ) : (
            <div className="grid-3">
              <div className="stat">
                <div className="label">OS</div>
                <div className="value">
                  {String(info.os_name)} {String(info.architecture)}
                </div>
              </div>
              <div className="stat">
                <div className="label">Python</div>
                <div className="value">{String(info.python_version)}</div>
              </div>
              <div className="stat">
                <div className="label">RAM available</div>
                <div className="value">
                  {String(info.ram_available_mb)} / {String(info.ram_total_mb)} MB
                </div>
              </div>
              <div className="stat">
                <div className="label">Disk free</div>
                <div className="value">{String(info.disk_free_gb)} GB</div>
              </div>
              <div className="stat">
                <div className="label">FFmpeg</div>
                <div className="value">{info.ffmpeg_available ? 'available' : 'missing'}</div>
              </div>
              <div className="stat">
                <div className="label">Degraded</div>
                <div className="value">{info.degraded ? 'yes' : 'no'}</div>
              </div>
            </div>
          )}
          {Array.isArray(info?.messages) && (info.messages as string[]).length > 0 && (
            <ul className="muted" style={{ marginTop: '0.85rem' }}>
              {(info.messages as string[]).map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <h2>GPU / ComfyUI</h2>
          <div className="grid-3">
            <div className="stat">
              <div className="label">GPU available</div>
              <div className="value">{String(gpu.available)}</div>
            </div>
            <div className="stat">
              <div className="label">GPU name</div>
              <div className="value">{String(gpu.name ?? 'n/a')}</div>
            </div>
            <div className="stat">
              <div className="label">VRAM free / total</div>
              <div className="value">
                {gpu.memory_free_mb != null
                  ? `${gpu.memory_free_mb} / ${gpu.memory_total_mb} MB`
                  : 'unmeasured'}
              </div>
            </div>
            <div className="stat">
              <div className="label">Probe source</div>
              <div className="value">{String(gpu.source ?? 'none')}</div>
            </div>
            <div className="stat">
              <div className="label">ComfyUI</div>
              <div className="value">{comfy?.reachable ? 'reachable' : 'offline'}</div>
            </div>
            <div className="stat">
              <div className="label">Compat tag</div>
              <div className="value">{String(gpu.compatibility ?? 'unverified')}</div>
            </div>
          </div>
          <p className="muted" style={{ marginTop: '0.85rem' }}>
            {String(comfy?.message ?? summary?.comfyui_message ?? '')}
          </p>
        </section>
      </div>

      <section className="panel">
        <h2>Feature readiness</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          <StatusBadge status="available" /> wired and ready ·{' '}
          <StatusBadge status="available_conditional" /> ready, weights checked at run ·{' '}
          <StatusBadge status="available_simulation" /> demo mock ·{' '}
          <StatusBadge status="unavailable" /> blocked on this PC
        </p>
        <table className="table">
          <thead>
            <tr>
              <th>Feature</th>
              <th>Status</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {features.length === 0 ? (
              <tr>
                <td colSpan={3} className="muted">
                  Loading…
                </td>
              </tr>
            ) : (
              features.map((f) => (
                <tr key={f.id}>
                  <td>{f.label}</td>
                  <td>
                    <StatusBadge status={f.status} />
                  </td>
                  <td className="muted">{f.notes}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </>
  )
}
