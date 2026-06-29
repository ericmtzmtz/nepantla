import { useState, useEffect } from 'react'
import { apiGet } from '../api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts'

export function Analytics() {
  const [range, setRange] = useState('7d')
  const [summary, setSummary] = useState<any>(null)
  const [byPlatform, setByPlatform] = useState<any[]>([])
  const [timeline, setTimeline] = useState<any[]>([])
  const [byModel, setByModel] = useState<any[]>([])

  const load = async () => {
    try {
      setSummary(await apiGet(`/api/analytics/summary?range=${range}`))
      const bp = await apiGet(`/api/analytics/by-platform?range=${range}`)
      setByPlatform(Array.isArray(bp) ? bp : [])
      const tl = await apiGet(`/api/analytics/timeline?range=${range}`)
      setTimeline(Array.isArray(tl) ? tl : [])
      const bm = await apiGet(`/api/analytics/by-model?range=${range}`)
      setByModel(Array.isArray(bm) ? bm : [])
    } catch { }
  }
  useEffect(() => { load() }, [range])

  const ranges = ['24h', '7d', '30d']
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Analytics</h1>
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5 border border-gray-200 dark:border-gray-700">
          {ranges.map(r => (
            <button key={r} onClick={() => setRange(r)} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all cursor-pointer ${range === r ? 'bg-white dark:bg-gray-700 shadow-sm text-blue-700 dark:text-blue-300' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>{r}</button>
          ))}
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          {[
            { label: 'Total Requests', value: summary.totalRequests.toLocaleString(), accent: 'blue' as const },
            { label: 'Success Rate', value: `${summary.successRate}%`, accent: 'emerald' as const },
            { label: 'Input Tokens', value: summary.totalInputTokens.toLocaleString(), accent: 'blue' as const },
            { label: 'Output Tokens', value: summary.totalOutputTokens.toLocaleString(), accent: 'blue' as const },
            { label: 'Avg Latency', value: `${summary.avgLatencyMs}ms`, accent: 'amber' as const },
            { label: 'Est. Savings', value: `$${summary.estimatedCostSavings}`, accent: 'emerald' as const },
          ].map(s => (
            <div key={s.label} className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-${s.accent}-500 p-4`}>
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">{s.label}</div>
              <div className="text-xl font-bold mt-1 text-gray-900 dark:text-gray-100">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Timeline */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-blue-500 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">Requests Over Time</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={timeline}>
            <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="successCount" stroke="#22c55e" name="Success" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="failureCount" stroke="#ef4444" name="Failure" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* By Platform */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-blue-500 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">Requests by Provider</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={byPlatform}>
            <XAxis dataKey="platform" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="requests" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* By Model */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-blue-500 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">Per-Model Breakdown</h3>
        <div className="overflow-x-auto max-h-64 overflow-y-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                <th className="pb-2 pr-2 font-medium sticky top-0 bg-white dark:bg-gray-800">Platform</th>
                <th className="pb-2 pr-2 font-medium sticky top-0 bg-white dark:bg-gray-800">Model</th>
                <th className="pb-2 pr-2 font-medium sticky top-0 bg-white dark:bg-gray-800">Requests</th>
                <th className="pb-2 pr-2 font-medium sticky top-0 bg-white dark:bg-gray-800">Success %</th>
                <th className="pb-2 pr-2 font-medium sticky top-0 bg-white dark:bg-gray-800">Latency</th>
                <th className="pb-2 pr-2 font-medium sticky top-0 bg-white dark:bg-gray-800">Input</th>
                <th className="pb-2 font-medium sticky top-0 bg-white dark:bg-gray-800">Output</th>
              </tr>
            </thead>
            <tbody>
              {byModel.map((m, i) => (
                <tr key={i} className="border-b dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="py-2 pr-2 text-gray-900 dark:text-gray-100">{m.platform}</td>
                  <td className="py-2 pr-2 font-mono text-xs">{m.modelId}</td>
                  <td className="py-2 pr-2">{m.requests}</td>
                  <td className="py-2 pr-2">{m.successRate}%</td>
                  <td className="py-2 pr-2">{m.avgLatencyMs}ms</td>
                  <td className="py-2 pr-2">{m.totalInputTokens.toLocaleString()}</td>
                  <td className="py-2">{m.totalOutputTokens.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
