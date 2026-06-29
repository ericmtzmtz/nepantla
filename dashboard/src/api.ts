const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function apiGet(path: string) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path}: ${res.status}`)
  return res.json()
}

export async function apiPost(path: string, body?: unknown) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`POST ${path}: ${res.status}`)
  return res.json()
}

export async function apiPut(path: string, body: unknown) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path}: ${res.status}`)
  return res.json()
}

export async function apiDelete(path: string) {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
  if (!res.ok && res.status !== 404) throw new Error(`DELETE ${path}: ${res.status}`)
  return res.status === 204 ? {} : res.json()
}

export async function apiPatch(path: string, body?: unknown) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`PATCH ${path}: ${res.status}`)
  return res.json()
}
