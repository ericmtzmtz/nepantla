export function KpiCard({ label, value, sub, accent = 'blue' }: { label: string; value: string | number; sub?: string; accent?: 'blue' | 'emerald' | 'amber' | 'rose' }) {
  const accentBorder = {
    blue: 'border-t-blue-500',
    emerald: 'border-t-emerald-500',
    amber: 'border-t-amber-500',
    rose: 'border-t-rose-500',
  }[accent]
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700/50 border-t-3 ${accentBorder} p-5`}>
      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">{label}</div>
      <div className="text-2xl font-bold mt-1.5 text-gray-900 dark:text-gray-100">{value}</div>
      {sub && <div className="text-xs text-gray-400 dark:text-gray-500 mt-1.5">{sub}</div>}
    </div>
  )
}
