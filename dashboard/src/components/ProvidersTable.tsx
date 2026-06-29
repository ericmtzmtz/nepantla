interface ProviderRow {
  platform: string
  requests: number
  errors: number
  avg_latency: number
}

export function ProvidersTable({ data }: { data: ProviderRow[] }) {
  return (
    <div className="h-full bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-blue-500 overflow-auto">
      <div className="p-5 pb-0">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Provider Breakdown</h3>
      </div>
      <div className="p-5 pt-3">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
              <th className="pb-2 pr-2 font-medium">Platform</th>
              <th className="pb-2 pr-2 font-medium">Requests</th>
              <th className="pb-2 pr-2 font-medium">Errors</th>
              <th className="pb-2 font-medium">Avg Latency</th>
            </tr>
          </thead>
          <tbody>
            {data.map((p, i) => (
              <tr key={i} className="border-b dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="py-2 pr-2 font-medium text-gray-900 dark:text-gray-100">{p.platform}</td>
                <td className="py-2 pr-2">{p.requests}</td>
                <td className="py-2 pr-2 text-rose-500">{p.errors}</td>
                <td className="py-2">{p.avg_latency.toFixed(0)}ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
