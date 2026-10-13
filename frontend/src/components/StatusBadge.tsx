const LABELS: Record<string, string> = {
  available: 'Ready',
  available_conditional: 'Ready*',
  available_simulation: 'Demo',
  entry_only: 'Entry only',
  unimplemented: 'Not built',
  unavailable: 'Not ready',
  completed: 'Done',
  failed: 'Failed',
  pending: 'Pending',
  preparing: 'Preparing',
  running: 'Running',
  cancelled: 'Cancelled',
  verified: 'Verified',
  unverified: 'Unverified',
  installed_unverified: 'Installed',
  logic_only: 'Logic only',
  simulated: 'Simulated',
}

export function StatusBadge({
  status,
  label,
}: {
  status: string
  label?: string
}) {
  const text = label ?? LABELS[status] ?? status.split('_').join(' ')
  return <span className={`status-pill ${status}`}>{text}</span>
}
