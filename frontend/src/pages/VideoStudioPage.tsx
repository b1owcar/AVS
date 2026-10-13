import { useEffect, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'

export function VideoStudioPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [assets, setAssets] = useState<Array<Record<string, unknown>>>([])
  const [assetId, setAssetId] = useState('')
  const [mode, setMode] = useState('info')
  const [interval, setIntervalSec] = useState(1)
  const [start, setStart] = useState(0)
  const [duration, setDuration] = useState(2)
  const [maxFrames, setMaxFrames] = useState(30)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [genKind, setGenKind] = useState<'text_to_video' | 'image_to_video'>('text_to_video')
  const [t2vPrompt, setT2vPrompt] = useState('cinematic drone shot over foggy hills')
  const [negPrompt, setNegPrompt] = useState('色调艳丽，过曝，静态，细节模糊，字幕，画面静止')
  const [refImageId, setRefImageId] = useState('')
  const [numFrames, setNumFrames] = useState(33)
  const [width, setWidth] = useState(832)
  const [height, setHeight] = useState(480)
  const [genTask, setGenTask] = useState<Record<string, unknown> | null>(null)
  const [genMsg, setGenMsg] = useState<string | null>(null)
  const [genBusy, setGenBusy] = useState(false)

  async function refresh() {
    const [st, as] = await Promise.all([
      fetch('/api/video/status').then((r) => r.json()),
      api.assets(),
    ])
    setStatus(st)
    setAssets(as.assets)
    if (!assetId && as.assets[0]) setAssetId(String(as.assets[0].asset_id))
    const images = as.assets.filter((a) =>
      ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(String(a.file_type).toLowerCase()),
    )
    if (!refImageId && images[0]) setRefImageId(String(images[0].asset_id))
  }

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  async function onUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const up = await api.uploadAsset(file)
      setAssetId(String(up.asset_id))
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      e.target.value = ''
    }
  }

  async function onPreprocess(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const body: Record<string, unknown> = {
        asset_id: assetId,
        mode,
        interval_seconds: interval,
        start_seconds: start,
        max_frames: maxFrames,
      }
      if (mode === 'clip') body.duration_seconds = duration
      const resp = await fetch('/api/video/preprocess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || JSON.stringify(data))
      setResult(data)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onGenerate(e: FormEvent) {
    e.preventDefault()
    setGenBusy(true)
    setGenMsg(null)
    setGenTask(null)
    setError(null)
    try {
      const body: Record<string, unknown> = {
        task_kind: genKind,
        prompt: t2vPrompt,
        negative_prompt: negPrompt,
        model_id: genKind === 'image_to_video' ? 'wan2.1-i2v' : 'wan2.1-t2v-1.3b',
        width,
        height,
        num_frames: genKind === 'image_to_video' ? Math.min(numFrames, 17) : numFrames,
        fps: 16,
      }
      if (genKind === 'image_to_video') {
        body.reference_image_asset_id = refImageId
        if (!refImageId) throw new Error('I2V requires a reference image asset')
      }
      const resp = await fetch('/api/video/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || JSON.stringify(data))
      let current = data
      for (let i = 0; i < 900; i += 1) {
        setGenTask(current)
        if (['completed', 'failed', 'cancelled'].includes(String(current.status))) break
        await new Promise((r) => setTimeout(r, 1000))
        current = await api.getTask(String(current.task_id))
      }
      setGenTask(current)
      if (String(current.status) === 'failed') {
        setGenMsg(String(current.error_message || 'generation failed'))
      } else if (String(current.status) === 'completed') {
        setGenMsg('Generation completed — see Task Queue / Asset Library for outputs.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setGenBusy(false)
    }
  }

  const features = (status?.features as Record<string, boolean> | undefined) ?? {}
  const imageAssets = assets.filter((a) =>
    ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(String(a.file_type).toLowerCase()),
  )

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Video Studio</h1>
          <p className="page-desc">
            FFmpeg preprocess plus Wan T2V 1.3B / I2V 480P via ComfyUI. I2V uses a separate schema
            and heavier weights — keep length short on 12GB GPUs.
          </p>
        </div>
        <div className="badge-row">
          <StatusBadge
            status={status?.ffmpeg_available ? 'available' : 'unavailable'}
            label={status?.ffmpeg_available ? 'ffmpeg ok' : 'ffmpeg missing'}
          />
          <StatusBadge
            status={features.text_to_video ? 'available' : 'unavailable'}
            label={features.text_to_video ? 'T2V comfy' : 'T2V offline'}
          />
          <StatusBadge
            status={features.image_to_video ? 'available' : 'unavailable'}
            label={features.image_to_video ? 'I2V comfy' : 'I2V offline'}
          />
        </div>
      </div>

      <section className="panel">
        <h2>Preprocess</h2>
        <form className="form" onSubmit={onPreprocess}>
          <label>
            Source asset
            <select value={assetId} onChange={(e) => setAssetId(e.target.value)} required>
              <option value="">Select uploaded video/image asset…</option>
              {assets.map((a) => (
                <option key={String(a.asset_id)} value={String(a.asset_id)}>
                  {String(a.asset_id).slice(0, 8)}… ({String(a.file_type)}) {String(a.file_path)}
                </option>
              ))}
            </select>
          </label>
          <div className="btn-row">
            <label className="btn secondary" style={{ cursor: 'pointer' }}>
              Upload media
              <input type="file" hidden accept="video/*,image/*" onChange={onUpload} />
            </label>
          </div>
          <label>
            Mode
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="info" disabled={features.info === false}>
                info
              </option>
              <option value="preview">preview</option>
              <option value="interval">interval frames</option>
              <option value="keyframes">keyframes</option>
              <option value="clip">clip</option>
              <option value="transcode">transcode</option>
            </select>
          </label>
          <div className="grid-3">
            <label>
              Interval (s)
              <input
                type="number"
                step="0.1"
                min={0.1}
                value={interval}
                onChange={(e) => setIntervalSec(Number(e.target.value))}
              />
            </label>
            <label>
              Start (s)
              <input
                type="number"
                step="0.1"
                min={0}
                value={start}
                onChange={(e) => setStart(Number(e.target.value))}
              />
            </label>
            <label>
              Duration (s, clip)
              <input
                type="number"
                step="0.1"
                min={0.1}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              />
            </label>
          </div>
          <label>
            Max frames
            <input
              type="number"
              min={1}
              max={500}
              value={maxFrames}
              onChange={(e) => setMaxFrames(Number(e.target.value))}
            />
          </label>
          <button className="btn" type="submit" disabled={busy || !assetId}>
            {busy ? 'Running…' : 'Run preprocess'}
          </button>
        </form>
        {error && <p className="error-text">{error}</p>}
        {result && (
          <pre className="mono muted" style={{ whiteSpace: 'pre-wrap', marginTop: '0.85rem' }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </section>

      <section className="panel">
        <h2>Wan generation (T2V / I2V)</h2>
        <div className="callout info">
          Requires ComfyUI running (<code>start_comfyui.ps1</code>) with Wan weights. T2V uses
          1.3B; I2V is official 14B@480P — separate model id and short defaults.
        </div>
        <form className="form" style={{ marginTop: '0.85rem' }} onSubmit={onGenerate}>
          <label>
            Kind
            <select
              value={genKind}
              onChange={(e) => {
                const v = e.target.value as 'text_to_video' | 'image_to_video'
                setGenKind(v)
                if (v === 'image_to_video') {
                  setNumFrames(17)
                  setWidth(832)
                  setHeight(480)
                } else {
                  setNumFrames(33)
                }
              }}
            >
              <option value="text_to_video">text_to_video (Wan 1.3B)</option>
              <option value="image_to_video">image_to_video (Wan I2V 480P)</option>
            </select>
          </label>
          <label>
            Prompt
            <textarea value={t2vPrompt} onChange={(e) => setT2vPrompt(e.target.value)} />
          </label>
          <label>
            Negative prompt
            <textarea value={negPrompt} onChange={(e) => setNegPrompt(e.target.value)} />
          </label>
          {genKind === 'image_to_video' && (
            <label>
              Reference image asset
              <select value={refImageId} onChange={(e) => setRefImageId(e.target.value)} required>
                <option value="">Select image…</option>
                {imageAssets.map((a) => (
                  <option key={String(a.asset_id)} value={String(a.asset_id)}>
                    {String(a.asset_id).slice(0, 8)}… {String(a.file_path)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="grid-3">
            <label>
              Frames
              <input
                type="number"
                min={1}
                max={121}
                value={numFrames}
                onChange={(e) => setNumFrames(Number(e.target.value))}
              />
            </label>
            <label>
              Width
              <input
                type="number"
                min={64}
                max={1280}
                value={width}
                onChange={(e) => setWidth(Number(e.target.value))}
              />
            </label>
            <label>
              Height
              <input
                type="number"
                min={64}
                max={1280}
                value={height}
                onChange={(e) => setHeight(Number(e.target.value))}
              />
            </label>
          </div>
          <button className="btn" type="submit" disabled={genBusy}>
            {genBusy ? 'Generating…' : 'Enqueue generation'}
          </button>
        </form>
        {genMsg && <p className="muted">{genMsg}</p>}
        {genTask && (
          <pre className="mono muted" style={{ whiteSpace: 'pre-wrap', marginTop: '0.85rem' }}>
            {JSON.stringify(genTask, null, 2)}
          </pre>
        )}
      </section>
    </>
  )
}
