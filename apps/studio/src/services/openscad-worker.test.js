import { describe, it, expect } from 'vitest'
import { detectPhase, isLogWorthy } from '../lib/openscad-phases'

describe('detectPhase', () => {
  it('returns "compiling" for lines containing Compiling', () => {
    expect(detectPhase('Compiling design (CSG Tree)...')).toBe('compiling')
  })

  it('returns "cgal" for lines containing CGAL', () => {
    expect(detectPhase('CGAL cache miss')).toBe('cgal')
  })

  it('returns "rendering" for lines containing Rendering', () => {
    expect(detectPhase('Rendering Polygon Mesh...')).toBe('rendering')
  })

  it('returns "rendering" for lines containing Geometries', () => {
    expect(detectPhase('Geometries in cache: 5')).toBe('rendering')
  })

  it('returns "geometry" for lines containing Parsing', () => {
    expect(detectPhase('Parsing design...')).toBe('geometry')
  })

  it('returns null for unrecognized lines', () => {
    expect(detectPhase('some random output')).toBeNull()
  })

  it('returns null for empty string', () => {
    expect(detectPhase('')).toBeNull()
  })
})

describe('isLogWorthy', () => {
  it.each([
    'Compiling design',
    'Parsing design',
    'CGAL cache miss',
    'Geometries in cache',
    'Rendering Polygon Mesh',
    'Total rendering time: 5s',
    'Simple: yes',
  ])('returns true for "%s"', (line) => {
    expect(isLogWorthy(line)).toBe(true)
  })

  it('returns false for noise lines', () => {
    expect(isLogWorthy('some random output')).toBe(false)
    expect(isLogWorthy('')).toBe(false)
    expect(isLogWorthy('WARNING: unused variable')).toBe(false)
  })
})
