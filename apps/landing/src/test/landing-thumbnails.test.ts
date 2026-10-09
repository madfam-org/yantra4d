/**
 * Thumbnail budget lane. Every card and the still-tier strip load
 * `public/projects/<slug>.webp`; on a full scroll they are most of the still
 * tier's bytes, and one 387 KB PNG was enough to break that budget. The
 * optimizer (`scripts/dev/optimize-landing-thumbnails.mjs`) fixes files; this
 * test keeps them fixed and keeps the generated list pointing at what exists.
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { audit, loadBudgets } from '../../../../scripts/dev/optimize-landing-thumbnails.mjs'
import { PROJECTS } from '../data/projects'

const REPO = path.resolve(__dirname, '..', '..', '..', '..')
const PUBLIC = path.join(REPO, 'apps', 'landing', 'public')
const THUMBS = path.join(PUBLIC, 'projects')

describe('landing thumbnails', () => {
  const budgets = loadBudgets(REPO)
  const found = audit(THUMBS, budgets)

  it('has a budget to enforce', () => {
    expect(budgets.thumbnailBytes).toBeGreaterThan(0)
    expect(found.webps.length).toBeGreaterThan(100)
  })

  it('ships no PNG thumbnail (WebP siblings replace them)', () => {
    expect(found.pngs).toEqual([])
  })

  it(`keeps every thumbnail within images.thumbnailBytes`, () => {
    expect(found.over.map((o) => `${o.file} ${o.bytes} B`)).toEqual([])
  })

  it('every generated thumbnail path points at an existing webp or svg', () => {
    const missing: string[] = []
    const wrongType: string[] = []
    for (const p of PROJECTS) {
      if (!/\.(webp|svg)$/.test(p.thumbnail)) wrongType.push(`${p.slug}: ${p.thumbnail}`)
      if (!fs.existsSync(path.join(PUBLIC, p.thumbnail.replace(/^\//, '')))) missing.push(`${p.slug}: ${p.thumbnail}`)
    }
    expect(wrongType).toEqual([])
    expect(missing).toEqual([])
  })
})
