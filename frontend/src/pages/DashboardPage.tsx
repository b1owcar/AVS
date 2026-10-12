import { useEffect, useState } from 'react'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'

export function DashboardPage() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null)
  const [features, setFeatures] = useState<Array<Record<string, string>>>([])
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
        setFeatures(feat.features as unknown as Array<Record<string, string>>)
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

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-desc">
            Hardware probe and feature gates for this development session. Values here describe the
            current machine — not the target RTX 5070 Ti laptop until deployment-day checks run.
          </p>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="callout">
        Remote Development Mode is active. Mock inference may run; real CUDA model downloads and
        GPU inference wait for the target PC.
      </div>

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
            {String(comfy?.message ?? '')}
          </p>
        </section>
      </div>

      <section className="panel">
        <h2>Feature gates</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Feature</th>
              <th>Status</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {features.map((f) => (
              <tr key={f.id}>
                <td>{f.label}</td>
                <td>
                  <StatusBadge status={f.status} />
                </td>
                <td className="muted">{f.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  )
}
