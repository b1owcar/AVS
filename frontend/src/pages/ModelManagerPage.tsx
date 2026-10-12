import { useEffect, useState } from 'react'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'

export function ModelManagerPage() {
  const [models, setModels] = useState<Array<Record<string, unknown>>>([])
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    const data = await api.models()
    setModels(data.models)
  }

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  async function onDownload(id: string) {
    setMessage(null)
    const res = await api.requestDownload(id)
    setMessage(String(res.message))
  }

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Model Manager</h1>
          <p className="page-desc">
            Registry of candidates with licenses, sizes, and verification state. Downloads are
            user-triggered and blocked in remote-dev mode.
          </p>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}
      {message && <div className="callout">{message}</div>}

      <section className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Availability</th>
              <th>Verification</th>
              <th>Size hint</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {models.map((m) => (
              <tr key={String(m.id)}>
                <td>
                  <div>{String(m.display_name)}</div>
                  <div className="mono muted">{String(m.id)}</div>
                  <div className="muted" style={{ marginTop: '0.35rem' }}>
                    {String(m.notes ?? '')}
                  </div>
                </td>
                <td>
                  <StatusBadge status={String(m.availability)} />
                </td>
                <td>
                  <StatusBadge status={String(m.verification_status)} />
                </td>
                <td className="muted">{String(m.download_size_hint ?? '—')}</td>
                <td>
                  <button className="btn secondary" type="button" onClick={() => onDownload(String(m.id))}>
                    Request download
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  )
}
