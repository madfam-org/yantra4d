import { describe, it, expect } from 'vitest'
import {
  COMMONS_CAPACITY_EXHAUSTED,
  COMMONS_QUOTA_EXHAUSTED,
  COMMONS_RENDER_BUSY,
  commonsLimitErrorFrom,
  describeReset,
  isCommonsLimitError,
} from './commonsQuota'

const exhausted = {
  status: 'error',
  error: 'You have used all 3 free CadQuery re-renders of Commons cartridges for today.',
  error_code: COMMONS_QUOTA_EXHAUSTED,
  quota: { scope: 'commons_brep', limit: 3, remaining: 0, window: 'day', reset_at: '2026-11-21T18:00:00Z' },
  retry_after_seconds: 7200,
  tier: 'guest',
  engine: 'cadquery',
}

describe('commonsLimitErrorFrom', () => {
  it('reads the API 429 into a typed error that keeps the HTTP text', () => {
    const err = commonsLimitErrorFrom(429, JSON.stringify(exhausted))
    expect(err).not.toBeNull()
    expect(isCommonsLimitError(err)).toBe(true)
    expect(err!.message).toContain('HTTP 429')
    expect(err!.code).toBe(COMMONS_QUOTA_EXHAUSTED)
    expect(err!.limit).toBe(3)
    expect(err!.engine).toBe('cadquery')
    expect(err!.resetAt).toBe('2026-11-21T18:00:00Z')
    expect(err!.retryAfterSeconds).toBe(7200)
  })

  it.each([COMMONS_CAPACITY_EXHAUSTED, COMMONS_RENDER_BUSY])('reads the 503 %s', code => {
    const err = commonsLimitErrorFrom(503, JSON.stringify({ error_code: code, retry_after_seconds: 30, engine: 'graph' }))
    expect(err!.code).toBe(code)
    expect(err!.limit).toBeNull()
  })

  it('leaves every other error alone', () => {
    expect(commonsLimitErrorFrom(429, JSON.stringify({ error_code: 'rate_limit_exceeded' }))).toBeNull()
    expect(commonsLimitErrorFrom(429, 'Too Many Requests')).toBeNull()
    expect(commonsLimitErrorFrom(403, JSON.stringify(exhausted))).toBeNull()
    expect(isCommonsLimitError(new Error('HTTP 429'))).toBe(false)
  })
})

describe('describeReset', () => {
  const now = Date.parse('2026-11-21T16:00:00Z')

  it('rounds the wait up to hours and minutes', () => {
    const r = describeReset({ resetAt: '2026-11-21T18:00:00Z', retryAfterSeconds: null }, now)
    expect(r!.hours).toBe(2)
    expect(r!.minutes).toBe(120)
    expect(r!.time).toBeTruthy()
  })

  it('falls back to the retry interval', () => {
    expect(describeReset({ resetAt: null, retryAfterSeconds: 30 }, now)!.minutes).toBe(1)
  })

  it('is null without either', () => {
    expect(describeReset({ resetAt: null, retryAfterSeconds: null }, now)).toBeNull()
  })
})
