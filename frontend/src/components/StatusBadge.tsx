export function StatusBadge({
  status,
  label,
}: {
  status: string
  label?: string
}) {
  return <span className={`status-pill ${status}`}>{label ?? status}</span>
}
