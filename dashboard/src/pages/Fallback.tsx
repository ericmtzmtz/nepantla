import { useState, useEffect } from 'react'
import { apiGet } from '../api'

interface FallbackEntry {
  id: string
  model_db_id: string
  platform: string
  model_id: string
  display_name: string
  pool: string
  priority: number
  enabled: boolean
}

const POOL_META: Record<string, { label: string; accent: string; icon: string }> = {
  chat:      { label: 'Chat',      accent: 'border-t-blue-500',      icon: 'M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z' },
  vision:    { label: 'Vision',    accent: 'border-t-violet-500',    icon: 'M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z' },
  image_gen: { label: 'Image Gen', accent: 'border-t-rose-500',     icon: 'M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z' },
  audio:     { label: 'Audio',     accent: 'border-t-amber-500',     icon: 'M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z' },
  embed:     { label: 'Embed',     accent: 'border-t-teal-500',      icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
}

const POOL_ORDER = ['chat', 'vision', 'image_gen', 'audio', 'embed']

function PoolIcon({ path }: { path: string }) {
  return <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d={path} /></svg>
}

export function Fallback() {
  const [entries, setEntries] = useState<FallbackEntry[]>([])

  const load = async () => {
    try { setEntries(await apiGet('/api/fallback')) } catch { }
  }
  useEffect(() => { load() }, [])

  const saveOrder = async () => {
    try {
      const grouped: Record<string, FallbackEntry[]> = {}
      for (const e of entries) {
        if (!grouped[e.pool]) grouped[e.pool] = []
        grouped[e.pool].push(e)
      }
      const updates = Object.values(grouped).flatMap(group =>
        group
          .sort((a, b) => a.priority - b.priority)
          .map((e, i) => ({ id: e.id, priority: i + 1, enabled: e.enabled }))
      )
      await Promise.all(updates.map(u =>
        fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/api/fallback/${u.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ priority: u.priority, enabled: u.enabled }),
        })
      ))
    } catch { }
  }

  const toggle = (id: string) => {
    setEntries(prev => prev.map(e => e.id === id ? { ...e, enabled: !e.enabled } : e))
  }

  const move = (id: string, dir: -1 | 1) => {
    setEntries(prev => {
      const copy = [...prev]
      const idx = copy.findIndex(e => e.id === id)
      if (idx === -1) return prev
      const pool = copy[idx].pool
      const poolIndices = copy
        .map((e, i) => ({ e, i }))
        .filter(({ e }) => e.pool === pool)
        .map(({ i }) => i)
      const posInPool = poolIndices.indexOf(idx)
      const targetPoolPos = posInPool + dir
      if (targetPoolPos < 0 || targetPoolPos >= poolIndices.length) return prev
      const targetIdx = poolIndices[targetPoolPos]
      ;[copy[idx], copy[targetIdx]] = [copy[targetIdx], copy[idx]]
      return copy
    })
  }

  const copyId = (id: string) => navigator.clipboard.writeText(id)

  const grouped = entries.reduce<Record<string, FallbackEntry[]>>((acc, e) => {
    if (!acc[e.pool]) acc[e.pool] = []
    acc[e.pool].push(e)
    return acc
  }, {})

  const sortedPools = Object.keys(grouped).sort(
    (a, b) => POOL_ORDER.indexOf(a) - POOL_ORDER.indexOf(b)
  )

  const hasEntries = entries.length > 0

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Fallback Chain</h1>
        <button onClick={saveOrder} disabled={!hasEntries}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium rounded-lg cursor-pointer transition-colors">Save Order</button>
      </div>

      {!hasEntries ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50">
          <svg className="w-16 h-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
          </svg>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No fallback entries</p>
          <p className="text-xs text-gray-400 mt-1">Entries will appear here when configured</p>
        </div>
      ) : (
        <div className="space-y-6">
          {sortedPools.map(pool => {
            const poolEntries = grouped[pool].sort((a, b) => a.priority - b.priority)
            const meta = POOL_META[pool] || { label: pool, accent: 'border-t-gray-500', icon: '' }
            return (
              <div key={pool} className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 ${meta.accent} overflow-hidden`}>
                <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-100 dark:border-gray-700/50 bg-gray-50 dark:bg-gray-800/80">
                  <PoolIcon path={meta.icon} />
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">{meta.label}</h3>
                  <span className="text-xs text-gray-400 ml-1">({poolEntries.length})</span>
                </div>
                {poolEntries.map((e, i) => (
                  <div key={e.id} className="flex items-center gap-3 px-5 py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                    <span className="text-sm font-bold text-gray-400 w-7 text-center">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {e.display_name || `${e.platform}/${e.model_id}`}
                      </span>
                      <span className="text-xs text-gray-400 ml-2 font-mono">{e.model_db_id.slice(0, 8)}</span>
                    </div>
                    <button onClick={() => copyId(e.model_db_id)} className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded cursor-pointer" title="Copy model ID">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                      </svg>
                    </button>
                    <button onClick={() => move(e.id, -1)} disabled={i === 0} className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-gray-600 dark:text-gray-400">▲</button>
                    <button onClick={() => move(e.id, 1)} disabled={i === poolEntries.length - 1} className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-gray-600 dark:text-gray-400">▼</button>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" checked={e.enabled} onChange={() => toggle(e.id)} className="sr-only peer" />
                      <div className="w-9 h-5 bg-gray-300 dark:bg-gray-600 peer-checked:bg-blue-600 rounded-full peer-checked:after:translate-x-4 after:content-[''] after:absolute after:top-0.75 after:left-0.75 after:bg-white after:rounded-full after:h-3.5 after:w-3.5 after:transition-all" />
                    </label>
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
