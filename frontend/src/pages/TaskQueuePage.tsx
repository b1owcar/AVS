import { useEffect, useState } from 'react'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'

export function TaskQueuePage() {
  const [tasks, setTasks] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    const data = await api.tasks()
    setTasks(data.tasks)
  }

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)))
    const id = window.setInterval(() => {
      refresh().catch(() => undefined)
    }, 2000)
    return () => window.clearInterval(id)
  }, [])

  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Task Queue</h1>
          <p className="page-desc">Persisted SQLite-backed queue. Simulation tasks are labeled.</p>
        </div>
        <button className="btn secondary" type="button" onClick={() => refresh()}>
          Refresh
        </button>
      </div>
      {error && <p className="error-text">{error}</p>}
      <section className="panel">
        {tasks.length === 0 ? (
          <div className="empty">No tasks yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Model</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Sim</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={String(t.task_id)}>
                  <td className="mono">{String(t.task_id).slice(0, 8)}…</td>
                  <td>{String(t.model_id)}</td>
                  <td>
                    <StatusBadge status={String(t.status)} />
                  </td>
                  <td>{Math.round(Number(t.progress || 0) * 100)}%</td>
                  <td>{String(t.is_simulation)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}
