import { useState, useEffect, useMemo } from 'react'
import { apiGet, apiPost } from '../api'

interface ModelEntry {
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
  free_tier: boolean
}

const PLATFORM_META: Record<string, { accent: string }> = {
  openai:   { accent: 'border-t-emerald-500' },
  anthropic:{ accent: 'border-t-violet-500' },
  google:   { accent: 'border-t-blue-500' },
  deepseek: { accent: 'border-t-amber-500' },
  groq:     { accent: 'border-t-rose-500' },
}

const CAPABILITIES = [
  { key: 'supports_vision' as const, label: 'Vision', color: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300' },
  { key: 'supports_image_gen' as const, label: 'Image Gen', color: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300' },
  { key: 'supports_audio_stt' as const, label: 'Audio STT', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
  { key: 'supports_audio_tts' as const, label: 'TTS', color: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300' },
  { key: 'supports_embeddings' as const, label: 'Embed', color: 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300' },
]

function CubeIcon() {
  return (
    <svg className="w-16 h-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
    </svg>
  )
}

export function Models({ onSelectModel }: { onSelectModel: (model: ModelEntry | null) => void }) {
  const [models, setModels] = useState<ModelEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [providerFilter, setProviderFilter] = useState('')
  const [activeCaps, setActiveCaps] = useState<Set<string>>(new Set())
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<{ summary: { inserted: number; disabled: number; updated: number }; total: number } | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)
  const [freeTierOnly, setFreeTierOnly] = useState(false)

  const doSync = async () => {
    setSyncing(true)
    setSyncError(null)
    setSyncResult(null)
    try {
      const res = await apiPost('/api/provisioning/sync')
      setSyncResult(res)
      const data = await apiGet('/api/models')
      setModels(data as ModelEntry[])
      setError(null)
    } catch {
      setSyncError('Sync failed')
    }
    setSyncing(false)
  }

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await apiGet('/api/models')
        if (!cancelled) setModels(data as ModelEntry[])
      } catch {
        if (!cancelled) setError('Failed to load models')
      }
      if (!cancelled) setLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [])

  const platforms = useMemo(() => [...new Set(models.map(m => m.platform))], [models])

  const filtered = useMemo(() => {
    return models.filter(m => {
      if (search) {
        const q = search.toLowerCase()
        const name = (m.display_name || `${m.platform}/${m.model_id}`).toLowerCase()
        if (!name.includes(q) && !m.model_id.toLowerCase().includes(q)) return false
      }
      if (providerFilter && m.platform !== providerFilter) return false
      if (freeTierOnly && !m.free_tier) return false
      if (activeCaps.size > 0) {
        for (const cap of activeCaps) {
          if (!(m as any)[cap]) return false
        }
      }
      return true
    })
  }, [models, search, providerFilter, activeCaps, freeTierOnly])

  const grouped = useMemo(() => filtered.reduce<Record<string, ModelEntry[]>>((acc, m) => {
    if (!acc[m.platform]) acc[m.platform] = []
    acc[m.platform].push(m)
    return acc
  }, {}), [filtered])

  const sortedPlatforms = useMemo(() => Object.keys(grouped).sort(), [grouped])

  const toggleCap = (key: string) => {
    setActiveCaps(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const formatContext = (val: number | null): string | null => {
    if (val === null || val === 0) return null
    return `${Math.round(val / 1000)}K`
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Model Catalog</h1>
        <div className="flex items-center justify-center py-16 text-gray-400">
          <svg className="w-6 h-6 mr-3 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Model Catalog</h1>
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50">
          <CubeIcon />
          <p className="text-sm font-medium text-red-500">{error}</p>
          <button onClick={() => window.location.reload()} className="mt-3 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer">Reload</button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Model Catalog</h1>
        <button onClick={doSync} disabled={syncing}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white transition-colors cursor-pointer">
          {syncing && (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
          </svg>
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-50">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search models..."
            className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 shadow-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none" />
        </div>
        <select value={providerFilter} onChange={e => setProviderFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 shadow-sm">
          <option value="">All Providers</option>
          {platforms.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      {/* Capability pills + Free tier filter */}
      <div className="flex flex-wrap gap-2">
        {CAPABILITIES.map(cap => {
          const active = activeCaps.has(cap.key)
          return (
            <button key={cap.key} onClick={() => toggleCap(cap.key)}
              className={`px-3 py-1 text-xs font-medium rounded-full border transition-colors cursor-pointer ${
                active
                  ? `${cap.color} border-transparent`
                  : 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600 hover:border-gray-400'
              }`}>
              {cap.label}
            </button>
          )
        })}
        <button onClick={() => setFreeTierOnly(!freeTierOnly)}
          className={`px-3 py-1 text-xs font-medium rounded-full border transition-colors cursor-pointer ${
            freeTierOnly
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 border-transparent'
              : 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600 hover:border-gray-400'
          }`}>
          Free only
        </button>
      </div>

      {syncResult && (
        <div className="flex items-center gap-3 px-4 py-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50 rounded-lg text-sm text-emerald-700 dark:text-emerald-300">
          <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Sync complete: {syncResult.summary.inserted} new, {syncResult.summary.disabled} disabled, {syncResult.summary.updated} updated</span>
          <button onClick={() => setSyncResult(null)} className="ml-auto text-emerald-500 hover:text-emerald-700 cursor-pointer">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
      {syncError && (
        <div className="px-4 py-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800/50 rounded-lg text-sm text-red-600 dark:text-red-400">
          {syncError}
        </div>
      )}

      {/* Content */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50">
          <CubeIcon />
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No models match your search</p>
          <p className="text-xs text-gray-400 mt-1">Try adjusting your filters</p>
        </div>
      ) : (
        <div className="space-y-6">
          {sortedPlatforms.map(platform => {
            const entries = grouped[platform]
            const meta = PLATFORM_META[platform] || { accent: 'border-t-gray-500' }
            const hasAnyKey = entries.some(m => m.has_key)
            return (
              <div key={platform} className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 ${meta.accent} overflow-hidden`}>
                {/* Header */}
                <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-100 dark:border-gray-700/50 bg-gray-50 dark:bg-gray-800/80">
                  <span className={`w-2 h-2 rounded-full ${hasAnyKey ? 'bg-green-500' : 'bg-amber-400'}`} />
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">{platform}</h3>
                  <span className="text-xs text-gray-400 ml-1">({entries.length})</span>
                </div>
                {/* Rows */}
                {entries.map(m => (
                  <div key={m.id} onClick={() => onSelectModel(m)}
                    className={`flex items-center gap-3 px-5 py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer ${!m.enabled ? 'opacity-50' : ''}`}>
                    <div className="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {m.display_name || `${m.platform}/${m.model_id}`}
                      </span>
                      {!m.has_key && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 leading-none">no key</span>
                      )}
                      {m.free_tier && (
                        <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded leading-none ${
                          m.has_key
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                            : 'bg-emerald-50 text-emerald-500 dark:bg-emerald-950/30 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/50'
                        }`}>
                          {m.has_key ? 'Free' : 'Free \u2014 needs key'}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {m.intelligence_rank > 0 && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 leading-none">Rank #{m.intelligence_rank}</span>
                      )}
                      {formatContext(m.context_window) && (
                        <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">{formatContext(m.context_window)}</span>
                      )}
                      {m.supports_vision && <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300 leading-none">Vision</span>}
                      {m.supports_image_gen && <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300 leading-none">Image Gen</span>}
                      {m.supports_audio_stt && <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 leading-none">Audio STT</span>}
                      {m.supports_audio_tts && <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300 leading-none">TTS</span>}
                      {m.supports_embeddings && <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 leading-none">Embed</span>}
                      <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
