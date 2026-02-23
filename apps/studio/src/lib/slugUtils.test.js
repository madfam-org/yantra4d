import { describe, it, expect } from 'vitest'
import { validateSlug, sanitizeSlug } from './slugUtils'

describe('validateSlug', () => {
  it('returns null for valid slug', () => {
    expect(validateSlug('my-project')).toBeNull()
    expect(validateSlug('project_123')).toBeNull()
    expect(validateSlug('abc')).toBeNull()
  })

  it('returns error for empty slug', () => {
    expect(validateSlug('')).toBe('Slug is required')
    expect(validateSlug(null)).toBe('Slug is required')
    expect(validateSlug(undefined)).toBe('Slug is required')
  })

  it('returns error for invalid format', () => {
    expect(validateSlug('AB')).toContain('Must be')
    expect(validateSlug('-start')).toContain('Must be')
    expect(validateSlug('end-')).toContain('Must be')
    expect(validateSlug('a')).toContain('Must be') // too short
  })
})

describe('sanitizeSlug', () => {
  it('lowercases input', () => {
    expect(sanitizeSlug('MyProject')).toBe('myproject')
  })

  it('replaces invalid chars with hyphens', () => {
    expect(sanitizeSlug('my project!')).toBe('my-project')
  })

  it('collapses multiple hyphens', () => {
    expect(sanitizeSlug('a---b')).toBe('a-b')
  })

  it('strips leading/trailing hyphens', () => {
    expect(sanitizeSlug('-test-')).toBe('test')
  })

  it('truncates to 50 chars', () => {
    const long = 'a'.repeat(60)
    expect(sanitizeSlug(long).length).toBe(50)
  })
})
