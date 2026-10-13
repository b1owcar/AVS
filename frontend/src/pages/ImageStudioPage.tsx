import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'

type ModelRow = Record<string, unknown>

export function ImageStudioPage() {
  const [prompt, setPrompt] = useState('moody workstation desk, soft blue rim light')
  const [width, setWidth] = useState(768)
  const [height, setHeight] = useState(768)
  const [steps, setSteps] = useState(25)
  const [modelId, setModelId] = useState('mock-demo')
  const [models, setModels] = useState<ModelRow[]>([])
  const [busy, setBusy] = useState(false)
  const [task, setTask] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hint, setHint] = useState<string | null>(null)

  useEffect(() => {
    api
      .models()
      .then((data) => {
        const list = data.models.filter((m) =>
          ['mock-demo', 'sdxl-base-1.0', 'sdxl-comfyui'].includes(String(m.id)),
        )
        setModels(list)
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setTask(null)
    try {
      const created = await api.createTask({
        task_type: 'text_to_image',
        model_id: modelId,
        parameters: {
          prompt,
          width,
          height,
          num_inference_steps: steps,
        },
      })
      let current = created
      // Real SDXL can take minutes — poll longer than mock
      const maxPolls = modelId === 'mock-demo' ? 40 : 600
      for (let i = 0; i < maxPolls; i += 1) {
        setTask(current)
        if (['completed', 'failed', 'cancelled'].includes(String(current.status))) break
        await new Promise((r) => setTimeout(r, modelId === 'mock-demo' ? 250 : 1000))
        current = await api.getTask(String(current.task_id))
      }
      setTask(current)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onDownloadHint() {
    setHint(null)
    const res = await api.requestDownload(modelId)
    setHint(String(res.message))
  }

  const selected = models.find((m) => String(m.id) === modelId)
  const availability = String(selected?.availability ?? 'unknown')

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Image Studio</h1>
          <p className="page-desc">
            Text-to-image. Mock is always safe. SDXL native and ComfyUI paths activate after
            office Phase 2 install scripts under D:\avs.
          </p>
        </div>
        <div className="badge-row">
          {modelId === 'mock-demo' ? (
            <span className="badge sim">Demo / Simulation Mode</span>
          ) : (
            <span className="badge ok">Real adapter path</span>
          )}
          <StatusBadge status={availability} />
        </div>
      </div>

      {modelId === 'mock-demo' ? (
        <div className="callout">
          Running <strong>mock-demo</strong> is SIMULATED. It is not real diffusion inference.
        </div>
      ) : (
        <div className="callout info">
          Real model selected. If the adapter is not ready, the task fails with install hints — it
          will never fake a successful GPU run.
        </div>
      )}

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h2>Generate</h2>
        <form className="form" onSubmit={onSubmit}>
          <label>
            Model
            <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
              {models.length === 0 ? (
                <>
                  <option value="mock-demo">mock-demo (simulation)</option>
                  <option value="sdxl-base-1.0">sdxl-base-1.0 (native)</option>
                  <option value="sdxl-comfyui">sdxl-comfyui</option>
                </>
              ) : (
                models.map((m) => (
                  <option key={String(m.id)} value={String(m.id)}>
                    {String(m.display_name)} ({String(m.availability)})
                  </option>
                ))
              )}
            </select>
          </label>
          <label>
            Prompt
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} required />
          </label>
          <div className="grid-3">
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
            <label>
              Steps
              <input
                type="number"
                min={1}
                max={80}
                value={steps}
                onChange={(e) => setSteps(Number(e.target.value))}
              />
            </label>
          </div>
          <div className="btn-row">
            <button className="btn" type="submit" disabled={busy}>
              {busy ? 'Running…' : 'Create task'}
            </button>
            <button className="btn secondary" type="button" onClick={onDownloadHint}>
              Install / download hint
            </button>
          </div>
        </form>
        {hint && <div className="callout" style={{ marginTop: '0.85rem' }}>{hint}</div>}
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
