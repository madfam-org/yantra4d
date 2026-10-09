import { describe, it, expect, beforeEach } from 'vitest'
import { RUM_EVENT, RUM_SESSION_KEY, buildTierBeacon, sendTierBeacon } from './rum'

describe('tier beacon', () => {
  beforeEach(() => {
    sessionStorage.clear()
    document.documentElement.setAttribute('data-tier', 'lite')
    document.documentElement.setAttribute('data-tier-source', 'signals')
    document.documentElement.lang = 'en'
  })

  it('carries the tier, its source, the language and the path — and nothing personal', () => {
    const b = buildTierBeacon()
    expect(b).toEqual({
      project: 'landing',
      event: RUM_EVENT,
      data: { tier: 'lite', source: 'signals', lang: 'en', path: '/' },
    })
    expect(JSON.stringify(b)).not.toMatch(/@|sub|email|token/)
  })

  it('does nothing when disabled', () => {
    const sent: string[] = []
    expect(sendTierBeacon({ endpoint: '/x', enabled: false, send: (u) => (sent.push(u), true) })).toBe(false)
    expect(sent).toEqual([])
  })

  it('sends once per session', () => {
    const sent: string[] = []
    const send = (u: string, body: string) => (sent.push(body), true)
    expect(sendTierBeacon({ endpoint: '/api/analytics/track', enabled: true, send })).toBe(true)
    expect(sendTierBeacon({ endpoint: '/api/analytics/track', enabled: true, send })).toBe(false)
    expect(sent).toHaveLength(1)
    expect(JSON.parse(sent[0]).data.tier).toBe('lite')
    expect(sessionStorage.getItem(RUM_SESSION_KEY)).toBe('1')
  })

  it('does not mark the session when the transport refuses, so a later attempt can retry', () => {
    expect(sendTierBeacon({ endpoint: '/x', enabled: true, send: () => false })).toBe(false)
    expect(sessionStorage.getItem(RUM_SESSION_KEY)).toBeNull()
  })

  it('survives a storage that throws', () => {
    const broken = { getItem: () => { throw new Error('SecurityError') }, setItem: () => {} } as unknown as Storage
    expect(sendTierBeacon({ endpoint: '/x', enabled: true, storage: broken, send: () => true })).toBe(false)
  })
})
