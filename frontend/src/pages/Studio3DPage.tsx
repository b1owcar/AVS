import { useEffect, useState } from 'react'
import { StatusBadge } from '../components/StatusBadge'

export function Studio3DPage() {
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
          <h1 className="page-title">3D Studio</h1>
          <p className="page-desc">
            Image-to-3D and video-to-3D are separate pipelines. TRELLIS stays in an isolated worker
            env; video keyframe approximation must not claim full geometry recovery.
          </p>
        </div>
        <StatusBadge status="entry_only" />
      </div>
      <section className="panel">
        <div className="callout info">
          Specialized worker interface is in place (`SpecializedModelWorker`). Install TRELLIS only
          into `env-trellis` on the office machine — never into the main backend venv.
        </div>
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
