export type FeatureStatus =
  | 'available'
  | 'available_conditional'
  | 'available_simulation'
  | 'entry_only'
  | 'unimplemented'
  | 'unavailable'

export interface FeatureEntry {
  id: string
  label: string
  status: FeatureStatus
  notes: string
}

export interface FeatureSummary {
  run_mode: string
  ready_count: number
  blocked_count: number
  comfyui: 'reachable' | 'offline'
  comfyui_message?: string
  sdxl_native?: 'ready' | 'not_ready'
  ffmpeg?: 'available' | 'missing'
  next_steps?: string[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, init)
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text || `HTTP ${resp.status}`)
  }
  return resp.json() as Promise<T>
}

export const api = {
  health: () => request<{ ok: boolean; run_mode: string; version: string }>('/api/health'),
  systemInfo: () => request<Record<string, unknown>>('/api/system/info'),
  features: () =>
    request<{ features: FeatureEntry[]; summary?: FeatureSummary }>('/api/features'),
  models: () => request<{ models: Array<Record<string, unknown>> }>('/api/models'),
  tasks: () => request<{ tasks: Array<Record<string, unknown>> }>('/api/tasks'),
  createTask: (body: {
    task_type: string
    model_id: string
    parameters: Record<string, unknown>
    input_files?: string[]
  }) =>
    request<Record<string, unknown>>('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  getTask: (id: string) => request<Record<string, unknown>>(`/api/tasks/${id}`),
  cancelTask: (id: string) =>
    request<Record<string, unknown>>(`/api/tasks/${id}/cancel`, { method: 'POST' }),
  assets: () => request<{ assets: Array<Record<string, unknown>> }>('/api/assets'),
  uploadAsset: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Record<string, unknown>>('/api/assets/upload', {
      method: 'POST',
      body: form,
    })
  },
  deleteAsset: (id: string) =>
    request<{ ok: boolean }>(`/api/assets/${id}`, { method: 'DELETE' }),
  comfyStatus: () => request<Record<string, unknown>>('/api/comfyui/status'),
  requestDownload: (modelId: string) =>
    request<Record<string, unknown>>(`/api/models/${modelId}/download`, { method: 'POST' }),
}
