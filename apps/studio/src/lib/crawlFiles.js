/**
 * Crawl files for app.yantra4d.com: `/robots.txt`, `/sitemap.xml`, `/llms.txt`.
 *
 * Built once per image by the `crawl-files` plugin in vite.config.js, from
 * `docs/commons-catalog.json` (the generated list of public cartridges, kept in
 * step with the commons pin by its CI drift gate), the same way the landing
 * builds its own sitemap at build time. nginx serves the three as exact-match
 * locations, so a missing file is a real 404 and never the SPA's index.html.
 *
 * A sitemap may only list URLs on its own host: this one carries the Studio's
 * catalog routes and one `/project/<slug>` page per public cartridge. The
 * landing's pages are in https://yantra4d.com/sitemap.xml.
 *
 * Pure functions, no I/O: the plugin reads the catalog and writes the assets.
 */

export const DEFAULT_STUDIO_ORIGIN = 'https://app.yantra4d.com'
export const LANDING_ORIGIN = 'https://yantra4d.com'
export const API_ORIGIN = 'https://api.yantra4d.com'

/** Catalog routes, besides one page per cartridge. `/` and `/projects` both
 *  render the catalog (ProjectsView). */
export const CATALOG_PATHS = ['/', '/projects']

/** Same-origin paths that are not pages: the proxied API and render artifacts. */
export const DISALLOWED_PATHS = ['/api/', '/static/']

/** A cartridge slug as the API and the router accept it. */
const SLUG_RE = /^[a-z0-9][a-z0-9_-]*$/

function base(origin) {
  return String(origin || DEFAULT_STUDIO_ORIGIN).replace(/\/+$/, '')
}

function xmlEscape(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

/**
 * The public cartridge slugs in a parsed `docs/commons-catalog.json`, sorted
 * and de-duplicated. Throws on a catalog with no cartridges or a malformed
 * slug: an empty or wrong sitemap must fail the build, not ship.
 */
export function catalogSlugs(catalog) {
  const cartridges = catalog && Array.isArray(catalog.cartridges) ? catalog.cartridges : null
  if (!cartridges || cartridges.length === 0) {
    throw new Error('commons catalog has no cartridges: refusing to build an empty Studio sitemap')
  }
  const slugs = new Set()
  for (const entry of cartridges) {
    const slug = entry && entry.slug
    if (typeof slug !== 'string' || !SLUG_RE.test(slug)) {
      throw new Error(`commons catalog entry has an invalid slug: ${JSON.stringify(slug)}`)
    }
    slugs.add(slug)
  }
  return [...slugs].sort()
}

/** sitemaps.org urlset: the catalog routes, then `/project/<slug>` per cartridge. */
export function buildSitemap(origin, slugs) {
  const root = base(origin)
  const locs = [
    ...CATALOG_PATHS.map((p) => `${root}${p}`),
    ...slugs.map((slug) => `${root}/project/${encodeURIComponent(slug)}`),
  ]
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...locs.map((loc) => `  <url><loc>${xmlEscape(loc)}</loc></url>`),
    '</urlset>',
    '',
  ].join('\n')
}

/** Allow the catalog and project pages, keep crawlers off the proxied API and
 *  the generated render artifacts, advertise the sitemap. */
export function buildRobots(origin) {
  const root = base(origin)
  return [
    'User-agent: *',
    'Allow: /',
    ...DISALLOWED_PATHS.map((p) => `Disallow: ${p}`),
    '',
    `Sitemap: ${root}/sitemap.xml`,
    '',
  ].join('\n')
}

/** llmstxt.org index for the Studio host: what it is, and where the full
 *  context lives (the API's and the landing's llms.txt). */
export function buildLlms(origin, slugs) {
  const root = base(origin)
  const cartridgeCount = slugs.length
  const example = slugs.includes('gridfinity') ? 'gridfinity' : slugs[0]
  return [
    '# Yantra4D Studio',
    '',
    `> The open parametric configurator for the Yantra4D commons: ${cartridgeCount} public cartridges,`,
    '> each customizable in the browser with sliders and toggles, with no install. Which',
    '> engines and export formats a visitor gets depends on the tier (see the landing).',
    '> The machine contract is the API; the product overview and pricing are on the landing.',
    '',
    '## Context',
    '',
    `- [API llms.txt](${API_ORIGIN}/api/llms.txt): public routes, render and estimate contract, OpenAPI 3.1 at /api/openapi.json`,
    `- [Landing llms.txt](${LANDING_ORIGIN}/llms.txt): what Yantra4D is, tiers, concepts, source code`,
    '',
    '## Studio',
    '',
    `- [Catalog](${root}/projects): search and filter every public cartridge`,
    `- [Cartridge pages](${root}/project/${encodeURIComponent(example)}): ${root}/project/<slug>, one per cartridge`,
    `- [Sitemap](${root}/sitemap.xml): every catalog and cartridge URL on this host`,
    '',
  ].join('\n')
}
