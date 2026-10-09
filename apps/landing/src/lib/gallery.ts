/**
 * Pure gallery logic — filtering, the 3D/grid partition, paging and string
 * templates. No React, no DOM, no fetch: the island composes these and the
 * tests pin them as tables.
 */

export interface GalleryItem {
  slug: string;
  name: string;
  description: string;
  category: string;
  thumbnail: string;
  isHyperobject: boolean;
  domain: string;
}

export interface GalleryFilter {
  query: string;
  category: string;
  domain: string;
}

/**
 * How many hyperobjects the 3D stage mounts at once. Every item is a live
 * mesh; the rest of any result set flows into the grid so nothing disappears.
 */
export const CAROUSEL_LIMIT = 24;

/** Cards the grid reveals per "show more". Also the server-rendered first page. */
export const PAGE_SIZE = 24;

export const EMPTY_FILTER: GalleryFilter = { query: '', category: 'all', domain: 'all' };

export function isFilterActive(f: GalleryFilter): boolean {
  return f.query.trim() !== '' || f.category !== 'all' || f.domain !== 'all';
}

export function filterItems(items: readonly GalleryItem[], f: GalleryFilter): GalleryItem[] {
  const q = f.query.trim().toLowerCase();
  return items.filter((p) => {
    if (q) {
      const text = `${p.name} ${p.description} ${p.slug}`.toLowerCase();
      if (!text.includes(q)) return false;
    }
    if (f.category === 'commons') {
      if (!p.isHyperobject) return false;
    } else if (f.category !== 'all' && p.category !== f.category) {
      return false;
    }
    if (f.domain !== 'all' && p.domain !== f.domain) return false;
    return true;
  });
}

/**
 * Split a result set between the 3D stage and the grid.
 *
 * The stage exists to show live geometry, so anything with a mesh goes first —
 * hyperobjects ahead of the rest, since they are what the section is about.
 * Unmodelled hyperobjects fill any remaining slots so a filtered view still
 * populates instead of emptying. Stable within groups. The grid is everything
 * the stage did not take, in the original order, derived from the stage rather
 * than assembled separately so a project can never appear in both.
 */
export function partitionGallery(
  items: readonly GalleryItem[],
  modelled: ReadonlySet<string>,
  limit: number = CAROUSEL_LIMIT,
): { carousel: GalleryItem[]; grid: GalleryItem[] } {
  const hyper = items.filter((p) => p.isHyperobject);
  const others = items.filter((p) => !p.isHyperobject);
  const has = (p: GalleryItem) => modelled.has(p.slug);
  const ranked = [...hyper.filter(has), ...others.filter(has), ...hyper.filter((p) => !has(p))];
  const carousel = ranked.slice(0, limit);
  const taken = new Set(carousel.map((p) => p.slug));
  return { carousel, grid: items.filter((p) => !taken.has(p.slug)) };
}

/**
 * `"Showing {shown} of {total}"` → `"Showing 24 of 502"`. Unknown, null and
 * undefined keys stay visible as `{key}` — a missing figure must be seen, not
 * silently blanked. Client-safe (no locale imports); `i18n.ts` re-exports it.
 */
export function fillTemplate(
  template: string,
  vars: Record<string, string | number | null | undefined>,
): string {
  return template.replace(/\{(\w+)\}/g, (m, key: string) => {
    const value = vars[key];
    return value === null || value === undefined ? m : String(value);
  });
}

/** The distinct, non-empty domains in list order of first appearance. */
export function domainsOf(items: readonly GalleryItem[]): string[] {
  const seen = new Set<string>();
  for (const p of items) if (p.domain && !seen.has(p.domain)) seen.add(p.domain);
  return [...seen];
}
