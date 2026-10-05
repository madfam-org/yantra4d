/**
 * The pravara motion stream as a PoseSource: `GET {base}/v1/machines/{id}/motion`,
 * `pravara.machine-motion/1`. A fetch-based Server-Sent Events reader, because the
 * stream needs an Authorization header (Janua bearer or API key, scope
 * `pravara-mes:read`) and EventSource cannot send one. The token never goes in the URL.
 *
 * Contract facts this reader relies on (W4-P7MES):
 * - framing `id: <seq>\nevent: <type>\ndata: <one-line JSON>\n\n`, plus `: keepalive`
 *   comments;
 * - every connection starts with a fresh `snapshot` at seq 1 (no replay; Last-Event-ID
 *   is ignored), then seq rises by 1 per event, gap-free;
 * - each `motion` event is the full merged state, so a dropped event only lowers the rate;
 * - errors are JSON `{"error": code}`: 401, 403, 404 `machine_not_found`,
 *   503 `motion_stream_disabled` (the default) or `motion_stream_unavailable`.
 */
import {
  type MachineMotion,
  type MotionEvent,
  MotionStreamError,
  motionAxes,
  parseMotionEvent,
} from './machineMotion'
import { BasePoseSource } from './poseSource'

export interface SsePoseSourceOptions {
  /** pravara-api origin, e.g. https://api.pravara.example (no trailing slash needed). */
  baseUrl: string
  /** The pravara machine UUID. */
  machineId: string
  /** The bearer token or API key for the Authorization header; null sends none. */
  getToken?: () => Promise<string | null> | string | null
  fetchImpl?: typeof fetch
  /** Reconnect backoff after a dropped stream or a 503 unavailable (ms). */
  reconnectMinMs?: number
  reconnectMaxMs?: number
  now?: () => number
}

export interface StreamStats {
  connections: number
  events: number
  motionEvents: number
  /** Sum of the server's `dropped` counts seen. */
  dropped: number
  /** seq gaps seen (a contract violation; should stay 0). */
  seqGaps: number
  /** Latest `sent_at_ms − sampled_at_ms` and `now − sampled_at_ms` (different clocks: NTP-grade). */
  lastServerLatencyMs: number | null
  lastClientLatencyMs: number | null
  lastSeq: number | null
}

/** Errors after which reconnecting cannot help. */
const FATAL_CODES = new Set(['unauthorized', 'forbidden', 'missing_scope', 'machine_not_found', 'motion_stream_disabled'])

/** Incremental SSE parser (WHATWG HTML §9.2.6, the subset this stream uses). */
export class SseParser {
  private buffer = ''
  private id = ''
  private event = ''
  private data: string[] = []

  constructor(private readonly onEvent: (e: { id: string; event: string; data: string }) => void) {}

  push(chunk: string): void {
    this.buffer += chunk
    let nl: number
    while ((nl = this.buffer.search(/\r\n|\r|\n/)) >= 0) {
      const line = this.buffer.slice(0, nl)
      const sep = this.buffer.startsWith('\r\n', nl) ? 2 : 1
      this.buffer = this.buffer.slice(nl + sep)
      this.line(line)
    }
  }

  private line(line: string): void {
    if (line === '') {
      if (this.data.length) this.onEvent({ id: this.id, event: this.event || 'message', data: this.data.join('\n') })
      this.event = ''
      this.data = []
      return
    }
    if (line.startsWith(':')) return // a comment: `: keepalive`
    const colon = line.indexOf(':')
    const field = colon < 0 ? line : line.slice(0, colon)
    let value = colon < 0 ? '' : line.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'data') this.data.push(value)
    else if (field === 'event') this.event = value
    else if (field === 'id' && !value.includes('\0')) this.id = value
  }
}

export class SsePoseSource extends BasePoseSource {
  readonly kind = 'pravara-sse'
  readonly stats: StreamStats = {
    connections: 0, events: 0, motionEvents: 0, dropped: 0, seqGaps: 0,
    lastServerLatencyMs: null, lastClientLatencyMs: null, lastSeq: null,
  }
  private abort: AbortController | null = null
  private closed = false
  private backoff: number
  private retryTimer: ReturnType<typeof setTimeout> | null = null
  private readonly opts: Required<Omit<SsePoseSourceOptions, 'getToken'>> & Pick<SsePoseSourceOptions, 'getToken'>

