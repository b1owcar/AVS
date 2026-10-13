import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'

export function MotionStudioPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [assets, setAssets] = useState<Array<Record<string, unknown>>>([])
  const [selectedFrames, setSelectedFrames] = useState<string[]>([])
  const [personId, setPersonId] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [task, setTask] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [schema, setSchema] = useState<Record<string, unknown> | null>(null)

  async function refresh() {
    const [st, as, schemas] = await Promise.all([
      fetch('/api/motion/status').then((r) => r.json()),
      api.assets(),
      fetch('/api/task-schemas').then((r) => r.json()),
    ])
    setStatus(st)
    setAssets(as.assets)
    setSchema(schemas)
  }

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  const frameAssets = assets.filter((a) =>
    ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(String(a.file_type).toLowerCase()),
  )

  function toggleFrame(id: string) {
    setSelectedFrames((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  async function onExtract(e: FormEvent) {
    e.preventDefault()
    if (selectedFrames.length === 0) {
      setError('Select at least one frame asset (from Video Studio preprocess).')
      return
    }
    setBusy(true)
    setError(null)
    setTask(null)
    try {
      const body: Record<string, unknown> = {
        frame_asset_ids: selectedFrames,
        export_skeleton_preview: true,
        coordinate_system: 'image_pixel',
        model_id: 'pose-mediapipe',
      }
      if (personId !== '') body.person_id = Number(personId)
      const resp = await fetch('/api/motion/pose/extract-frames', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || JSON.stringify(data))
      let current = data
      for (let i = 0; i < 120; i += 1) {
        setTask(current)
        if (['completed', 'failed', 'cancelled'].includes(String(current.status))) break
        await new Promise((r) => setTimeout(r, 500))
        current = await api.getTask(String(current.task_id))
      }
      setTask(current)
      if (String(current.status) === 'failed') {
        setError(String(current.error_message || 'pose extract failed'))
      }
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const poseReady = Boolean(
    (status?.pose_extract as Record<string, unknown> | undefined)?.ready,
  )

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Motion Studio</h1>
          <p className="page-desc">
            Phase 5 stage-1: select frames → optional person id → pose JSON + skeleton preview.
            Pose extract is not full motion transfer.
          </p>
        </div>
        <div className="badge-row">
          <StatusBadge
            status={poseReady ? 'available' : 'unavailable'}
            label={poseReady ? 'pose ready' : 'pose not installed'}
          />
          <StatusBadge status="entry_only" label="transfer stage-2" />
        </div>
      </div>

      <section className="panel">
        <h2>Workflow</h2>
        <ol className="muted">
          <li>Import reference video in Video Studio and run interval / keyframes preprocess</li>
          <li>Select frame assets below (person selection: MediaPipe Pose is single-person)</li>
          <li>Extract pose sequence → JSON + skeleton overlays</li>
          <li>Stage 2 motion transfer remains unavailable</li>
        </ol>
      </section>

      <section className="panel">
        <h2>Pose extract (stage 1)</h2>
        {!poseReady && (
          <div className="callout">
            Install on D:\avs: <code>scripts\windows\install-pose.ps1</code> then restart LAVS.
            Tasks fail clearly until env-pose is ready — no fake success.
          </div>
        )}
        <form className="form" onSubmit={onExtract}>
          <fieldset>
            <legend>Frame assets</legend>
            {frameAssets.length === 0 ? (
              <p className="muted">No image frames yet. Preprocess a video first.</p>
            ) : (
              <div className="muted" style={{ maxHeight: 220, overflow: 'auto' }}>
                {frameAssets.map((a) => {
                  const id = String(a.asset_id)
                  return (
                    <label key={id} style={{ display: 'flex', gap: '0.5rem', marginBottom: 6 }}>
                      <input
                        type="checkbox"
                        checked={selectedFrames.includes(id)}
                        onChange={() => toggleFrame(id)}
                      />
                      <span>
                        {id.slice(0, 8)}… ({String(a.file_type)}) {String(a.file_path)}
                      </span>
                    </label>
                  )
                })}
              </div>
            )}
          </fieldset>
          <label>
            Person id (optional; leave empty for primary / only person)
            <input
              type="number"
              min={0}
              value={personId}
              onChange={(e) => setPersonId(e.target.value)}
              placeholder="0"
            />
          </label>
          <button className="btn" type="submit" disabled={busy || selectedFrames.length === 0}>
            {busy ? 'Extracting…' : 'Run pose extract'}
          </button>
        </form>
        {error && <p className="error-text">{error}</p>}
        {task && (
          <pre className="mono muted" style={{ whiteSpace: 'pre-wrap', marginTop: '0.85rem' }}>
            {JSON.stringify(task, null, 2)}
          </pre>
        )}
      </section>

      <section className="panel">
        <h2>Parameter schemas</h2>
        <pre className="mono muted" style={{ whiteSpace: 'pre-wrap' }}>
          {schema
            ? JSON.stringify(
                {
                  pose_extract: schema.pose_extract,
                  motion_transfer: schema.motion_transfer,
                },
                null,
                2,
              )
            : 'Loading…'}
        </pre>
      </section>
    </>
  )
}
