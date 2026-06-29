import { useState, useCallback } from 'react'
import { apiGet, apiPost, apiPut, apiDelete, apiPatch } from '../api'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { ProvidersTable } from '../components/ProvidersTable'

interface ProviderEntry {
  id: string
  name: string
  base_url: string | null
  timeout_ms: number
  extra_headers: Record<string, string> | null
  is_native: boolean
  npm_package: string | null
  free_tier: boolean
  enabled: boolean
}

interface ProviderForm {
  id: string
  name: string
  base_url: string
  timeout_ms: number
  extra_headers: string
  is_native: boolean
  free_tier: boolean
  enabled: boolean
}

const emptyForm: ProviderForm = {
  id: '', name: '', base_url: '', timeout_ms: 30000,
  extra_headers: '', is_native: false, free_tier: false, enabled: true,
}

export function Providers() {
  const [tab, setTab] = useState<'management' | 'analytics'>('management')
  const [providers, setProviders] = useState<ProviderEntry[]>([])
  const [analyticsData, setAnalyticsData] = useState([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<ProviderForm>(emptyForm)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [error, setError] = useState('')

  const loadProviders = useCallback(async () => {
    try { setProviders(await apiGet('/api/provisioning/providers')) } catch { /* ignore */ }
  }, [])

  const loadAnalytics = useCallback(async () => {
    try { setAnalyticsData(await apiGet('/api/analytics/providers')) } catch { /* ignore */ }
  }, [])

  useAutoRefresh(useCallback(() => {
    if (tab === 'management') loadProviders()
    else loadAnalytics()
  }, [tab]))

  const openCreate = () => {
    setEditingId(null)
    setForm(emptyForm)
    setError('')
    setModalOpen(true)
  }

  const openEdit = (p: ProviderEntry) => {
    setEditingId(p.id)
    setForm({
      id: p.id,
      name: p.name,
      base_url: p.base_url || '',
      timeout_ms: p.timeout_ms,
      extra_headers: p.extra_headers ? JSON.stringify(p.extra_headers, null, 2) : '',
      is_native: p.is_native,
      free_tier: p.free_tier,
      enabled: p.enabled,
    })
    setError('')
    setModalOpen(true)
  }

  const save = async () => {
    setError('')
    try {
      const body = {
        name: form.name,
        base_url: form.base_url || null,
        timeout_ms: form.timeout_ms,
        extra_headers: form.extra_headers ? JSON.parse(form.extra_headers) : null,
        is_native: form.is_native,
        free_tier: form.free_tier,
        enabled: form.enabled,
      }
      if (editingId) {
        await apiPut(`/api/provisioning/providers/${editingId}`, body)
      } else {
        await apiPost('/api/provisioning/providers', { ...body, id: form.id })
      }
      setModalOpen(false)
      await loadProviders()
    } catch (e: any) {
      setError(e.message || 'Save failed')
    }
  }

  const toggleProvider = async (id: string) => {
    try {
      await apiPatch(`/api/provisioning/providers/${id}/toggle`)
      await loadProviders()
    } catch { /* ignore */ }
  }

  const deleteProvider = async (id: string) => {
    try {
      await apiDelete(`/api/provisioning/providers/${id}`)
      setConfirmDelete(null)
      await loadProviders()
    } catch (e: any) {
      setError(e.message || 'Delete failed')
      setConfirmDelete(null)
    }
  }

  const runSync = async () => {
    try { await apiPost('/api/provisioning/sync'); await loadProviders() } catch { /* ignore */ }
  }
  const refreshCatalog = async () => {
    try { await apiPost('/api/provisioning/refresh-catalog'); await loadProviders() } catch { /* ignore */ }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Providers</h1>
        <div className="flex items-center gap-2">
          <button onClick={runSync} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg cursor-pointer transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" /></svg>
            Sync
          </button>
          <button onClick={refreshCatalog} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg cursor-pointer transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 8.688c0-.621.504-1.125 1.125-1.125h1.874a1.124 1.124 0 01.796.329l.367.367a1.123 1.123 0 00.795.33h4.088c.62 0 1.125.504 1.125 1.125v.751M9 12.75L11.25 15 15 9.75m-3-6.75a9 9 0 100 18 9 9 0 000-18z" /></svg>
            Refresh Catalog
          </button>
          {tab === 'management' && (
            <button onClick={openCreate} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg cursor-pointer transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
              Add Provider
            </button>
          )}
        </div>
      </div>

      <div className="flex gap-4 border-b border-gray-200 dark:border-gray-700">
        <button onClick={() => setTab('management')} className={`pb-2 text-sm font-medium border-b-2 transition-colors cursor-pointer ${tab === 'management' ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}>
          Management
        </button>
        <button onClick={() => setTab('analytics')} className={`pb-2 text-sm font-medium border-b-2 transition-colors cursor-pointer ${tab === 'analytics' ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}>
          Analytics
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-400 px-4 py-2 rounded-lg text-sm">
          {error}
          <button onClick={() => setError('')} className="ml-2 font-bold cursor-pointer">&times;</button>
        </div>
      )}

      {tab === 'management' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-blue-500 overflow-x-auto">
          {providers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <svg className="w-16 h-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-18v18M3 7h2.25m13.5 0H21M3 11h2.25m13.5 0H21M3 15h2.25m13.5 0H21M4.5 3h15" /></svg>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No providers configured</p>
              <p className="text-xs text-gray-400 mt-1">Run the seed script or click "Add Provider"</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                  <th className="p-3 font-medium">ID</th>
                  <th className="p-3 font-medium">Name</th>
                  <th className="p-3 font-medium">Base URL</th>
                  <th className="p-3 font-medium">Timeout</th>
                  <th className="p-3 font-medium text-center">Type</th>
                  <th className="p-3 font-medium text-center">Free</th>
                  <th className="p-3 font-medium text-center">Enabled</th>
                  <th className="p-3 font-medium text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                {providers.map(p => (
                  <tr key={p.id} className="border-b dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="p-3 font-mono text-xs text-gray-900 dark:text-gray-100">{p.id}</td>
                    <td className="p-3 font-medium text-gray-900 dark:text-gray-100">{p.name}</td>
                    <td className="p-3 text-xs text-gray-500 dark:text-gray-400 max-w-62.5 truncate" title={p.base_url || ''}>{p.base_url || <span className="italic text-gray-400">none</span>}</td>
                    <td className="p-3 text-gray-500 dark:text-gray-400">{p.timeout_ms}ms</td>
                    <td className="p-3 text-center">
                      {p.is_native
                        ? <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400 font-medium">Native</span>
                        : <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400 font-medium">Generic</span>
                      }
                    </td>
                    <td className="p-3 text-center">
                      {p.free_tier
                        ? <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400 font-medium">Free</span>
                        : <span className="text-xs text-gray-400">—</span>
                      }
                    </td>
                    <td className="p-3 text-center">
                      <label className="inline-flex items-center cursor-pointer">
                        <input type="checkbox" checked={p.enabled} onChange={() => toggleProvider(p.id)} className="sr-only peer" />
                        <div className="w-9 h-5 bg-gray-300 dark:bg-gray-600 peer-checked:bg-blue-600 rounded-full peer-checked:after:translate-x-4 after:content-[''] after:absolute after:top-0.75 after:left-0.75 after:bg-white after:rounded-full after:h-3.5 after:w-3.5 after:transition-all relative" />
                      </label>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center justify-center gap-1.5">
                        <button onClick={() => openEdit(p)} className="px-2.5 py-1 text-xs font-medium text-blue-600 hover:text-blue-700 bg-white dark:bg-gray-900 border border-blue-300 dark:border-blue-800 hover:bg-blue-50 dark:hover:bg-blue-950/30 rounded-lg cursor-pointer transition-colors">Edit</button>
                        <button onClick={() => setConfirmDelete(p.id)} className="px-2.5 py-1 text-xs font-medium text-rose-600 hover:text-rose-700 bg-white dark:bg-gray-900 border border-rose-300 dark:border-rose-800 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded-lg cursor-pointer transition-colors">Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === 'analytics' && <div className="flex-1 min-h-0"><ProvidersTable data={analyticsData} /></div>}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setModalOpen(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-lg mx-4 p-6" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">
              {editingId ? 'Edit: ' + editingId : 'Add Provider'}
            </h2>
            <div className="space-y-3">
              {!editingId && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">ID *</label>
                  <input value={form.id} onChange={e => setForm(p => ({ ...p, id: e.target.value }))} placeholder="e.g. my-provider" className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm" />
                </div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Name *</label>
                <input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="My Provider" className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Base URL</label>
                <input value={form.base_url} onChange={e => setForm(p => ({ ...p, base_url: e.target.value }))} placeholder="https://api.example.com/v1" className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Timeout (ms)</label>
                <input type="number" value={form.timeout_ms} onChange={e => setForm(p => ({ ...p, timeout_ms: parseInt(e.target.value) || 30000 }))} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Extra Headers (JSON)</label>
                <textarea value={form.extra_headers} onChange={e => setForm(p => ({ ...p, extra_headers: e.target.value }))} rows={3} placeholder='{"X-Api-Key": "..."}' className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm font-mono" />
              </div>
              <div className="flex items-center gap-6">
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                  <input type="checkbox" checked={form.is_native} onChange={e => setForm(p => ({ ...p, is_native: e.target.checked }))} className="rounded" />
                  Native Provider
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                  <input type="checkbox" checked={form.free_tier} onChange={e => setForm(p => ({ ...p, free_tier: e.target.checked }))} className="rounded" />
                  Free Tier
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                  <input type="checkbox" checked={form.enabled} onChange={e => setForm(p => ({ ...p, enabled: e.target.checked }))} className="rounded" />
                  Enabled
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setModalOpen(false)} className="px-4 py-2 text-sm font-medium bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg cursor-pointer">Cancel</button>
              <button onClick={save} className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg cursor-pointer transition-colors">{editingId ? 'Save' : 'Create'}</button>
            </div>
          </div>
        </div>
      )}

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setConfirmDelete(null)}>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-sm mx-4 p-6" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">Delete Provider?</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Are you sure you want to delete <strong className="text-gray-700 dark:text-gray-300">{confirmDelete}</strong>?
              This will fail if the provider has active API keys.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(null)} className="px-4 py-2 text-sm font-medium bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg cursor-pointer">Cancel</button>
              <button onClick={() => deleteProvider(confirmDelete)} className="px-4 py-2 text-sm font-medium bg-rose-600 hover:bg-rose-700 text-white rounded-lg cursor-pointer transition-colors">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
