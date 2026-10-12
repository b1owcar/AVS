import { useEffect, useState } from 'react'
import type { ChangeEvent } from 'react'
import { api } from '../api'

export function AssetLibraryPage() {
  const [assets, setAssets] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    const data = await api.assets()
    setAssets(data.assets)
  }

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  async function onUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    try {
      await api.uploadAsset(file)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      e.target.value = ''
    }
  }

  async function onDelete(id: string) {
    try {
      await api.deleteAsset(id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Asset Library</h1>
          <p className="page-desc">
            Local file metadata in SQLite; binaries stay on disk. Path traversal is blocked.
          </p>
        </div>
        <label className="btn secondary" style={{ cursor: 'pointer' }}>
          Upload
          <input type="file" hidden onChange={onUpload} />
        </label>
      </div>
      {error && <p className="error-text">{error}</p>}
      <section className="panel">
        {assets.length === 0 ? (
          <div className="empty">No assets yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Type</th>
                <th>Size</th>
                <th>Flags</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <tr key={String(a.asset_id)}>
                  <td>
                    <div className="mono">{String(a.asset_id).slice(0, 8)}…</div>
                    <div className="muted mono">{String(a.file_path)}</div>
                  </td>
                  <td>{String(a.file_type)}</td>
                  <td>{String(a.file_size)} B</td>
                  <td className="muted">
                    {a.is_original_input ? 'input' : ''}
                    {a.is_generated ? ' generated' : ''}
                  </td>
                  <td>
                    <button className="btn danger" type="button" onClick={() => onDelete(String(a.asset_id))}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}
