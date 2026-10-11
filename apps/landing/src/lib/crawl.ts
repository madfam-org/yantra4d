/**
 * Crawl files for yantra4d.com: `/sitemap.xml` and `/robots.txt`.
 *
 * Both are built statically by the endpoints in `src/pages/` from the list
 * below, so nginx serves real files instead of the SPA fallback (which used to
 * answer them with 200 text/html).
 *
 * A sitemap may only list URLs on its own host, so this covers the landing's
 * own pages. The hyperobject configurators the gallery links to live on
 * app.yantra4d.com and belong in that host's sitemap, not this one. The
 * `/data/<lang>/commons.json` endpoint is data, not a page, and is left out.
 *
 * `crawl.test.ts` walks `src/pages/` and fails when a page is added or removed
 * without updating this list.
 */

/** Spanish (unprefixed) path of every public page; English lives under `/en`.
 *  Trailing slashes match the canonical links BaseLayout emits. */
export const PUBLIC_PAGE_PATHS = [
  '/',
  '/concepts/hyperobjects/',
  '/concepts/common-denominator/',
  '/concepts/commons/',
] as const;

/** The English counterpart of a Spanish path, as BaseLayout computes it. */
export function englishPath(esPath: string): string {
  return `/en${esPath}`;
}

function xmlEscape(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/** sitemaps.org urlset with the same es / en / x-default alternates as the
 *  `<link rel="alternate">` tags in BaseLayout. */
export function buildSitemap(origin: string, esPaths: readonly string[] = PUBLIC_PAGE_PATHS): string {
  const base = origin.replace(/\/+$/, '');
  const entries = esPaths.flatMap((esPath) => {
    const es = `${base}${esPath}`;
    const en = `${base}${englishPath(esPath)}`;
    const alternates = [
      `    <xhtml:link rel="alternate" hreflang="es" href="${xmlEscape(es)}"/>`,
      `    <xhtml:link rel="alternate" hreflang="en" href="${xmlEscape(en)}"/>`,
      `    <xhtml:link rel="alternate" hreflang="x-default" href="${xmlEscape(es)}"/>`,
    ].join('\n');
    return [es, en].map((loc) => `  <url>\n    <loc>${xmlEscape(loc)}</loc>\n${alternates}\n  </url>`);
  });
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ...entries,
    '</urlset>',
    '',
  ].join('\n');
}

/** The landing is a static marketing site: nothing on this host is private, so
 *  everything is allowed and the sitemap is advertised. */
export function buildRobots(origin: string): string {
  const base = origin.replace(/\/+$/, '');
  return ['User-agent: *', 'Allow: /', '', `Sitemap: ${base}/sitemap.xml`, ''].join('\n');
}
