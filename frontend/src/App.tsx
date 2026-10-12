import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { api, type FeatureEntry } from './api'
import { DashboardPage } from './pages/DashboardPage'
import { ImageStudioPage } from './pages/ImageStudioPage'
import { PlaceholderStudioPage } from './pages/PlaceholderStudioPage'
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
  const [features, setFeatures] = useState<FeatureEntry[]>([])
  const [backendOk, setBackendOk] = useState<boolean | null>(null)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [health, feat] = await Promise.all([api.health(), api.features()])
        if (!alive) return
        setRunMode(health.run_mode)
        setFeatures(feat.features)
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

  const featureMap = Object.fromEntries(features.map((f) => [f.id, f]))

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
          <Route
            path="/video"
            element={
              <PlaceholderStudioPage
                title="Video Studio"
                feature={featureMap.video_studio}
                detail="Text-to-video / image-to-video entries are reserved. Wan 2.1 T2V 1.3B via ComfyUI is the first candidate after FFmpeg preprocess lands on the target PC."
              />
            }
          />
          <Route
            path="/motion"
            element={
              <PlaceholderStudioPage
                title="Motion Studio"
                feature={featureMap.motion_studio}
                detail="Phase plan: frame extract → person select → pose extract → JSON motion → transfer model. Pose ≠ full motion transfer."
              />
            }
          />
          <Route
            path="/3d"
            element={
              <PlaceholderStudioPage
                title="3D Studio"
                feature={featureMap.studio_3d}
                detail="TRELLIS stays in an isolated experimental environment. Official docs require Linux testing and ≥16GB VRAM — target laptop VRAM is unverified."
              />
            }
          />
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