  constructor(options: SsePoseSourceOptions) {
    super()
    if (!/^[0-9a-fA-F-]{8,64}$/.test(options.machineId)) {
      throw new MotionStreamError(`machine id ${JSON.stringify(options.machineId)} is not a UUID`)
    }
    this.opts = {
      fetchImpl: options.fetchImpl ?? globalThis.fetch.bind(globalThis),
      reconnectMinMs: options.reconnectMinMs ?? 1000,
      reconnectMaxMs: options.reconnectMaxMs ?? 30000,
      now: options.now ?? Date.now,
      ...options,
    }
    this.backoff = this.opts.reconnectMinMs
  }

  get url(): string {
    return `${this.opts.baseUrl.replace(/\/+$/, '')}/v1/machines/${encodeURIComponent(this.opts.machineId)}/motion`
  }

  /** Open the stream (and keep it open, with backoff, until close or a fatal error). */
  start(): void {
    if (this.closed || this.abort) return
    void this.connect()
  }

  close(): void {
    this.closed = true
    if (this.retryTimer) clearTimeout(this.retryTimer)
    this.abort?.abort()
    this.abort = null
    super.close()
  }

  private scheduleReconnect(reason: string): void {
    if (this.closed) return
    this.emitState('connecting', `reconnecting in ${this.backoff} ms: ${reason}`)
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null
      void this.connect()
    }, this.backoff)
    this.backoff = Math.min(this.backoff * 2, this.opts.reconnectMaxMs)
  }

  private async connect(): Promise<void> {
    if (this.closed) return
    this.abort = new AbortController()
    this.emitState('connecting')
    const headers: Record<string, string> = { Accept: 'text/event-stream' }
    const token = this.opts.getToken ? await this.opts.getToken() : null
    if (token) headers.Authorization = `Bearer ${token}`
    let response: Response
    try {
      response = await this.opts.fetchImpl(this.url, { headers, signal: this.abort.signal, cache: 'no-store' })
    } catch (err) {
      this.abort = null
      if (this.closed) return
      this.scheduleReconnect(err instanceof Error ? err.message : String(err))
      return
    }
    if (!response.ok || !response.body) {
      let code = `http_${response.status}`
      try {
        const body = await response.json()
        if (body && typeof body.error === 'string') code = body.error
      } catch {
        /* a non-JSON error body keeps the HTTP code */
      }
      this.abort = null
      if (response.status === 401 || response.status === 403 || response.status === 404 || FATAL_CODES.has(code)) {
        this.emitState('error', `${response.status} ${code}`)
        return
      }
      this.scheduleReconnect(`${response.status} ${code}`)
      return
    }
    this.stats.connections++
    let expected = 1 // every connection starts with a snapshot at seq 1
    const parser = new SseParser(({ id, event, data }) => {
      let parsed: MotionEvent
      try {
        parsed = parseMotionEvent(event, data, id)
      } catch (err) {
        this.emitState('error', err instanceof Error ? err.message : String(err))
        return
      }
      if (parsed.seq !== expected) this.stats.seqGaps++
      expected = parsed.seq + 1
      this.handle(parsed)
    })
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        parser.push(value)
      }
    } catch (err) {
      if (this.closed) return
      this.abort = null
      this.scheduleReconnect(err instanceof Error ? err.message : String(err))
      return
    }
    this.abort = null
    if (!this.closed) this.scheduleReconnect('the stream ended')
  }

  private handle(e: MotionEvent): void {
    this.stats.events++
    this.stats.lastSeq = e.seq
    this.stats.dropped += e.dropped ?? 0
    if (this.lastState !== 'live') {
      this.backoff = this.opts.reconnectMinMs
      this.emitState('live')
    }
    if (e.type === 'snapshot') {
      this.emitStatus(e.status)
      if (e.motion) this.motion(e.motion, e.seq, e.sent_at_ms)
    } else if (e.type === 'status') {
      this.emitStatus(e)
    } else {
      this.stats.motionEvents++
      this.motion(e, e.seq, e.sent_at_ms)
    }
  }

  private motion(m: MachineMotion, seq: number, sentAtMs: number): void {
    if (m.sampled_at_ms !== null && m.sampled_at_ms !== undefined) {
      this.stats.lastServerLatencyMs = sentAtMs - m.sampled_at_ms
      this.stats.lastClientLatencyMs = this.opts.now() - m.sampled_at_ms
    }
    this.emitPose({ axes: motionAxes(m), motion: m, seq, sampledAtMs: m.sampled_at_ms ?? undefined })
  }
}
