import { useState, useEffect } from 'react'
import { apiGet } from '../api'

interface ModelSidePanelProps {
  model: {
    id: string
    platform: string
    model_id: string
    display_name: string
    enabled: boolean
    intelligence_rank: number
    speed_rank: number
    size_label: string
    context_window: number | null
    supports_vision: boolean
    supports_image_gen: boolean
    supports_audio_stt: boolean
    supports_audio_tts: boolean
    supports_embeddings: boolean
    has_key: boolean
  } | null
  onClose: () => void
}

export function ModelSidePanel({ model, onClose }: ModelSidePanelProps) {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!model) return
    setLoading(true)
    apiGet('/api/analytics/by-model?range=24h')
      .then((data: any[]) => {
        const match = (Array.isArray(data) ? data : []).find(
          (m: any) => m.platform === model.platform && m.modelId === model.model_id
        )
        setStats(match ?? null)
      })
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [model])

  useEffect(() => {
    if (!model) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [model, onClose])

  const formatContext = (val: number | null) => {
    if (val === null) return 'N/A'
    return `${(val / 1000).toFixed(0)}K`
  }

  return (
    <>
      {model && (
        <div
          className="fixed inset-0 bg-black/30 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      <div
        className={`fixed top-0 right-0 h-full w-120 bg-white dark:bg-gray-800 shadow-2xl z-50 transform transition-transform duration-300 ${
          model ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {model && (
          <div className="h-full flex flex-col">
            <div className="flex items-start justify-between px-6 py-5 border-b border-gray-200 dark:border-gray-700/50">
              <div className="min-w-0">
                <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 truncate">{model.display_name}</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{model.platform}</p>
              </div>
              <button onClick={onClose} className="p-1.5 -mr-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg cursor-pointer transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
              <section>
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Details</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400 dark:text-gray-500">Context Window</div>
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{formatContext(model.context_window)}</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400 dark:text-gray-500">Intelligence Rank</div>
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{model.intelligence_rank}</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400 dark:text-gray-500">Speed Rank</div>
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{model.speed_rank}</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                    <div className="text-xs text-gray-400 dark:text-gray-500">Size</div>
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{model.size_label}</div>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    model.enabled
                      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                  }`}>
                    {model.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                  {!model.has_key && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                      No Key
                    </span>
                  )}
                </div>
              </section>

              <section>
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Capabilities</h3>
                <div className="flex flex-wrap gap-2">
                  {model.supports_vision && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400">Vision</span>
                  )}
                  {model.supports_image_gen && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400">Image Gen</span>
                  )}
                  {model.supports_audio_stt && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">Audio STT</span>
                  )}
                  {model.supports_audio_tts && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">Audio TTS</span>
                  )}
                  {model.supports_embeddings && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400">Embed</span>
                  )}
                  {!model.supports_vision && !model.supports_image_gen && !model.supports_audio_stt && !model.supports_audio_tts && !model.supports_embeddings && (
                    <span className="text-xs text-gray-400 dark:text-gray-500 italic">No special capabilities</span>
                  )}
                </div>
              </section>

              <section>
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Usage (24h)</h3>
                {loading ? (
                  <div className="flex items-center justify-center py-8 text-gray-400">
                    <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </div>
                ) : stats ? (
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                      <div className="text-xs text-gray-400 dark:text-gray-500">Requests</div>
                      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{stats.requests?.toLocaleString() ?? 0}</div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                      <div className="text-xs text-gray-400 dark:text-gray-500">Success Rate</div>
                      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{stats.successRate != null ? `${stats.successRate}%` : '—'}</div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                      <div className="text-xs text-gray-400 dark:text-gray-500">Avg Latency</div>
                      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{stats.avgLatencyMs != null ? `${stats.avgLatencyMs}ms` : '—'}</div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                      <div className="text-xs text-gray-400 dark:text-gray-500">Input Tokens</div>
                      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{stats.totalInputTokens?.toLocaleString() ?? 0}</div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                      <div className="text-xs text-gray-400 dark:text-gray-500">Output Tokens</div>
                      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{stats.totalOutputTokens?.toLocaleString() ?? 0}</div>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-gray-400">
                    <svg className="w-8 h-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                    </svg>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">No usage data yet</p>
                  </div>
                )}
              </section>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
