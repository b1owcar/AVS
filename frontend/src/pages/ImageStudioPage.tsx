import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'

export function ImageStudioPage() {
  const [prompt, setPrompt] = useState('moody workstation desk, soft blue rim light')
  const [width, setWidth] = useState(512)
  const [height, setHeight] = useState(512)
  const [modelId, setModelId] = useState('mock-demo')
  const [busy, setBusy] = useState(false)
  const [task, setTask] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setTask(null)
    try {
      const created = await api.createTask({
        task_type: 'text_to_image',
        model_id: modelId,
        parameters: { prompt, width, height },
      })
      let current = created
      for (let i = 0; i < 40; i += 1) {
        setTask(current)
        if (['completed', 'failed', 'cancelled'].includes(String(current.status))) break
        await new Promise((r) => setTimeout(r, 250))
        current = await api.getTask(String(current.task_id))
      }
      setTask(current)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Image Studio</h1>
          <p className="page-desc">
            Text-to-image entry. Mock adapter produces a clearly labeled simulation image. SDXL
            remains unavailable until target-PC verification.
          </p>
        </div>
        <div className="badge-row">
          <span className="badge sim">Demo / Simulation Mode</span>
        </div>
      </div>

      <div className="callout">
        Running <strong>mock-demo</strong> is SIMULATED. It is not real diffusion inference and must
        not be reported as GPU PASS.
      </div>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h2>Generate</h2>
        <form className="form" onSubmit={onSubmit}>
          <label>
            Model
            <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
              <option value="mock-demo">mock-demo (simulation)</option>
              <option value="sdxl-base-1.0">sdxl-base-1.0 (unavailable)</option>
            </select>
          </label>
          <label>
            Prompt
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} required />
          </label>
          <div className="grid-2">
            <label>
              Width
              <input
                type="number"
                min={64}
                max={2048}
                value={width}
                onChange={(e) => setWidth(Number(e.target.value))}
              />
            </label>
            <label>
              Height
              <input
                type="number"
                min={64}
                max={2048}
                value={height}
                onChange={(e) => setHeight(Number(e.target.value))}
              />
            </label>
          </div>
          <div className="btn-row">
            <button className="btn" type="submit" disabled={busy}>
              {busy ? 'Running…' : 'Create task'}
            </button>
          </div>
        </form>
        {error && <p className="error-text">{error}</p>}
      </section>

      {task && (
        <section className="panel">
          <h2>Latest task</h2>
          <div className="grid-3">
            <div className="stat">
              <div className="label">ID</div>
              <div className="value mono">{String(task.task_id)}</div>
            </div>
            <div className="stat">
              <div className="label">Status</div>
              <div className="value">
                <StatusBadge status={String(task.status)} />
              </div>
            </div>
            <div className="stat">
              <div className="label">Simulation</div>
              <div className="value">{String(task.is_simulation)}</div>
            </div>
            <div className="stat">
              <div className="label">Progress</div>
              <div className="value">{Math.round(Number(task.progress || 0) * 100)}%</div>
            </div>
            <div className="stat">
              <div className="label">Outputs</div>
              <div className="value mono">
                {Array.isArray(task.output_files)
                  ? (task.output_files as string[]).join(', ') || '—'
                  : '—'}
              </div>
            </div>
            <div className="stat">
              <div className="label">Error</div>
              <div className="value">{String(task.error_message ?? '—')}</div>
            </div>
          </div>
          {task.logs ? (
            <pre className="mono muted" style={{ whiteSpace: 'pre-wrap', marginTop: '0.85rem' }}>
              {String(task.logs)}
            </pre>
          ) : null}
        </section>
      )}
    </>
  )
}
