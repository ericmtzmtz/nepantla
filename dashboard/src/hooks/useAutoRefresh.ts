import { useEffect, useRef } from 'react'

export function useAutoRefresh(cb: () => void, intervalMs = 60000) {
  const saved = useRef(cb)
  saved.current = cb
  useEffect(() => {
    saved.current()
    const id = setInterval(() => saved.current(), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])
}
