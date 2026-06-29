import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Overview } from './pages/Overview'
import { Keys } from './pages/Keys'
import { Playground } from './pages/Playground'
import { Fallback } from './pages/Fallback'
import { Analytics } from './pages/Analytics'
import { Errors } from './pages/Errors'
import { Models } from './pages/Models'
import { ModelSidePanel } from './components/ModelSidePanel'
import { Providers } from './pages/Providers'
import { Usage } from './pages/Usage'

const pathLabels: Record<string, string> = {
  '/': 'Overview',
  '/keys': 'API Keys',
  '/models': 'Model Catalog',
  '/playground': 'Playground',
  '/fallback': 'Fallback',
  '/analytics': 'Analytics',
  '/errors': 'Errors',
  '/providers': 'Providers',
  '/usage': 'Usage',
}

interface ModelEntry {
  id: string
  platform: string
  model_id: string
  display_name: string
  enabled: boolean
  intelligence_rank: number
  speed_rank: number
  size_label: string
  context_window: number | null
  supports_vision: boolean
  supports_image_gen: boolean
  supports_audio_stt: boolean
  supports_audio_tts: boolean
  supports_embeddings: boolean
  has_key: boolean
}

function AppShell() {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [dark, setDark] = useState(() => localStorage.getItem('theme') !== 'light')
  const [selectedModel, setSelectedModel] = useState<ModelEntry | null>(null)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  const currentPage = pathLabels[location.pathname] || 'Dashboard'

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="flex items-center gap-3 px-4 lg:px-6 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm">
          <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 cursor-pointer">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{currentPage}</h1>
          <div className="ml-auto" />
          <button onClick={() => setDark(!dark)} className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg cursor-pointer" title={dark ? 'Switch to light mode' : 'Switch to dark mode'}>
            {dark ? (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
              </svg>
            )}
          </button>
        </header>
        <main className="flex-1 overflow-auto p-6 lg:p-8">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/keys" element={<Keys />} />
            <Route path="/playground" element={<Playground />} />
            <Route path="/models" element={<Models onSelectModel={setSelectedModel} />} />
            <Route path="/fallback" element={<Fallback />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/errors" element={<Errors />} />
            <Route path="/providers" element={<Providers />} />
            <Route path="/usage" element={<Usage />} />
          </Routes>
          <ModelSidePanel model={selectedModel} onClose={() => setSelectedModel(null)} />
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}

export default App
