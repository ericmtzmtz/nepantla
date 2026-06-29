import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export function RequestChart({ data }: { data: { hour: string; requests: number }[] }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-blue-500 p-5">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">Request Volume (7d)</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <XAxis dataKey="hour" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Line type="monotone" dataKey="requests" stroke="#3b82f6" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
