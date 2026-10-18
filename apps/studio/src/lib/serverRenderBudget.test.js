import { describe, it, expect } from 'vitest'
import { backgroundRendersAllowed } from './serverRenderBudget'

describe('backgroundRendersAllowed', () => {
  it('allows background renders only on an unlimited server-render budget', () => {
    expect(backgroundRendersAllowed({ backend_renders_per_hour: -1 })).toBe(true)
  })

  it('refuses them on every metered tier', () => {
    // apps/api/tiers.json: guest 10, essentials 30, pro 150
    for (const budget of [10, 30, 150]) {
      expect(backgroundRendersAllowed({ backend_renders_per_hour: budget })).toBe(false)
    }
  })

  it('reads the legacy renders_per_hour key', () => {
    expect(backgroundRendersAllowed({ renders_per_hour: -1 })).toBe(true)
    expect(backgroundRendersAllowed({ renders_per_hour: 30 })).toBe(false)
  })

  it('treats unknown limits as metered', () => {
    expect(backgroundRendersAllowed(null)).toBe(false)
    expect(backgroundRendersAllowed(undefined)).toBe(false)
    expect(backgroundRendersAllowed({})).toBe(false)
  })
})
