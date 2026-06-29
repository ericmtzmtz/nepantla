import { useState, useEffect, useRef } from 'react'
import { apiGet } from '../api'

type Tab = 'chat' | 'vision' | 'image' | 'tts' | 'audio'

interface ModelInfo {
  model_id: string; platform: string; has_key: boolean
  supports_vision: boolean; supports_image_gen: boolean
  supports_audio_stt: boolean; supports_audio_tts: boolean
}

interface Message { 
  role: 'user' | 'assistant'; 
  content: string; 
  platform?: string; 
  model?: string; 
  latency?: number;
  tool_calls?: any[]
}

const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'chat', label: 'Chat', icon: 'M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z' },
  { id: 'vision', label: 'Vision', icon: 'M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z' },
  { id: 'image', label: 'Image Gen', icon: 'M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z' },
  { id: 'tts', label: 'TTS', icon: 'M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z' },
  { id: 'audio', label: 'Audio', icon: 'M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z' },
]

const VOICES = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']

function TabIcon({ path }: { path: string }) {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  )
}

export function Playground() {
  const [tab, setTab] = useState<Tab>('chat')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [unifiedKey, setUnifiedKey] = useState('')
  const [genN, setGenN] = useState(1)
  const [genSize, setGenSize] = useState('1024x1024')
  const [genImages, setGenImages] = useState<string[]>([])
  const [voice, setVoice] = useState('alloy')
  const [audioUrl, setAudioUrl] = useState('')
  const [transcript, setTranscript] = useState('')
  const [toolsJson, setToolsJson] = useState('')
  const [showTools, setShowTools] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    Promise.all([
      apiGet('/api/models').catch(() => []),
      apiGet('/api/settings/api-key').catch(() => ({ key: '' })),
    ]).then(([modelsData, keyData]) => {
      const seen = new Set<string>()
      const list: ModelInfo[] = Array.isArray(modelsData)
        ? modelsData.filter((m: any) => { if (seen.has(m.model_id)) return false; seen.add(m.model_id); return true }).filter((m: any) => m.has_key).map((m: any) => ({
            model_id: m.model_id, platform: m.platform, has_key: true,
            supports_vision: !!m.supports_vision, supports_image_gen: !!m.supports_image_gen,
            supports_audio_stt: !!m.supports_audio_stt, supports_audio_tts: !!m.supports_audio_tts,
          }))
        : []
      setModels(list)
      setUnifiedKey((keyData as any).key || '')
    })
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const filteredModels = models.filter(m => {
    if (tab === 'vision') return m.supports_vision
    if (tab === 'image') return m.supports_image_gen
    if (tab === 'tts') return m.supports_audio_tts
    if (tab === 'audio') return m.supports_audio_stt
    return true
  })

  const fetchJson = (url: string, body: any) =>
    fetch(`${BASE}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${unifiedKey || 'playground'}` },
      body: JSON.stringify(body),
    }).then(r => r.json())

  const sendChat = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)
    try {
        const body: any = {
          model: selectedModel || undefined,
          messages: [...messages, userMsg].map(m => ({ role: m.role, content: m.content })),
        }
        if (toolsJson.trim()) {
          try { body.tools = JSON.parse(toolsJson) } catch { /* ignore invalid JSON */ }
        }
        const data = await fetchJson('/v1/chat/completions', body)
       setMessages(prev => [...prev, {
         role: 'assistant',
         content: data.choices?.[0]?.message?.content || data.error?.message || 'No response',
         platform: data._routed_via,
         model: data.model || selectedModel,
         latency: data._latency_ms || 0,
         tool_calls: data.choices?.[0]?.message?.tool_calls || undefined,
       }])
     } catch (e: any) {
       setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }])
     }
    setLoading(false)
  }

  const sendVision = async () => {
    if (!input.trim() || loading) return
    const userDisplay = `${input}${imageUrl ? `\n[Image: ${imageUrl}]` : ''}`
    setMessages(prev => [...prev, { role: 'user', content: userDisplay }])
    const imgContent = imageUrl
      ? [{ type: 'text', text: input }, { type: 'image_url', image_url: { url: imageUrl } }]
      : input
    setInput('')
    setImageUrl('')
    setLoading(true)
    try {
      const apiMessages = messages.map(m => ({ role: m.role, content: m.content }))
      apiMessages.push({ role: 'user', content: imgContent as any })
      const data = await fetchJson('/v1/chat/completions', { model: selectedModel || undefined, messages: apiMessages })
      setMessages(prev => [...prev, {
         role: 'assistant',
         content: data.choices?.[0]?.message?.content || data.error?.message || 'No response',
         platform: data._routed_via,
         model: data.model || selectedModel,
         latency: data._latency_ms || 0,
         tool_calls: data.choices?.[0]?.message?.tool_calls || undefined,
       }])
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }])
    }
    setLoading(false)
  }

  const sendImageGen = async () => {
    if (!input.trim() || loading) return
    setLoading(true)
    setGenImages([])
    try {
      const data = await fetchJson('/v1/images/generations', {
        model: selectedModel || undefined,
        prompt: input,
        n: genN,
        size: genSize,
      })
      setGenImages((data.data || []).map((d: any) => d.url || d.b64_json || '').filter(Boolean))
    } catch (e: any) {
      setGenImages([])
      alert(`Error: ${e.message}`)
    }
    setLoading(false)
  }

  const sendTts = async () => {
    if (!input.trim() || loading) return
    setLoading(true)
    setAudioUrl('')
    try {
      const res = await fetch(`${BASE}/v1/audio/speech`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${unifiedKey || 'playground'}` },
        body: JSON.stringify({ model: selectedModel || undefined, input: input, voice }),
      })
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText) }
      const blob = await res.blob()
      setAudioUrl(URL.createObjectURL(blob))
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    }
    setLoading(false)
  }

  const sendAudio = async (file: File) => {
    if (loading) return
    setLoading(true)
    setTranscript('')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('model', selectedModel || 'auto')
      const res = await fetch(`${BASE}/v1/audio/transcriptions`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${unifiedKey || 'playground'}` },
        body: form,
      })
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText) }
      const data = await res.json()
      setTranscript(data.text || '(no transcription)')
    } catch (e: any) {
      setTranscript(`Error: ${e.message}`)
    }
    setLoading(false)
  }

  const renderMessages = () => (
    <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700/50">
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <svg className="w-14 h-14 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
          </svg>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Send a message to start</p>
          <p className="text-xs text-gray-400 mt-1">Choose a model above or leave it on Auto</p>
        </div>
      ) : (
        messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${
              m.role === 'user'
                ? 'bg-blue-600 text-white rounded-2xl rounded-tr-sm'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-2xl rounded-tl-sm'
            } px-4 py-2.5 shadow-sm`}>
<p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
               {(m.tool_calls?.length ?? 0) > 0 && (
                 <div className="mt-2">
                   <p className="text-xs font-semibold text-blue-600 dark:text-blue-400">Tool Calls:</p>
                   <div className="space-y-1">
                     {m.tool_calls?.map((tc: any, index: number) => (
                       <div key={index} className="bg-gray-50 dark:bg-gray-800 p-2 rounded">
                         <p className="text-xs font-mono">{tc.function?.name || 'unknown'}</p>
                         <p className="text-xs break-all">{tc.function?.arguments || '{}'}</p>
                       </div>
                     ))}
                   </div>
                 </div>
               )}
               {(m.platform != null || (m.latency ?? 0) > 0) && (
                <p className={`text-xs mt-1.5 ${m.role === 'user' ? 'text-blue-200' : 'text-gray-400'}`}>
                  {m.platform && <>via {m.platform}</>}
                  {m.latency ? <> • {m.latency}ms</> : ''}
                </p>
              )}
            </div>
          </div>
        ))
      )}
      {loading && (
        <div className="flex justify-start">
          <div className="bg-gray-100 dark:bg-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)] max-w-4xl mx-auto">
      {/* Tab bar + model selector */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5 border border-gray-200 dark:border-gray-700">
          {TABS.map(t => (
            <button key={t.id} onClick={() => { setTab(t.id); setMessages([]); setGenImages([]); setAudioUrl(''); setTranscript('') }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all cursor-pointer ${
                tab === t.id ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}>
              <TabIcon path={t.icon} />
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <label className="text-xs text-gray-500 dark:text-gray-400 font-medium">Model:</label>
          <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 shadow-sm min-w-40">
            <option value="">Auto (fallback)</option>
            {filteredModels.map(m => <option key={m.model_id} value={m.model_id}>{m.platform}/{m.model_id}</option>)}
          </select>
        </div>
      </div>

      {/* Debug: Tools JSON */}
      <div className="mb-3">
        <button onClick={() => setShowTools(!showTools)}
          className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer">
          {showTools ? '▼' : '▶'} Tools (debug)
        </button>
        {showTools && (
          <textarea value={toolsJson} onChange={e => setToolsJson(e.target.value)}
            placeholder='[{"type":"function","function":{"name":"get_weather","description":"...","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}]'
            className="w-full mt-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-xs font-mono bg-white dark:bg-gray-800 resize-y h-20 shadow-sm outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-500" />
        )}
      </div>

      {(tab === 'chat') && <>
        {renderMessages()}
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat() } }}
              placeholder="Type a message... (Enter to send, Shift+Enter for newline)"
              className="w-full px-4 py-3 pr-16 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 resize-none text-sm shadow-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none" rows={2} />
            <span className="absolute bottom-3 right-3 text-xs text-gray-400">{input.length}</span>
          </div>
          <button onClick={sendChat} disabled={loading || !input.trim()}
            className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-xl text-sm font-medium transition-colors cursor-pointer shadow-sm">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </>}

      {(tab === 'vision') && <>
        {renderMessages()}
        <div className="mb-3">
          <input value={imageUrl} onChange={e => setImageUrl(e.target.value)}
            placeholder="Paste image URL..."
            className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 text-sm shadow-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none" />
        </div>
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendVision() } }}
              placeholder="Ask about the image..."
              className="w-full px-4 py-3 pr-16 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 resize-none text-sm shadow-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none" rows={2} />
            <span className="absolute bottom-3 right-3 text-xs text-gray-400">{input.length}</span>
          </div>
          <button onClick={sendVision} disabled={loading || !input.trim()}
            className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-xl text-sm font-medium transition-colors cursor-pointer shadow-sm">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </>}

      {(tab === 'image') && <>
        <div className="flex-1 overflow-y-auto space-y-3 mb-4 p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700/50">
          {genImages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <svg className="w-14 h-14 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
              </svg>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Describe an image to generate</p>
              <p className="text-xs text-gray-400 mt-1">Enter a prompt below and click Generate</p>
            </div>
          )}
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <div className="grid grid-cols-2 gap-3 w-full max-w-md">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="aspect-square bg-gray-200 dark:bg-gray-700 rounded-xl animate-pulse" />
                ))}
              </div>
              <p className="text-sm mt-4 animate-pulse">Generating...</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            {genImages.map((url, i) => (
              <img key={i} src={url} alt={`Generated ${i}`} className="rounded-xl w-full shadow-sm border border-gray-200 dark:border-gray-700" />
            ))}
          </div>
        </div>
        <div className="flex gap-3 mb-3 flex-wrap items-center">
          <label className="text-sm flex items-center gap-2 text-gray-700 dark:text-gray-300">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">N:</span>
            <select value={genN} onChange={e => setGenN(Number(e.target.value))} className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 shadow-sm">
              {[1, 2, 3, 4].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <label className="text-sm flex items-center gap-2 text-gray-700 dark:text-gray-300">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Size:</span>
            <select value={genSize} onChange={e => setGenSize(e.target.value)} className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 shadow-sm">
              {['256x256','512x512','1024x1024','1024x1792','1792x1024'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
        </div>
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendImageGen() } }}
              placeholder="Describe the image to generate..."
              className="w-full px-4 py-3 pr-16 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 resize-none text-sm shadow-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none" rows={2} />
            <span className="absolute bottom-3 right-3 text-xs text-gray-400">{input.length}</span>
          </div>
          <button onClick={sendImageGen} disabled={loading || !input.trim()}
            className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-xl text-sm font-medium transition-colors cursor-pointer shadow-sm">
            Generate
          </button>
        </div>
      </>}

      {(tab === 'tts') && <>
        <div className="flex-1 overflow-y-auto mb-4 p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700/50 flex flex-col items-center justify-center">
          {!audioUrl && !loading && (
            <div className="flex flex-col items-center text-gray-400">
              <svg className="w-14 h-14 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
              </svg>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Type text and select a voice</p>
              <p className="text-xs text-gray-400 mt-1">Choose a voice and enter text to speak</p>
            </div>
          )}
          {loading && (
            <div className="flex flex-col items-center text-gray-400">
              <div className="flex items-end gap-1 mb-4 h-12">
                {Array.from({ length: 20 }).map((_, i) => (
                  <div key={i} className="w-1.5 bg-blue-400 rounded-full animate-pulse" style={{
                    height: `${20 + Math.sin(i * 0.8) * 30 + Math.random() * 20}px`,
                    animationDelay: `${i * 80}ms`
                  }} />
                ))}
              </div>
              <p className="text-sm animate-pulse">Generating audio...</p>
            </div>
          )}
          {audioUrl && (
            <div className="w-full max-w-md">
              <div className="flex items-end gap-1 mb-4 justify-center h-16">
                {Array.from({ length: 30 }).map((_, i) => (
                  <div key={i} className="w-1.5 bg-blue-500 rounded-full" style={{
                    height: `${15 + Math.sin(i * 0.5 + Date.now() * 0.001) * 25 + 10}px`,
                  }} />
                ))}
              </div>
              <audio controls src={audioUrl} className="w-full" autoPlay />
            </div>
          )}
        </div>
        <div className="flex gap-3 mb-3 items-center">
          <label className="text-sm flex items-center gap-2 text-gray-700 dark:text-gray-300">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Voice:</span>
            <select value={voice} onChange={e => setVoice(e.target.value)} className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 shadow-sm">
              {VOICES.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
        </div>
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTts() } }}
              placeholder="Text to speak..."
              className="w-full px-4 py-3 pr-16 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 resize-none text-sm shadow-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none" rows={2} />
            <span className="absolute bottom-3 right-3 text-xs text-gray-400">{input.length}</span>
          </div>
          <button onClick={sendTts} disabled={loading || !input.trim()}
            className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-xl text-sm font-medium transition-colors cursor-pointer shadow-sm">
            Speak
          </button>
        </div>
      </>}

      {(tab === 'audio') && <>
        <div className="flex-1 overflow-y-auto mb-4 p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700/50">
          {!transcript && !loading && (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <svg className="w-14 h-14 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
              </svg>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Upload an audio file to transcribe</p>
              <p className="text-xs text-gray-400 mt-1">Supports MP3, WAV, M4A, and more</p>
            </div>
          )}
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <div className="flex items-end gap-1 mb-4 h-12">
                {Array.from({ length: 20 }).map((_, i) => (
                  <div key={i} className="w-1.5 bg-blue-400 rounded-full animate-pulse" style={{
                    height: `${15 + Math.sin(i * 0.7) * 25 + 10}px`,
                    animationDelay: `${i * 60}ms`
                  }} />
                ))}
              </div>
              <p className="text-sm animate-pulse">Transcribing...</p>
            </div>
          )}
          {transcript && (
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl px-4 py-3 border border-gray-200 dark:border-gray-600">
              <p className="text-sm whitespace-pre-wrap text-gray-900 dark:text-gray-100">{transcript}</p>
            </div>
          )}
        </div>
        <div className="flex gap-3">
          <label className="flex-1 flex items-center gap-3 px-4 py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 hover:border-blue-400 dark:hover:border-blue-500 transition-colors cursor-pointer">
            <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            <span className="text-sm text-gray-500 dark:text-gray-400">Choose audio file...</span>
            <input type="file" accept="audio/*" onChange={e => { const f = e.target.files?.[0]; if (f) sendAudio(f) }} className="hidden" />
          </label>
        </div>
      </>}
    </div>
  )
}
