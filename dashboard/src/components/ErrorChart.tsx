import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export function ErrorChart({ data }: { data: { error: string; count: number }[] }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-blue-500 p-5">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">Error Distribution</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
          <XAxis dataKey="error" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Bar dataKey="count" fill="#ef4444" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
