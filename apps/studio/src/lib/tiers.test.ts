import { describe, it, expect } from 'vitest'
import {
  LEGACY_TIER_ALIASES,
  TIER_HIERARCHY,
  TOP_TIER,
  normalizeTier,
  tierAtLeast,
  tierNameKey,
  tierRank,
} from './tiers'

describe('the tier ladder', () => {
  it('tops out at premium', () => {
    expect(TOP_TIER).toBe('premium')
    expect(TIER_HIERARCHY.premium).toBe(3)
  })

  it('no longer lists the old top-tier name as a tier', () => {
    expect(TIER_HIERARCHY.madfam).toBeUndefined()
  })

  it('ranks the ladder in order', () => {
    expect(tierRank('guest')).toBeLessThan(tierRank('essentials'))
    expect(tierRank('essentials')).toBeLessThan(tierRank('pro'))
    expect(tierRank('pro')).toBeLessThan(tierRank('premium'))
  })
})

describe('deprecated tier names', () => {
  it('declares madfam as a permanent alias of premium', () => {
    expect(LEGACY_TIER_ALIASES.madfam).toBe('premium')
    // Predates this rename and must survive it.
    expect(LEGACY_TIER_ALIASES.basic).toBe('essentials')
  })

  it('normalises the alias forward', () => {
    expect(normalizeTier('madfam')).toBe('premium')
    expect(normalizeTier('basic')).toBe('essentials')
    expect(normalizeTier('premium')).toBe('premium')
  })

  it('seats the alias at the top of the ladder', () => {
    expect(tierRank('madfam')).toBe(tierRank('premium'))
  })

  it('accepts the alias on either side of a comparison', () => {
    expect(tierAtLeast('madfam', 'pro')).toBe(true)
    expect(tierAtLeast('madfam', 'premium')).toBe(true)
    expect(tierAtLeast('premium', 'madfam')).toBe(true)
    expect(tierAtLeast('pro', 'madfam')).toBe(false)
  })
})

describe('unknown and missing tiers', () => {
  it('fails closed at the bottom of the ladder', () => {
    expect(tierRank('platinum')).toBe(0)
    expect(tierAtLeast('platinum', 'pro')).toBe(false)
  })

  it.each([null, undefined, ''])('treats %p as no tier at all', (value) => {
    expect(tierRank(value)).toBe(0)
    expect(tierAtLeast(value, 'pro')).toBe(false)
    expect(tierAtLeast(value, 'guest')).toBe(true)
  })
})

describe('tierNameKey', () => {
  it('points at the canonical i18n key', () => {
    expect(tierNameKey('premium')).toBe('tier.name_premium')
    expect(tierNameKey('madfam')).toBe('tier.name_premium')
    expect(tierNameKey('pro')).toBe('tier.name_pro')
  })

  it('falls back to guest rather than producing a keyless lookup', () => {
    expect(tierNameKey(null)).toBe('tier.name_guest')
  })
})
