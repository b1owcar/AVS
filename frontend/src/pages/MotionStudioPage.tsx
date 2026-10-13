import { useEffect, useState } from 'react'
import { StatusBadge } from '../components/StatusBadge'

export function MotionStudioPage() {
  const [schema, setSchema] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    fetch('/api/task-schemas')
      .then((r) => r.json())
      .then(setSchema)
      .catch(() => setSchema(null))
  }, [])

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Motion Studio</h1>
          <p className="page-desc">
            Stage 1 framework: pose extract and motion-transfer parameter models. Real DWPose /
            transfer models are not wired yet — pose ≠ full motion transfer.
          </p>
        </div>
        <StatusBadge status="entry_only" />
      </div>
      <section className="panel">
        <h2>Planned workflow</h2>
        <ol className="muted">
          <li>Import reference action video</li>
          <li>Detect / select person</li>
          <li>Extract pose sequence → JSON</li>
          <li>Import target (image / video / mesh — not interchangeable)</li>
          <li>Run transfer model (Stage 2)</li>
        </ol>
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
