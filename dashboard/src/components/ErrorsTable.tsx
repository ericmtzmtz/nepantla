interface ErrorRow {
  platform: string
  model: string
  error: string
  timestamp: string
}

export function ErrorsTable({ errors }: { errors: ErrorRow[] }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-rose-500 overflow-x-auto">
      <div className="p-5 pb-0">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Recent Errors</h3>
      </div>
      <div className="p-5 pt-3">
        {errors.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-gray-400">
            <svg className="w-12 h-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm">No errors in the last 24h</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                <th className="pb-2 pr-2 font-medium">Platform</th>
                <th className="pb-2 pr-2 font-medium">Model</th>
                <th className="pb-2 pr-2 font-medium">Error</th>
                <th className="pb-2 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {errors.map((e, i) => (
                <tr key={i} className="border-b dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="py-2 pr-2">{e.platform}</td>
                  <td className="py-2 pr-2 font-mono text-xs">{e.model}</td>
                  <td className="py-2 pr-2 text-rose-500">{e.error}</td>
                  <td className="py-2 text-xs text-gray-400">{new Date(e.timestamp).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
