import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { buildLlms, buildRobots, buildSitemap, catalogSlugs, CATALOG_PATHS } from './crawlFiles.js'

const CATALOG = JSON.parse(
  readFileSync(join(__dirname, '..', '..', '..', '..', 'docs', 'commons-catalog.json'), 'utf8'),
)
const ORIGIN = 'https://app.yantra4d.com'

describe('Studio crawl files (geo-stab V1 F10)', () => {
  it('lists the catalog routes and one /project/<slug> per public cartridge', () => {
    const slugs = catalogSlugs(CATALOG)
    expect(slugs.length).toBe(CATALOG.counts.cartridges)
    const xml = buildSitemap(ORIGIN, slugs)
    const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1])
    expect(locs.length).toBe(slugs.length + CATALOG_PATHS.length)
    expect(locs).toContain(`${ORIGIN}/`)
    expect(locs).toContain(`${ORIGIN}/projects`)
    expect(locs).toContain(`${ORIGIN}/project/gridfinity`)
    // Every URL is on this host: a sitemap may not list another origin.
    expect(locs.every((loc) => loc.startsWith(`${ORIGIN}/`))).toBe(true)
    expect(new Set(locs).size).toBe(locs.length)
    expect(xml.startsWith('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')).toBe(true)
  })

  it('never lists a client-private cartridge', () => {
    const slugs = catalogSlugs(CATALOG)
    expect(slugs).not.toContain('tablaco')
    expect(slugs).not.toContain('tablaco-v2')
  })

  it('refuses an empty or malformed catalog instead of shipping an empty sitemap', () => {
    expect(() => catalogSlugs({ cartridges: [] })).toThrow(/no cartridges/)
    expect(() => catalogSlugs({})).toThrow(/no cartridges/)
    expect(() => catalogSlugs({ cartridges: [{ slug: '../etc' }] })).toThrow(/invalid slug/)
  })

  it('allows the pages, keeps crawlers off /api/ and /static/, and advertises the sitemap', () => {
    const robots = buildRobots(`${ORIGIN}/`)
    expect(robots).toContain('User-agent: *\nAllow: /\n')
    expect(robots).toContain('Disallow: /api/\n')
    expect(robots).toContain('Disallow: /static/\n')
    expect(robots).toContain(`Sitemap: ${ORIGIN}/sitemap.xml\n`)
    expect(robots).not.toMatch(/Disallow: \/(project|projects)?\s*$/m)
  })

  it('points llms.txt at the API and landing indexes', () => {
    const slugs = catalogSlugs(CATALOG)
    const llms = buildLlms(ORIGIN, slugs)
    expect(llms.startsWith('# Yantra4D Studio\n')).toBe(true)
    expect(llms).toContain('(https://api.yantra4d.com/api/llms.txt)')
    expect(llms).toContain('(https://yantra4d.com/llms.txt)')
    expect(llms).toContain(`${slugs.length} public cartridges`)
    expect(llms).toContain(`(${ORIGIN}/sitemap.xml)`)
  })
})
