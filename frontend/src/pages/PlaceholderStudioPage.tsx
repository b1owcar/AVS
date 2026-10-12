import type { FeatureEntry } from '../api'
import { StatusBadge } from '../components/StatusBadge'

export function PlaceholderStudioPage({
  title,
  feature,
  detail,
}: {
  title: string
  feature?: FeatureEntry
  detail: string
}) {
  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">{title}</h1>
          <p className="page-desc">{detail}</p>
        </div>
        <div className="badge-row">
          {feature ? <StatusBadge status={feature.status} label={feature.status} /> : null}
        </div>
      </div>
      <section className="panel">
        <h2>Status</h2>
        <div className="callout info">
          Entry is visible by design. This feature is <strong>not marked available</strong> until a
          real adapter is implemented and verified on the target machine.
        </div>
        <p className="muted" style={{ marginTop: '1rem' }}>
          {feature?.notes ?? 'No feature metadata loaded.'}
        </p>
      </section>
    </>
  )
}
