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

  const [poseJsonId, setPoseJsonId] = useState('')
  const [targetImageId, setTargetImageId] = useState('')
  const [transferBusy, setTransferBusy] = useState(false)
  const [transferTask, setTransferTask] = useState<Record<string, unknown> | null>(null)

  async function refresh() {
    const [st, as, schemas] = await Promise.all([
      fetch('/api/motion/status').then((r) => r.json()),
      api.assets(),
      fetch('/api/task-schemas').then((r) => r.json()),
    ])
    setStatus(st)
    setAssets(as.assets)
    setSchema(schemas)
    const jsons = as.assets.filter((a) => String(a.file_type).toLowerCase() === 'json')
    const images = as.assets.filter((a) =>
      ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(String(a.file_type).toLowerCase()),
    )
    if (!poseJsonId && jsons[0]) setPoseJsonId(String(jsons[0].asset_id))
    if (!targetImageId && images[0]) setTargetImageId(String(images[0].asset_id))
  }

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  const frameAssets = assets.filter((a) =>
    ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(String(a.file_type).toLowerCase()),
  )
  const jsonAssets = assets.filter((a) => String(a.file_type).toLowerCase() === 'json')
  const imageAssets = frameAssets

  function toggleFrame(id: string) {
    setSelectedFrames((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  async function pollTask(created: Record<string, unknown>, max = 120) {
    let current = created
    for (let i = 0; i < max; i += 1) {
      if (['completed', 'failed', 'cancelled'].includes(String(current.status))) break
      await new Promise((r) => setTimeout(r, 500))
      current = await api.getTask(String(current.task_id))
    }
    return current
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
      const current = await pollTask(data)
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

  async function onTransfer(e: FormEvent) {
    e.preventDefault()
    setTransferBusy(true)
    setError(null)
    setTransferTask(null)
    try {
      const resp = await fetch('/api/motion/transfer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reference_video_asset_id: poseJsonId,
          target_type: 'person_image',
          target_asset_id: targetImageId,
          model_id: 'motion-transfer',
        }),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || JSON.stringify(data))
      const current = await pollTask(data, 60)
      setTransferTask(current)
      if (String(current.status) === 'failed') {
        setError(String(current.error_message || 'transfer failed'))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setTransferBusy(false)
    }
  }

  async function onComposePreview() {
    setTransferBusy(true)
    setError(null)
    setTransferTask(null)
    try {
      const resp = await fetch('/api/motion/compose-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pose_json_asset_id: poseJsonId,
          target_image_asset_id: targetImageId,
        }),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || JSON.stringify(data))
      const current = await pollTask(data, 40)
      setTransferTask(current)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setTransferBusy(false)
    }
  }

  const poseReady = Boolean(
    (status?.pose_extract as Record<string, unknown> | undefined)?.ready,
  )
  const transferReady = Boolean(
    (status?.motion_transfer as Record<string, unknown> | undefined)?.ready,
  )

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Motion Studio</h1>
          <p className="page-desc">
            Phase 5: pose extract (stage 1) then motion transfer (stage 2). Compose preview overlays
            a skeleton and is explicitly not transfer.
          </p>
        </div>
        <div className="badge-row">
          <StatusBadge
            status={poseReady ? 'available' : 'unavailable'}
            label={poseReady ? 'pose ready' : 'pose not installed'}
          />
          <StatusBadge
            status={transferReady ? 'available' : 'unavailable'}
            label={transferReady ? 'transfer ready' : 'transfer not ready'}
          />
        </div>
      </div>

      <section className="panel">
        <h2>Pose extract (stage 1)</h2>
        {!poseReady && (
          <div className="callout">
            Install: <code>scripts/windows/install-pose.ps1</code> or{' '}
            <code>scripts/linux/install-pose.sh</code>
          </div>
        )}
        <form className="form" onSubmit={onExtract}>
          <fieldset>
            <legend>Frame assets</legend>
            {frameAssets.length === 0 ? (
              <p className="muted">No image frames yet. Preprocess a video first.</p>
            ) : (
              <div className="muted" style={{ maxHeight: 180, overflow: 'auto' }}>
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
            Person id (optional)
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
        {task && (
          <pre className="mono muted" style={{ whiteSpace: 'pre-wrap', marginTop: '0.85rem' }}>
            {JSON.stringify(task, null, 2)}
          </pre>
        )}
      </section>

      <section className="panel">
        <h2>Motion transfer (stage 2)</h2>
        <div className="callout info">
          Needs pose JSON asset + target person image. Real transfer requires{' '}
          <code>install-motion.ps1</code> and weights. Compose preview is labeled and is not
          transfer.
        </div>
        <form className="form" onSubmit={onTransfer}>
          <label>
            Pose JSON asset
            <select value={poseJsonId} onChange={(e) => setPoseJsonId(e.target.value)} required>
              <option value="">Select pose JSON…</option>
              {jsonAssets.map((a) => (
                <option key={String(a.asset_id)} value={String(a.asset_id)}>
                  {String(a.asset_id).slice(0, 8)}… {String(a.file_path)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Target person image
            <select
              value={targetImageId}
              onChange={(e) => setTargetImageId(e.target.value)}
              required
            >
              <option value="">Select image…</option>
              {imageAssets.map((a) => (
                <option key={String(a.asset_id)} value={String(a.asset_id)}>
                  {String(a.asset_id).slice(0, 8)}… {String(a.file_path)}
                </option>
              ))}
            </select>
          </label>
          <div className="btn-row">
            <button className="btn" type="submit" disabled={transferBusy || !poseJsonId}>
              {transferBusy ? 'Running…' : 'Enqueue motion transfer'}
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={transferBusy || !poseJsonId || !targetImageId}
              onClick={onComposePreview}
            >
              Skeleton compose preview
            </button>
          </div>
        </form>
        {error && <p className="error-text">{error}</p>}
        {transferTask && (
          <pre className="mono muted" style={{ whiteSpace: 'pre-wrap', marginTop: '0.85rem' }}>
            {JSON.stringify(transferTask, null, 2)}
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
