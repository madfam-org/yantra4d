/**
 * WebSocket client with auto-reconnect and SSE fallback.
 *
 * Usage:
 *   const ws = createWebSocket('/api/ws/render/session-123')
 *   ws.onMessage((data) => console.log(data))
 *   ws.send({ action: 'cancel' })
 *   ws.close()
 */

interface WebSocketMessage {
  type: string
  [key: string]: unknown
}

interface WebSocketClientOptions {
  /** Max reconnect attempts before giving up (default: 5) */
  maxReconnectAttempts?: number
  /** Initial reconnect delay in ms (default: 1000, doubles each attempt) */
  reconnectDelay?: number
  /** Heartbeat interval in ms (default: 30000) */
  heartbeatInterval?: number
  /** Called when connection opens */
  onOpen?: () => void
  /** Called when connection closes permanently */
  onClose?: () => void
  /** Called on connection error */
  onError?: (error: Event) => void
}

interface WebSocketClient {
  send: (data: Record<string, unknown>) => void
  onMessage: (handler: (data: WebSocketMessage) => void) => void
  close: () => void
  readonly connected: boolean
}

/**
 * Create a WebSocket connection with auto-reconnect and exponential backoff.
 * Returns null if WebSocket is not supported by the browser.
 */
export function createWebSocket(
  path: string,
  options: WebSocketClientOptions = {},
): WebSocketClient | null {
  if (typeof WebSocket === 'undefined') return null

  const {
    maxReconnectAttempts = 5,
    reconnectDelay = 1000,
    heartbeatInterval = 30000,
    onOpen,
    onClose,
    onError,
  } = options

  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  let messageHandlers: ((data: WebSocketMessage) => void)[] = []
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let intentionallyClosed = false

  function getUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}${path}`
  }

  function connect() {
    try {
      ws = new WebSocket(getUrl())
    } catch {
      return
    }

    ws.onopen = () => {
      reconnectAttempts = 0
      startHeartbeat()
      onOpen?.()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage
        // Don't forward heartbeat/pong to handlers
        if (data.type === 'pong' || data.type === 'heartbeat') return
        messageHandlers.forEach(handler => handler(data))
      } catch {
        // Non-JSON message — ignore
      }
    }

    ws.onerror = (event) => {
      onError?.(event)
    }

    ws.onclose = () => {
      stopHeartbeat()
      if (!intentionallyClosed && reconnectAttempts < maxReconnectAttempts) {
        const delay = reconnectDelay * Math.pow(2, reconnectAttempts)
        reconnectAttempts++
        setTimeout(connect, delay)
      } else if (intentionallyClosed || reconnectAttempts >= maxReconnectAttempts) {
        onClose?.()
      }
    }
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'ping' }))
      }
    }, heartbeatInterval)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  // Initial connection
  connect()

  return {
    send(data: Record<string, unknown>) {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data))
      }
    },
    onMessage(handler: (data: WebSocketMessage) => void) {
      messageHandlers.push(handler)
    },
    close() {
      intentionallyClosed = true
      stopHeartbeat()
      ws?.close()
      messageHandlers = []
    },
    get connected() {
      return ws?.readyState === WebSocket.OPEN
    },
  }
}
