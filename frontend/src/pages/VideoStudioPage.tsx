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
  const [t2vPrompt, setT2vPrompt] = useState('cinematic drone shot over foggy hills')
  const [genMsg, setGenMsg] = useState<string | null>(null)

  async function refresh() {
    const [st, as] = await Promise.all([
      fetch('/api/video/status').then((r) => r.json()),
      api.assets(),
    ])
    setStatus(st)
    setAssets(as.assets)
    if (!assetId && as.assets[0]) setAssetId(String(as.assets[0].asset_id))
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

  async function validateT2V() {
    setGenMsg(null)
    const resp = await fetch('/api/video/generate/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_kind: 'text_to_video',
        prompt: t2vPrompt,
        model_id: 'wan2.1-t2v-1.3b',
        width: 480,
        height: 480,
        num_frames: 33,
      }),
    })
    const data = await resp.json()
    if (!resp.ok) {
      setGenMsg(String(data.detail || 'validation failed'))
      return
    }
    setGenMsg(String(data.message))
  }

  const features = (status?.features as Record<string, boolean> | undefined) ?? {}

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Video Studio</h1>
          <p className="page-desc">
            FFmpeg preprocess is live (info / frames / clip / transcode). Text-to-video generation
            stays gated until Wan/ComfyUI is installed on D:\avs.
          </p>
        </div>
        <div className="badge-row">
          <StatusBadge
            status={status?.ffmpeg_available ? 'available' : 'unavailable'}
            label={status?.ffmpeg_available ? 'ffmpeg ok' : 'ffmpeg missing'}
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
        <h2>Text-to-video (params only)</h2>
        <div className="callout">
          Generation is <strong>not executed</strong> here. This validates the T2V parameter schema
          separately from I2V.
        </div>
        <form
          className="form"
          style={{ marginTop: '0.85rem' }}
          onSubmit={(e) => {
            e.preventDefault()
            validateT2V()
          }}
        >
          <label>
            Prompt
            <textarea value={t2vPrompt} onChange={(e) => setT2vPrompt(e.target.value)} />
          </label>
          <button className="btn secondary" type="submit">
            Validate T2V params
          </button>
        </form>
        {genMsg && <p className="muted">{genMsg}</p>}
      </section>
    </>
  )
}
