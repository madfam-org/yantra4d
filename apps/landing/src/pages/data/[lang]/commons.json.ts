/**
 * `/data/<lang>/commons.json` — the commons list the gallery island fetches ON
 * DEMAND (first search, filter or "show more"), one locale at a time.
 *
 * Built statically from the same generated `src/data/projects.ts` the Astro
 * pages render from, so the JSON can never disagree with the HTML. Before this
 * endpoint existed the whole bilingual array (502 entries) was bundled INTO the
 * gallery island's JavaScript and shipped to every visitor before they had
 * touched anything.
 */
import type { APIRoute, GetStaticPaths } from 'astro';
import { PROJECTS, COMMONS_STATS } from '../../../data/projects';

export const getStaticPaths: GetStaticPaths = () => [
  { params: { lang: 'es' } },
  { params: { lang: 'en' } },
];

export interface CommonsItem {
  slug: string;
  name: string;
  description: string;
  category: string;
  thumbnail: string;
  isHyperobject: boolean;
  domain: string;
}

export function commonsItems(lang: 'es' | 'en'): CommonsItem[] {
  return PROJECTS.map((p) => ({
    slug: p.slug,
    name: p.name,
    description: lang === 'es' ? p.descriptionEs : p.description,
    category: p.category,
    thumbnail: p.thumbnail,
    isHyperobject: Boolean(p.isHyperobject),
    domain: p.domain ?? '',
  }));
}

export const GET: APIRoute = ({ params }) => {
  const lang = params.lang === 'en' ? 'en' : 'es';
  const items = commonsItems(lang);
  const body = JSON.stringify({
    lang,
    count: items.length,
    stats: COMMONS_STATS,
    items,
  });
  return new Response(body, {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
