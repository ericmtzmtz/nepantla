import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Overview', icon: 'overview' },
  { to: '/keys', label: 'API Keys', icon: 'keys' },
  { to: '/playground', label: 'Playground', icon: 'play' },
  { to: '/models', label: 'Models', icon: 'models' },
  { to: '/fallback', label: 'Fallback', icon: 'shuffle' },
  { to: '/analytics', label: 'Analytics', icon: 'analytics' },
  { to: '/errors', label: 'Errors', icon: 'errors' },
  { to: '/providers', label: 'Providers', icon: 'providers' },
  { to: '/usage', label: 'Usage', icon: 'usage' },
]

function SidebarIcon({ name }: { name: string }) {
  const cls = "w-5 h-5"
  switch (name) {
    case 'overview': return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" /></svg>
    case 'keys': return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" /></svg>
    case 'play': return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" /></svg>
    case 'shuffle': return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" /></svg>
    case 'analytics': return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>
    case 'errors': return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" /></svg>
    case 'providers': return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-18v18M3 7h2.25m13.5 0H21M3 11h2.25m13.5 0H21M3 15h2.25m13.5 0H21M4.5 3h15" /></svg>
    case 'usage': return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6a7.5 7.5 0 107.5 7.5h-7.5V6z" /><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 3H21v7.5M21 3l-9 9" /></svg>
    case 'models': return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>
    default: return null
  }
}

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      {open && <div className="fixed inset-0 bg-black/50 lg:hidden z-40" onClick={onClose} />}
      <aside className={`fixed top-0 left-0 h-full w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 z-50 transform transition-transform lg:relative lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-5 border-b border-gray-200 dark:border-gray-800">
          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">nepantla</div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Proxy Dashboard</div>
        </div>
        <nav className="p-3 space-y-1">
          {links.map(l => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border-r-2 border-blue-600'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`
              }
            >
              <SidebarIcon name={l.icon} />
              {l.label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  )
}
