/** `/robots.txt` — allow all, advertise the sitemap (see src/lib/crawl.ts). */
import type { APIRoute } from 'astro';
import { buildRobots } from '../lib/crawl';
import { SITE_ORIGIN } from '../lib/env';

export const GET: APIRoute = () =>
  new Response(buildRobots(SITE_ORIGIN), {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
