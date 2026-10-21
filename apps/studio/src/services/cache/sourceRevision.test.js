import { describe, it, expect, beforeEach, vi } from 'vitest'

describe('sourceRevision', () => {
  beforeEach(() => vi.resetModules())

  it('starts at 0 and counts saves per project', async () => {
    const { sourceRevision, bumpSourceRevision } = await import('./sourceRevision')
    expect(sourceRevision('fork')).toBe(0)
    expect(bumpSourceRevision('fork')).toBe(1)
    expect(bumpSourceRevision('fork')).toBe(2)
    expect(sourceRevision('fork')).toBe(2)
    expect(sourceRevision('other')).toBe(0)
  })

  it('treats a missing project as one bucket', async () => {
    const { sourceRevision, bumpSourceRevision } = await import('./sourceRevision')
    bumpSourceRevision(null)
    expect(sourceRevision(undefined)).toBe(1)
  })
})
