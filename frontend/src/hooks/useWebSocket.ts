import { useEffect, useRef, useCallback } from 'react'

type MessageHandler = (msg: { type: string; data?: unknown }) => void

export function useWebSocket(url: string, onMessage: MessageHandler) {
  const wsRef       = useRef<WebSocket | null>(null)
  const handlerRef  = useRef(onMessage)
  const retryRef    = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef  = useRef(true)

  handlerRef.current = onMessage

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        handlerRef.current(data)
      } catch { /* ignore malformed frames */ }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      // Auto-reconnect after 3 s
      retryRef.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => ws.close()
  }, [url])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return wsRef
}
