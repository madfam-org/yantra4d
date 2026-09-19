import { describe, it, expect } from 'vitest'
import {
  CAROUSEL_LIMIT,
  EMPTY_FILTER,
  domainsOf,
  fillTemplate,
  filterItems,
  isFilterActive,
  partitionGallery,
  type GalleryItem,
} from './gallery'
import { modelUrl, modelledSlugs, usesMeshopt } from './models-manifest'

const item = (slug: string, extra: Partial<GalleryItem> = {}): GalleryItem => ({
  slug,
  name: slug.replace(/-/g, ' '),
  description: `${slug} description`,
  category: 'mechanical',
  thumbnail: `/projects/${slug}.webp`,
  isHyperobject: true,
  domain: 'industrial',
  ...extra,
})

describe('filterItems', () => {
  const items = [
    item('gridfinity', { category: 'storage', domain: 'household' }),
    item('gear-reducer'),
    item('voronoi', { category: 'art', isHyperobject: false, domain: '' }),
    item('slide-holder', { category: 'education', domain: 'medical' }),
  ]

  it('returns everything for the empty filter', () => {
    expect(filterItems(items, EMPTY_FILTER)).toHaveLength(4)
  })
  it('matches name, description and slug, case-insensitively, ignoring blank queries', () => {
    expect(filterItems(items, { ...EMPTY_FILTER, query: 'GRID' }).map((p) => p.slug)).toEqual(['gridfinity'])
    expect(filterItems(items, { ...EMPTY_FILTER, query: 'reducer description' })).toHaveLength(1)
    expect(filterItems(items, { ...EMPTY_FILTER, query: '   ' })).toHaveLength(4)
    expect(filterItems(items, { ...EMPTY_FILTER, query: 'zzzz' })).toHaveLength(0)
  })
  it('treats "commons" as hyperobjects-only and other categories literally', () => {
    expect(filterItems(items, { ...EMPTY_FILTER, category: 'commons' })).toHaveLength(3)
    expect(filterItems(items, { ...EMPTY_FILTER, category: 'art' }).map((p) => p.slug)).toEqual(['voronoi'])
  })
  it('composes category and domain', () => {
    expect(filterItems(items, { query: '', category: 'commons', domain: 'medical' }).map((p) => p.slug)).toEqual(['slide-holder'])
  })
  it('knows when a filter is active', () => {
    expect(isFilterActive(EMPTY_FILTER)).toBe(false)
    expect(isFilterActive({ ...EMPTY_FILTER, query: ' x' })).toBe(true)
    expect(isFilterActive({ ...EMPTY_FILTER, domain: 'medical' })).toBe(true)
  })
})

describe('partitionGallery', () => {
  const modelled = new Set(['gridfinity', 'voronoi'])
  const items = [
    item('a-hyper-unmodelled'),
    item('voronoi', { isHyperobject: false }),
    item('gridfinity'),
    item('plain', { isHyperobject: false }),
  ]

  it('puts modelled hyperobjects first, then modelled others, then unmodelled hyperobjects; plain unmodelled go to the grid', () => {
    const { carousel, grid } = partitionGallery(items, modelled)
    expect(carousel.map((p) => p.slug)).toEqual(['gridfinity', 'voronoi', 'a-hyper-unmodelled'])
    expect(grid.map((p) => p.slug)).toEqual(['plain'])
  })
  it('caps the carousel and never shows an item in both', () => {
    const many = Array.from({ length: 60 }, (_, i) => item(`h${i}`))
    const { carousel, grid } = partitionGallery(many, new Set(), CAROUSEL_LIMIT)
    expect(carousel).toHaveLength(CAROUSEL_LIMIT)
    expect(grid).toHaveLength(60 - CAROUSEL_LIMIT)
    const inBoth = carousel.filter((c) => grid.some((g) => g.slug === c.slug))
    expect(inBoth).toEqual([])
  })
  it('keeps the grid in original order', () => {
    const { grid } = partitionGallery(items, new Set(), 1)
    expect(grid.map((p) => p.slug)).toEqual(['voronoi', 'gridfinity', 'plain'])
  })
})

describe('fillTemplate / domainsOf', () => {
  it('fills known keys and leaves unknown ones visible', () => {
    expect(fillTemplate('Showing {shown} of {total}', { shown: 24, total: 502 })).toBe('Showing 24 of 502')
    expect(fillTemplate('{nope} {shown}', { shown: 1 })).toBe('{nope} 1')
  })
  it('lists distinct domains in first-appearance order, skipping blanks', () => {
    expect(domainsOf([item('a', { domain: 'medical' }), item('b', { domain: '' }), item('c'), item('d', { domain: 'medical' })])).toEqual(['medical', 'industrial'])
  })
})

describe('models manifest reader', () => {
  const v1 = { generated: 'x', models: [{ slug: 'gridfinity', size: 100 }] }
  const v2 = {
    version: 2,
    generated: 'y',
    models: [
      { slug: 'gridfinity', size: 10, lod1: { file: 'gridfinity.lod1.glb', bytes: 10 }, lod0: { file: 'gridfinity.lod0.glb', bytes: 50 } },
      { slug: 'gears', size: 12, lod1: { file: 'gears.lod1.glb', bytes: 12 } },
      { slug: 'legacy', size: 99 },
    ],
  }
  it('lists slugs from either shape and tolerates garbage', () => {
    expect(modelledSlugs(v1)).toEqual(['gridfinity'])
    expect(modelledSlugs(v2)).toEqual(['gridfinity', 'gears', 'legacy'])
    expect(modelledSlugs(null)).toEqual([])
    expect(modelledSlugs({ models: 'nope' } as any)).toEqual([])
  })
  it('resolves the requested LOD with sensible fallbacks', () => {
    expect(modelUrl(v1, 'gridfinity')).toBe('/models/gridfinity.glb')
    expect(modelUrl(v2, 'gridfinity')).toBe('/models/gridfinity.lod1.glb')
    expect(modelUrl(v2, 'gridfinity', 'lod0')).toBe('/models/gridfinity.lod0.glb')
    expect(modelUrl(v2, 'gears', 'lod0')).toBe('/models/gears.lod1.glb')
    expect(modelUrl(v2, 'legacy')).toBe('/models/legacy.glb')
    expect(modelUrl(v2, 'missing')).toBeNull()
  })
  it('knows when the decoder is needed', () => {
    expect(usesMeshopt(v1)).toBe(false)
    expect(usesMeshopt(v2)).toBe(true)
  })
})
