import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export function UsageChart({ data }: { data: { hour: string; tokens: number }[] }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 border-t-blue-500 p-5">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">Token Consumption</h3>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data}>
          <XAxis dataKey="hour" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Area type="monotone" dataKey="tokens" stroke="#10b981" fill="#10b98120" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
