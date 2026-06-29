import { useState, useCallback } from 'react'
import { apiGet } from '../api'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { ErrorsTable } from '../components/ErrorsTable'
import { ErrorChart } from '../components/ErrorChart'

export function Errors() {
  const [errors, setErrors] = useState<any[]>([])
  const [distribution, setDistribution] = useState<any[]>([])
  const refresh = useCallback(async () => {
    try {
      const e = await apiGet('/api/analytics/errors?range=24h')
      setErrors(Array.isArray(e) ? e : [])
      const d = await apiGet('/api/analytics/error-distribution?range=24h')
      setDistribution(Array.isArray(d?.byCategory) ? d.byCategory : [])
    } catch { /* ignore */ }
  }, [])
  useAutoRefresh(refresh)

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Errors</h1>
        <button onClick={refresh} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg cursor-pointer transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
          </svg>
          Refresh
        </button>
      </div>
      <div className="space-y-6">
        <ErrorsTable errors={errors} />
        <ErrorChart data={distribution} />
      </div>
    </div>
  )
}
