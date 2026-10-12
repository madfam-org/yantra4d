import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { PUBLIC_PAGE_PATHS, buildRobots, buildSitemap, englishPath } from './crawl'

const LANDING = resolve(__dirname, '..', '..')
const PAGES_DIR = resolve(LANDING, 'src', 'pages')

function astroPages(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) return astroPages(full)
    return name.endsWith('.astro') ? [relative(PAGES_DIR, full)] : []
  })
}

/** `concepts/commons.astro` -> `/concepts/commons/`, `en/index.astro` -> `/en/`. */
function routeOf(file: string): string {
  const noExt = file.replace(/\.astro$/, '').replace(/(^|\/)index$/, '')
  return noExt ? `/${noExt}/` : '/'
}

describe('crawl files', () => {
  it('lists every static page under src/pages, in both locales', () => {
    const routes = astroPages(PAGES_DIR)
    expect(routes.some((f) => f.includes('['))).toBe(false)
    const expected = PUBLIC_PAGE_PATHS.flatMap((p) => [p, englishPath(p)]).sort()
    expect(routes.map(routeOf).sort()).toEqual(expected)
  })

  it('builds a sitemap of absolute URLs on the landing host only', () => {
    const xml = buildSitemap('https://yantra4d.com')
    expect(xml.startsWith('<?xml version="1.0" encoding="UTF-8"?>')).toBe(true)
    const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1])
    expect(locs).toHaveLength(PUBLIC_PAGE_PATHS.length * 2)
    expect(locs).toContain('https://yantra4d.com/')
    expect(locs).toContain('https://yantra4d.com/en/concepts/commons/')
    for (const loc of locs) expect(new URL(loc).host).toBe('yantra4d.com')
    expect(xml).toContain('hreflang="x-default" href="https://yantra4d.com/concepts/hyperobjects/"')
  })

  it('normalises a trailing slash on the origin', () => {
    expect(buildSitemap('https://yantra4d.com/')).toBe(buildSitemap('https://yantra4d.com'))
    expect(buildRobots('https://yantra4d.com/')).toBe(buildRobots('https://yantra4d.com'))
  })

  it('builds robots.txt that allows all and names the sitemap', () => {
    const robots = buildRobots('https://yantra4d.com')
    expect(robots).toMatch(/^User-agent: \*$/m)
    expect(robots).toMatch(/^Allow: \/$/m)
    expect(robots).toMatch(/^Sitemap: https:\/\/yantra4d\.com\/sitemap\.xml$/m)
    expect(robots).not.toMatch(/Disallow/)
  })

  it('ships a public llms.txt that links pricing and holds no prices', () => {
    const llms = readFileSync(resolve(LANDING, 'public', 'llms.txt'), 'utf8')
    expect(llms).toMatch(/^# Yantra4D\n/)
    expect(llms).toMatch(/^> /m)
    expect(llms).toMatch(/^## Links$/m)
    expect(llms).toContain('https://yantra4d.com/en/#pricing')
    expect(llms).not.toMatch(/\$\s?\d|MXN|USD/)
    expect(llms).not.toMatch(/admin\.|api\.yantra4d|localhost/)
  })

  it('nginx serves crawl files as files and 404s missing ones', () => {
    const conf = readFileSync(resolve(LANDING, 'nginx.conf'), 'utf8')
    const crawl = conf.indexOf('location ~* \\.(txt|xml)$')
    expect(crawl).toBeGreaterThan(-1)
    const block = conf.slice(crawl, conf.indexOf('}', crawl))
    expect(block).toContain('try_files $uri =404;')
    // An add_header here would drop the inherited server-level security headers.
    expect(block).not.toContain('add_header')
  })
})
