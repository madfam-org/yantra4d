import { describe, it, expect } from 'vitest'
import { getCheckoutUrl, isPremiumTier } from './billing'

const planOf = (url: string) => new URL(url).searchParams.get('plan')

describe('getCheckoutUrl', () => {
  it('sends the registered plan id for pro', () => {
    expect(planOf(getCheckoutUrl('pro'))).toBe('yantra4d_pro')
  })

  it('sends the registered plan id for the top tier, which is NOT the tier name', () => {
    // The tier is `premium`; the SKU dhanam registered is still
    // `yantra4d_madfam`. Deriving the plan id from the tier name would point
    // checkout at a plan that does not exist.
    expect(planOf(getCheckoutUrl('premium'))).toBe('yantra4d_madfam')
  })

  it('defaults to pro', () => {
    expect(planOf(getCheckoutUrl())).toBe('yantra4d_pro')
  })

  it('carries the product and the optional identifiers', () => {
    const params = new URL(getCheckoutUrl('pro', 'u1', 'https://app/return')).searchParams
    expect(params.get('product')).toBe('yantra4d')
    expect(params.get('user_id')).toBe('u1')
    expect(params.get('return_url')).toBe('https://app/return')
  })

  it('omits the optional identifiers when they are not supplied', () => {
    const params = new URL(getCheckoutUrl('pro')).searchParams
    expect(params.has('user_id')).toBe(false)
    expect(params.has('return_url')).toBe(false)
  })
})

describe('isPremiumTier', () => {
  it('is true for the paid tiers', () => {
    expect(isPremiumTier('pro')).toBe(true)
    expect(isPremiumTier('premium')).toBe(true)
  })

  it('still accepts the deprecated top-tier name', () => {
    expect(isPremiumTier('madfam')).toBe(true)
  })

  it('is false below pro', () => {
    expect(isPremiumTier('guest')).toBe(false)
    expect(isPremiumTier('essentials')).toBe(false)
    expect(isPremiumTier('basic')).toBe(false)
  })
})
