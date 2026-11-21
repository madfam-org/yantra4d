/**
 * The free-tier Commons B-Rep quota, as the Studio sees it.
 *
 * Guest and essentials may re-render a Commons cartridge whose mode needs the
 * CadQuery or graph engine a limited number of times a day
 * (apps/api/services/engine/commons_render_quota.py, tiers.json
 * `commons_brep_renders_per_day`). When the server will not run one now it
 * answers 429 (quota spent) or 503 (free capacity full) with a stable
 * `error_code`; this module turns that into an error the render hook can
 * explain, with the reset time.
 */

/** API error codes for the free-tier Commons B-Rep quota (commons_render_quota.py). */
export const COMMONS_QUOTA_EXHAUSTED = 'commons_render_quota_exhausted'
export const COMMONS_CAPACITY_EXHAUSTED = 'commons_render_capacity_exhausted'
export const COMMONS_RENDER_BUSY = 'commons_render_busy'
const COMMONS_LIMIT_CODES = new Set([COMMONS_QUOTA_EXHAUSTED, COMMONS_CAPACITY_EXHAUSTED, COMMONS_RENDER_BUSY])

/**
 * A free-tier Commons B-Rep render the server would not run now: the daily
 * quota is spent (429), or free capacity is full (503). The message keeps the
 * `HTTP <status>` text every other render error carries, so callers that only
 * look at the message behave as before; callers that know this class read the
 * fields to say what happened and when it resets.
 */
export class CommonsRenderLimitError extends Error {
  readonly code: string
  readonly status: number
  readonly engine: string | null
  readonly limit: number | null
  readonly resetAt: string | null
  readonly retryAfterSeconds: number | null

  constructor(status: number, text: string, body: Record<string, unknown>) {
    super(`Render request failed (HTTP ${status}): ${text}`)
    this.name = 'CommonsRenderLimitError'
    this.status = status
    this.code = String(body.error_code)
    this.engine = typeof body.engine === 'string' ? body.engine : null
    const quota = (body.quota && typeof body.quota === 'object') ? body.quota as Record<string, unknown> : {}
    this.limit = typeof quota.limit === 'number' ? quota.limit : null
    this.resetAt = typeof quota.reset_at === 'string' ? quota.reset_at : null
    this.retryAfterSeconds = typeof body.retry_after_seconds === 'number' ? body.retry_after_seconds : null
  }
}

/** The quota error a failed render response carries, or null when it is another error. */
export function commonsLimitErrorFrom(status: number, text: string): CommonsRenderLimitError | null {
  if (status !== 429 && status !== 503) return null
  try {
    const body = JSON.parse(text)
    if (body && typeof body === 'object' && COMMONS_LIMIT_CODES.has(body.error_code)) {
      return new CommonsRenderLimitError(status, text, body)
    }
  } catch {
    // Not JSON: an ordinary error.
  }
  return null
}

/** Duck-typed so code under a mocked renderService can still recognise it. */
export function isCommonsLimitError(err: unknown): err is CommonsRenderLimitError {
  return err instanceof Error && err.name === 'CommonsRenderLimitError'
    && typeof (err as { code?: unknown }).code === 'string'
}

/**
 * When the refusal ends: `time` is the local clock time, `minutes`/`hours`
 * the rounded-up wait. Null when the server gave neither a reset time nor a
 * retry interval.
 */
export function describeReset(
  err: Pick<CommonsRenderLimitError, 'resetAt' | 'retryAfterSeconds'>,
  now: number = Date.now(),
): { time: string, minutes: number, hours: number } | null {
  let at: number | null = null
  if (err.resetAt) {
    const parsed = Date.parse(err.resetAt)
    if (!Number.isNaN(parsed)) at = parsed
  }
  if (at === null && typeof err.retryAfterSeconds === 'number') at = now + err.retryAfterSeconds * 1000
  if (at === null) return null
  const waitSeconds = Math.max(1, Math.round((at - now) / 1000))
  return {
    time: new Date(at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
    minutes: Math.max(1, Math.ceil(waitSeconds / 60)),
    hours: Math.max(1, Math.ceil(waitSeconds / 3600)),
  }
}
