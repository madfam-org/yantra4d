import React, { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ProjectGalleryGrid from './ProjectGalleryGrid';
import StillStrip from './StillStrip';
import { settleTier, type Tier } from '../lib/tier';
import {
  CAROUSEL_LIMIT,
  EMPTY_FILTER,
  PAGE_SIZE,
  fillTemplate,
  filterItems,
  isFilterActive,
  partitionGallery,
  type GalleryFilter,
  type GalleryItem,
} from '../lib/gallery';
import type { ModelsManifest } from '../lib/models-manifest';

/**
 * The gallery island.
 *
 * What it does NOT do is the point: it ships no three.js, no commons list and
 * no meshes by itself. The first 24 cards are server-rendered HTML next to it;
 * the full list (`/data/<lang>/commons.json`) is fetched the first time someone
 * searches, filters or asks for more; the 3D stage (`ProjectCarousel3D` and the
 * `vendor-three` chunk behind it) is imported only once the device tier has
 * been settled as lite or full, which `settleTier()` decides right here, after
 * a WebGL probe. On the still tier the same objects appear as a thumbnail strip
 * and the 3D code is never requested.
 */

const ProjectCarousel3D = lazy(() => import('./ProjectCarousel3D'));

export interface GalleryLabels {
  search: string;
  allCategories: string;
  allDomains: string;
  showMore: string;
  showing: string;
  inThreeD: string;
  noResults: string;
  openStudio: string;
  openInStudio: string;
  swipe: string;
  drag: string;
  prev: string;
  next: string;
  live: string;
  stillStrip: string;
  hyperobject: string;
  loading: string;
  categories: Record<string, string>;
  domains: Record<string, string>;
}

export interface CommonsGalleryProps {
  lang: 'es' | 'en';
  labels: GalleryLabels;
  /** The server's pick for the stage: modelled first, capped at CAROUSEL_LIMIT. */
  stage: GalleryItem[];
  /** Every slug that has a pre-rendered mesh — lets the client reproduce the server's partition exactly. */
  modelled: string[];
  /** How many commons items exist in total (the JSON is only fetched on demand). */
  total: number;
  categories: string[];
  domains: string[];
  dataUrl: string;
  manifestUrl: string;
  studioUrl: string;
  /** Test seam: skips the WebGL probe and forces a tier. */
  forcedTier?: Tier;
}

type CommonsPayload = { items: GalleryItem[] };

export default function CommonsGallery(props: CommonsGalleryProps) {
  const { lang, labels, stage, modelled, total, categories, domains, dataUrl, manifestUrl, studioUrl, forcedTier } = props;

  const [tier, setTier] = useState<Tier | null>(forcedTier ?? null);
  const [manifest, setManifest] = useState<ModelsManifest | null>(null);
  const [all, setAll] = useState<GalleryItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<GalleryFilter>(EMPTY_FILTER);
  const [pages, setPages] = useState(1);
  const loadPromise = useRef<Promise<GalleryItem[]> | null>(null);
  const modelledSet = useMemo(() => new Set(modelled), [modelled]);

  // 1. Settle the tier once, right before anything 3D could load.
  useEffect(() => {
    if (forcedTier) return;
    setTier(settleTier().tier);
  }, [forcedTier]);

  // 2. The mesh manifest is only needed by the stage.
  useEffect(() => {
    if (tier === null || tier === 'still') return;
    let cancelled = false;
    fetch(manifestUrl)
      .then((r) => (r.ok ? r.json() : { models: [] }))
      .then((m: ModelsManifest) => { if (!cancelled) setManifest(m); })
      .catch(() => { if (!cancelled) setManifest({ models: [] }); });
    return () => { cancelled = true; };
  }, [tier, manifestUrl]);

  // 3. The full list, on demand, once.
  const ensureData = useCallback((): Promise<GalleryItem[]> => {
    if (all) return Promise.resolve(all);
    if (!loadPromise.current) {
      setLoading(true);
      loadPromise.current = fetch(dataUrl)
        .then((r) => (r.ok ? r.json() : { items: [] }))
        .then((payload: CommonsPayload) => {
          const items = Array.isArray(payload.items) ? payload.items : [];
          setAll(items);
          return items;
        })
        .catch(() => [] as GalleryItem[])
        .finally(() => setLoading(false));
    }
    return loadPromise.current;
  }, [all, dataUrl]);

  // 4. "Show more" is a server-rendered link; once we are awake we page locally.
  useEffect(() => {
    const more = document.querySelector<HTMLElement>('[data-testid="commons-more"]');
    if (!more) return;
    const onClick = (e: Event) => {
      e.preventDefault();
      ensureData().then(() => setPages((p) => p + 1));
    };
    more.addEventListener('click', onClick);
    return () => more.removeEventListener('click', onClick);
  }, [ensureData]);

  const active = isFilterActive(filter);
  const update = (patch: Partial<GalleryFilter>) => {
    setFilter((f) => ({ ...f, ...patch }));
    setPages(1);
    void ensureData();
  };

  // The partition the server made, reproduced when the data is here; before
  // that, the server's stage stands in.
  const view = useMemo(() => {
    if (!all) return { carousel: stage, grid: [] as GalleryItem[], count: total, ready: false };
    const source = active ? filterItems(all, filter) : all;
    const { carousel, grid } = partitionGallery(source, modelledSet, CAROUSEL_LIMIT);
    return { carousel, grid, count: source.length, ready: true };
  }, [all, active, filter, stage, total, modelledSet]);

  // Which grid cards this island draws. Unfiltered: pages AFTER the server's
  // first one (the SSR grid stays on the page). Filtered: everything, paged.
  const dynamicGrid = useMemo(() => {
    if (!view.ready) return [];
    if (active) return view.grid.slice(0, PAGE_SIZE * pages);
    return view.grid.slice(PAGE_SIZE, PAGE_SIZE * pages);
  }, [view, active, pages]);

  // Hide the server-rendered first page while a filter is active; the island
  // owns the whole result set then. Never remove it from the DOM: it is the
  // canonical content, and the filter may be cleared.
  useEffect(() => {
    const ssr = document.querySelector<HTMLElement>('[data-testid="commons-grid"]');
    const more = document.querySelector<HTMLElement>('[data-testid="commons-more"]');
    if (ssr) ssr.hidden = active;
    if (more) {
      const exhausted = view.ready && (active ? PAGE_SIZE * pages >= view.grid.length : PAGE_SIZE * pages >= view.grid.length);
      more.hidden = active || exhausted;
    }
  }, [active, view, pages]);

  const note = view.ready && view.grid.length > 0
    ? fillTemplate(labels.inThreeD, { shown: view.carousel.length, total: view.count })
    : undefined;

  return (
    <div className="flex flex-col gap-6" data-testid="commons-gallery" data-tier={tier ?? undefined}>
      {/* Toolbar: category, domain, search. Works on every tier. */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2 items-center">
          <select
            aria-label={labels.allCategories}
            value={filter.category}
            onChange={(e) => update({ category: e.target.value })}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm min-h-[44px]"
          >
            <option value="all">{labels.allCategories}</option>
            {categories.filter((c) => c !== 'all').map((c) => (
              <option key={c} value={c}>{labels.categories[c] ?? c}</option>
            ))}
          </select>
          <select
            aria-label={labels.allDomains}
            value={filter.domain}
            onChange={(e) => update({ domain: e.target.value })}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm min-h-[44px]"
          >
            <option value="all">{labels.allDomains}</option>
            {domains.map((d) => (
              <option key={d} value={d}>{labels.domains[d] ?? d}</option>
            ))}
          </select>
        </div>
        <label className="relative block w-full sm:w-72">
          <span className="sr-only">{labels.search}</span>
          <input
            type="search"
            data-testid="commons-search"
            placeholder={labels.search}
            value={filter.query}
            onChange={(e) => update({ query: e.target.value })}
            className="block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm min-h-[44px] focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </label>
      </div>

      {/* The stage — or its still-tier stand-in. */}
      {tier === null && <div data-testid="commons-loading" className="h-[60vh] rounded-xl border border-border bg-zinc-950" aria-busy="true" />}
      {tier === 'still' && (
        <StillStrip
          items={view.carousel}
          studioUrl={studioUrl}
          caption={labels.stillStrip}
          openLabel={labels.openStudio}
          hyperobjectLabel={labels.hyperobject}
        />
      )}
      {(tier === 'lite' || tier === 'full') && (
        <Suspense fallback={<div data-testid="commons-loading" className="h-[60vh] rounded-xl border border-border bg-zinc-950 flex items-center justify-center text-sm text-zinc-500" aria-busy="true">{labels.loading}</div>}>
          <ProjectCarousel3D
            lang={lang}
            tier={tier}
            labels={labels}
            projects={view.carousel}
            manifest={manifest}
            note={note}
            studioUrl={studioUrl}
          />
        </Suspense>
      )}

      {view.ready && view.count === 0 && (
        <p className="text-center text-muted-foreground" data-testid="commons-empty">{labels.noResults}</p>
      )}

      {/* Results the island owns: filtered sets, or pages after the first. */}
      {dynamicGrid.length > 0 && (
        <div data-testid="commons-grid-more">
          <ProjectGalleryGrid
            lang={lang}
            projects={dynamicGrid}
            activeCategory={filter.category}
            setActiveCategory={(c) => update({ category: c })}
            categoryLabels={labels.categories}
            domainLabels={labels.domains}
            openLabel={labels.openInStudio}
            hyperobjectLabel={labels.hyperobject}
            showTabs={active}
          />
          {view.grid.length > (active ? dynamicGrid.length : PAGE_SIZE * pages) && (
            <div className="mt-6 text-center">
              <button
                type="button"
                onClick={() => setPages((p) => p + 1)}
                className="rounded-md border border-border px-4 py-2 text-sm min-h-[44px] hover:bg-secondary/40"
              >
                {labels.showMore} · {fillTemplate(labels.showing, { shown: active ? dynamicGrid.length : PAGE_SIZE * pages, total: view.grid.length })}
              </button>
            </div>
          )}
        </div>
      )}
      {loading && <p className="text-center text-xs text-muted-foreground" aria-live="polite">{labels.loading}</p>}
    </div>
  );
}
