import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'

export function Studio3DPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [assets, setAssets] = useState<Array<Record<string, unknown>>>([])
  const [schema, setSchema] = useState<Record<string, unknown> | null>(null)
  const [imageId, setImageId] = useState('')
  const [videoId, setVideoId] = useState('')
  const [busy, setBusy] = useState(false)
  const [task, setTask] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    const [st, as, schemas] = await Promise.all([
      fetch('/api/studio3d/status').then((r) => r.json()),
      api.assets(),
      fetch('/api/task-schemas').then((r) => r.json()),
    ])
    setStatus(st)
    setAssets(as.assets)
    setSchema(schemas)
    const images = as.assets.filter((a) =>
      ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(String(a.file_type).toLowerCase()),
    )
    const videos = as.assets.filter((a) =>
      ['mp4', 'mov', 'webm', 'mkv', 'avi'].includes(String(a.file_type).toLowerCase()),
    )
    if (!imageId && images[0]) setImageId(String(images[0].asset_id))
    if (!videoId && videos[0]) setVideoId(String(videos[0].asset_id))
  }

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  async function pollTask(created: Record<string, unknown>, max = 120) {
    let current = created
    for (let i = 0; i < max; i += 1) {
      setTask(current)
      if (['completed', 'failed', 'cancelled'].includes(String(current.status))) break
      await new Promise((r) => setTimeout(r, 500))
      current = await api.getTask(String(current.task_id))
    }
    return current
  }

  async function onImageTo3D(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setTask(null)
    try {
      const resp = await fetch('/api/studio3d/image-to-3d', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_asset_id: imageId,
          model_id: 'trellis-image-to-3d',
          output_formats: ['glb'],
        }),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || JSON.stringify(data))
      const current = await pollTask(data, 60)
      setTask(current)
      if (String(current.status) === 'failed') {
        setError(String(current.error_message || 'image-to-3d failed'))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onVideoTo3D(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setTask(null)
    try {
      const resp = await fetch('/api/studio3d/video-to-3d', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_asset_id: videoId,
          mode: 'keyframe_approx',
        }),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || JSON.stringify(data))
      const current = await pollTask(data, 180)
      setTask(current)
      if (String(current.status) === 'failed') {
        setError(String(current.error_message || 'video-to-3d failed'))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const i3d = status?.image_to_3d as Record<string, unknown> | undefined
  const v3d = status?.video_to_3d as Record<string, unknown> | undefined
  const images = assets.filter((a) =>
    ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(String(a.file_type).toLowerCase()),
  )
  const videos = assets.filter((a) =>
    ['mp4', 'mov', 'webm', 'mkv', 'avi'].includes(String(a.file_type).toLowerCase()),
  )

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">3D Studio</h1>
          <p className="page-desc">
            Phase 6: TRELLIS image-to-3D in env-trellis (Linux / ≥16GB VRAM stated upstream). Video
            path is keyframe approximation only — not full geometry recovery.
          </p>
        </div>
        <div className="badge-row">
          <StatusBadge
            status={i3d?.ready ? 'available' : 'unavailable'}
            label={i3d?.ready ? 'trellis ready' : 'trellis not installed'}
          />
          <StatusBadge
            status={v3d?.ready ? 'available' : 'unavailable'}
            label={v3d?.ready ? 'keyframe approx' : 'ffmpeg missing'}
          />
        </div>
      </div>

      <section className="panel">
        <div className="callout info">
          Prefer <code>scripts/linux/install-trellis.sh</code>. Windows scaffold is experimental and
          unverified. Never install TRELLIS into the main backend venv.
        </div>
      </section>

      <section className="panel">
        <h2>Image → 3D (TRELLIS)</h2>
        <form className="form" onSubmit={onImageTo3D}>
          <label>
            Image asset
            <select value={imageId} onChange={(e) => setImageId(e.target.value)} required>
              <option value="">Select…</option>
              {images.map((a) => (
                <option key={String(a.asset_id)} value={String(a.asset_id)}>
                  {String(a.asset_id).slice(0, 8)}… {String(a.file_path)}
                </option>
              ))}
            </select>
          </label>
          <button className="btn" type="submit" disabled={busy || !imageId}>
            {busy ? 'Running…' : 'Enqueue image-to-3d'}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Video → 3D (keyframe approx)</h2>
        <div className="callout">
          Produces a keyframe pack + manifest. Does <strong>not</strong> claim full mesh recovery.
          <code>multiview_rebuild</code> is rejected.
        </div>
        <form className="form" onSubmit={onVideoTo3D}>
          <label>
            Video asset
            <select value={videoId} onChange={(e) => setVideoId(e.target.value)} required>
              <option value="">Select…</option>
              {videos.map((a) => (
                <option key={String(a.asset_id)} value={String(a.asset_id)}>
                  {String(a.asset_id).slice(0, 8)}… {String(a.file_path)}
                </option>
              ))}
            </select>
          </label>
          <button className="btn" type="submit" disabled={busy || !videoId}>
            {busy ? 'Running…' : 'Enqueue keyframe approx'}
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
                  image_to_3d: schema.image_to_3d,
                  video_to_3d: schema.video_to_3d,
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
