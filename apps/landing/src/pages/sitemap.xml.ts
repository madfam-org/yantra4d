/** `/sitemap.xml` — the landing's own public pages (see src/lib/crawl.ts). */
import type { APIRoute } from 'astro';
import { buildSitemap } from '../lib/crawl';
import { SITE_ORIGIN } from '../lib/env';

export const GET: APIRoute = () =>
  new Response(buildSitemap(SITE_ORIGIN), {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
