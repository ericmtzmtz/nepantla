import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'

interface ApiKeyEntry {
  id: string
  platform: string
  label: string
  maskedKey: string
  status: string
  enabled: boolean
  createdAt: string
  lastCheckedAt: string | null
}

export function Keys() {
  const [keys, setKeys] = useState<ApiKeyEntry[]>([])
  const [unifiedKey, setUnifiedKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [platforms, setPlatforms] = useState<string[]>([])
  const [newPlatform, setNewPlatform] = useState('')
  const [newKey, setNewKey] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [validatingAll, setValidatingAll] = useState(false)
  const [loading, setLoading] = useState(true)

  const loadKeys = async () => {
    try { const data = await apiGet('/api/keys'); setKeys(data) } catch { }
    setLoading(false)
  }
  const loadUnifiedKey = async () => {
    try {
      const data = await apiGet('/api/settings/api-key')
      setUnifiedKey(data.key || '')
    } catch { }
  }

  useEffect(() => {
    loadKeys()
    loadUnifiedKey()
    apiGet('/api/models').then(data => {
      const models = data as Array<{ platform: string }>
      const unique = [...new Set(models.map(m => m.platform))].sort()
      setPlatforms(unique)
      if (unique.length > 0) setNewPlatform(unique[0])
    }).catch(() => {})
  }, [])

  const addKey = async () => {
    if (!newKey) return
    try {
      await apiPost('/api/keys', { platform: newPlatform, key: newKey, label: newLabel })
      setNewKey(''); setNewLabel('')
      await loadKeys()
    } catch { }
  }

  const deleteKey = async (id: string) => {
    try {
      await fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/api/keys/${id}`, { method: 'DELETE' })
      await loadKeys()
    } catch { }
  }

  const toggleKey = async (id: string, enabled: boolean) => {
    try {
      await fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/api/keys/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      await loadKeys()
    } catch { }
  }

  const validateKey = async (keyId: string) => {
    try {
      const res = await apiPost(`/api/keys/${keyId}/validate`)
      setKeys(prev => prev.map(k => k.id === keyId ? { ...k, status: res.status, lastCheckedAt: res.lastCheckedAt } : k))
    } catch { }
  }

  const validateAll = async () => {
    setValidatingAll(true)
    try {
      await apiPost('/api/keys/validate-all')
      await loadKeys()
    } catch { }
    setValidatingAll(false)
  }

  const regenerateUnified = async () => {
    try {
      const data = await (await fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/api/settings/api-key/regenerate`, { method: 'POST' })).json()
      setUnifiedKey(data.key)
    } catch { }
  }

  const copyUnified = () => navigator.clipboard.writeText(unifiedKey)

  const grouped: Record<string, typeof keys> = {}
  for (const k of keys) {
    if (!grouped[k.platform]) grouped[k.platform] = []
    grouped[k.platform].push(k)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">API Keys</h1>
        <button onClick={validateAll} disabled={validatingAll}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white transition-colors cursor-pointer">
          {validatingAll && (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {validatingAll ? 'Validating...' : 'Validate All'}
        </button>
      </div>

      {/* Unified API Key */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-blue-500 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2">Your Proxy API Key</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">Use this key to call the API. Base URL: <code className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-xs font-mono">http://localhost:8000</code> — Endpoint: <code className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-xs font-mono">/v1/chat/completions</code></p>
        <div className="flex items-center gap-2">
          <code className="flex-1 bg-gray-100 dark:bg-gray-700 px-3 py-2 rounded-lg text-sm font-mono truncate border border-gray-200 dark:border-gray-600">
            {showKey ? unifiedKey : unifiedKey ? unifiedKey.slice(0, 8) + '...' + unifiedKey.slice(-4) : '(not set)'}
          </code>
          <button onClick={() => setShowKey(!showKey)} className="px-3 py-1.5 text-xs font-medium bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg cursor-pointer">{showKey ? 'Hide' : 'Show'}</button>
          <button onClick={copyUnified} className="px-3 py-1.5 text-xs font-medium bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg cursor-pointer">Copy</button>
          <button onClick={regenerateUnified} className="px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg cursor-pointer transition-colors">Regenerate</button>
        </div>
      </div>

      {/* Add Key */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-emerald-500 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">Add Provider Key</h3>
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <label className="text-xs text-gray-500 dark:text-gray-400 font-medium">Platform</label>
            <select value={newPlatform} onChange={e => setNewPlatform(e.target.value)} className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm">
              {platforms.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-50 space-y-1">
            <label className="text-xs text-gray-500 dark:text-gray-400 font-medium">API Key</label>
            <input type="password" placeholder="sk-..." value={newKey} onChange={e => setNewKey(e.target.value)} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500 dark:text-gray-400 font-medium">Label</label>
            <input type="text" placeholder="Optional" value={newLabel} onChange={e => setNewLabel(e.target.value)} className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm w-36" />
          </div>
          <button onClick={addKey} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg cursor-pointer transition-colors">Add Key</button>
        </div>
      </div>

      {/* Keys List */}
      {loading ? null : Object.entries(grouped).length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50">
          <svg className="w-16 h-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
          </svg>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No provider keys configured</p>
          <p className="text-xs text-gray-400 mt-1">Add a provider key above to get started</p>
        </div>
      ) : (
        Object.entries(grouped).map(([platform, platformKeys]) => (
          <div key={platform} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 p-5">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">{platform}</h3>
            {platformKeys.map(k => (
              <div key={k.id} className="flex items-center gap-3 py-2.5 border-b border-gray-100 dark:border-gray-700/50 last:border-0">
                <span className={`w-2 h-2 rounded-full shrink-0 ${k.status === 'healthy' ? 'bg-emerald-500' : k.status === 'rate_limited' ? 'bg-amber-500' : k.status === 'invalid' || k.status === 'error' ? 'bg-rose-500' : 'bg-gray-400'}`} />
                <span className="font-mono text-sm flex-1 text-gray-900 dark:text-gray-100">{k.maskedKey}</span>
                {k.label && <span className="text-xs text-gray-500 dark:text-gray-400">{k.label}</span>}
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  k.status === 'healthy' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400' :
                  k.status === 'rate_limited' ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400' :
                  k.status === 'invalid' || k.status === 'error' ? 'bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400' :
                  'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                }`}>{k.status}</span>
                <button onClick={() => toggleKey(k.id, !k.enabled)} className={`w-9 h-5 rounded-full relative transition-colors ${k.enabled ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}`}>
                  <span className={`absolute top-0.5 left-0.5 w-3.5 h-3.5 bg-white rounded-full transition-transform ${k.enabled ? 'translate-x-4' : ''}`} />
                </button>
                <button onClick={() => validateKey(k.id)} className="px-2.5 py-1 text-xs font-medium text-emerald-600 hover:text-emerald-700 bg-white dark:bg-gray-900 border border-emerald-300 dark:border-emerald-800 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 rounded-lg cursor-pointer transition-colors">Validate</button>
                <button onClick={() => deleteKey(k.id)} className="px-2.5 py-1 text-xs font-medium text-rose-600 hover:text-rose-700 bg-white dark:bg-gray-900 border border-rose-300 dark:border-rose-800 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded-lg cursor-pointer transition-colors">Remove</button>
              </div>
            ))}
          </div>
        ))
      )}
    </div>
  )
}
