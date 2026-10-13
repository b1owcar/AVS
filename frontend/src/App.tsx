import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { api } from './api'
import { DashboardPage } from './pages/DashboardPage'
import { ImageStudioPage } from './pages/ImageStudioPage'
import { VideoStudioPage } from './pages/VideoStudioPage'
import { MotionStudioPage } from './pages/MotionStudioPage'
import { Studio3DPage } from './pages/Studio3DPage'
import { ModelManagerPage } from './pages/ModelManagerPage'
import { TaskQueuePage } from './pages/TaskQueuePage'
import { AssetLibraryPage } from './pages/AssetLibraryPage'
import { SettingsPage } from './pages/SettingsPage'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/image', label: 'Image Studio' },
  { to: '/video', label: 'Video Studio' },
  { to: '/motion', label: 'Motion Studio' },
  { to: '/3d', label: '3D Studio' },
  { to: '/models', label: 'Model Manager' },
  { to: '/tasks', label: 'Task Queue' },
  { to: '/assets', label: 'Asset Library' },
  { to: '/settings', label: 'Settings' },
]

export default function App() {
  const [runMode, setRunMode] = useState<string>('unknown')
  const [backendOk, setBackendOk] = useState<boolean | null>(null)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const health = await api.health()
        if (!alive) return
        setRunMode(health.run_mode)
        setBackendOk(true)
      } catch {
        if (!alive) return
        setBackendOk(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="app-shell">
      <aside className="nav">
        <div className="brand">
          <div className="brand-mark">Local AI Vision Studio</div>
          <div className="brand-sub">Local workstation · hybrid inference</div>
        </div>
        <nav className="nav-list">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="badge-row" style={{ padding: '0 0.35rem' }}>
          <span className={`badge ${runMode === 'simulation' ? 'sim' : 'ok'}`}>
            {runMode === 'simulation' ? 'Demo / Simulation Mode' : runMode}
          </span>
          <span className={`badge ${backendOk ? 'ok' : backendOk === false ? 'danger' : 'warn'}`}>
            API {backendOk ? 'online' : backendOk === false ? 'offline' : '…'}
          </span>
        </div>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/image" element={<ImageStudioPage />} />
          <Route path="/video" element={<VideoStudioPage />} />
          <Route path="/motion" element={<MotionStudioPage />} />
          <Route path="/3d" element={<Studio3DPage />} />
          <Route path="/models" element={<ModelManagerPage />} />
          <Route path="/tasks" element={<TaskQueuePage />} />
          <Route path="/assets" element={<AssetLibraryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
