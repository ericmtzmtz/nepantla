import { useState, useCallback } from 'react'
import { apiGet } from '../api'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { KpiCard } from '../components/KpiCard'
import { RequestChart } from '../components/RequestChart'

interface DashboardData {
  total_requests: number
  success_rate: number
  active_providers: number
  error_count: number
  request_volume: { hour: string; requests: number }[]
}

export function Overview() {
  const [data, setData] = useState<DashboardData | null>(null)
  const refresh = useCallback(async () => {
    try {
      const d = await apiGet('/api/analytics/dashboard?range=7d')
      setData(d && typeof d === 'object' ? d : null)
    } catch { /* ignore */ }
  }, [])
  useAutoRefresh(refresh)

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Overview</h1>
        <button onClick={refresh} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg cursor-pointer transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
          </svg>
          Refresh
        </button>
      </div>
      {data ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <KpiCard label="Total Requests (24h)" value={data.total_requests.toLocaleString()} accent="blue" />
            <KpiCard label="Success Rate" value={`${(data.success_rate * 100).toFixed(1)}%`} accent="emerald" />
            <KpiCard label="Active Providers" value={data.active_providers} accent="amber" />
            <KpiCard label="Errors (24h)" value={data.error_count.toLocaleString()} sub="See Errors tab for details" accent="rose" />
          </div>
          <RequestChart data={Array.isArray(data.request_volume) ? data.request_volume : []} />
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <svg className="w-10 h-10 animate-spin mb-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-sm">Loading...</p>
        </div>
      )}
    </div>
  )
}
