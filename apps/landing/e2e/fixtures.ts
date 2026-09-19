/**
 * Shared fixture and helpers for the landing's Playwright gates.
 *
 * The one custom option is `tier`: the `?tier=` a project pins on every
 * navigation (`desktop-full` → full, `mobile-lite` → lite) or `null` for the
 * `still` project, which must land on still from its own signals (reduced
 * motion) with no override at all. Headless Chromium would otherwise be
 * classified by user agent, so every 3D profile says what it wants explicitly —
 * see BOT_UA_RE in src/lib/tier-core.js.
 *
 * Every number the specs compare against comes from perf-budgets.json, read
 * here once. Nothing in e2e/ hardcodes a budget.
 */
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { test as base, expect, type Page } from '@playwright/test';
import { TIER_STORAGE_KEY, TIER_VERSION } from '../src/lib/tier-core.js';

export type Tier = 'still' | 'lite' | 'full';

export type LandingOptions = {
  /** `?tier=` pinned on every navigation; `null` leaves the decision to the page's signals. */
  tier: Tier | null;
};

export const test = base.extend<LandingOptions>({
  tier: [null, { option: true }],
});

export { expect, TIER_STORAGE_KEY, TIER_VERSION };

export interface PerfBudgets {
  transfer: {
    initialJsBytes: number;
    initialPageBytes: number;
    threeChunkBytes: number;
    postprocessingChunkBytes: number;
    fullScrollBytes: Record<Tier, number>;
  };
  vitals: { lcpMs: { mobile: number; desktop: number }; inpMs: number; cls: number; tbtMs: number };
  runtime: { frameP95Ms: number; governorDemoteMs: number; maxWebglContexts: number; maxHeapMb: number; maxLongTaskMs: number };
  lighthouse: { performanceMobile: number; accessibility: number; bestPractices: number; seo: number };
}

export const BUDGETS: PerfBudgets = JSON.parse(
  fs.readFileSync(fileURLToPath(new URL('../perf-budgets.json', import.meta.url)), 'utf8'),
);

/** The 3D chunk, named by astro.config.mjs `manualChunks`. */
export const THREE_CHUNK_RE = /vendor-three\./;
/** The on-demand commons list, one file per locale. */
export const COMMONS_JSON_RE = /\/data\/(es|en)\/commons\.json/;

/** The tier a project's page actually renders when nothing is stored. */
export function effectiveTier(tier: Tier | null): Tier {
  return tier ?? 'still';
}

/** `path` with the project's `?tier=` appended (or untouched when there is none). */
export function landingPath(path: string, tier: Tier | null): string {
  if (!tier) return path;
  return `${path}${path.includes('?') ? '&' : '?'}tier=${tier}`;
}

export function kb(bytes: number): string {
  return `${(bytes / 1024).toFixed(1)} KB`;
}

/** Load event, then no network for 500 ms — the static site's "done". */
export async function settle(page: Page): Promise<void> {
  await page.waitForLoadState('load');
  await page.waitForLoadState('networkidle');
}

/**
 * Scroll to the footer the way a person does — one viewport at a time, with a
 * pause so IntersectionObservers and lazy images fire — then settle the
 * network. ONE in-page loop rather than a CDP round trip per step: with a live
 * canvas the main thread is contended and every evaluate would queue behind
 * it. Throws when the footer is not reached within the time budget, because a
 * partial scroll would turn every "full scroll" figure into a lie. Callers
 * mark their test `slow()`: on a phone viewport the un-paged gallery is a
 * 177,000 px page, and a starved main thread stretches every step.
 */
export async function scrollThrough(page: Page, { pauseMs = 50, maxMs = 150_000 } = {}): Promise<void> {
  const result = await page.evaluate(
    async ({ pauseMs, maxMs }) => {
      const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
      const start = performance.now();
      let steps = 0;
      const outcome = (reachedBottom: boolean) => ({
        reachedBottom,
        steps,
        height: document.documentElement.scrollHeight,
        ms: Math.round(performance.now() - start),
      });
      while (performance.now() - start < maxMs) {
        const before = window.scrollY;
        window.scrollTo({ top: before + window.innerHeight, behavior: 'instant' as ScrollBehavior });
        steps += 1;
        await sleep(pauseMs);
        const max = document.documentElement.scrollHeight - window.innerHeight;
        if (window.scrollY >= max - 1 || window.scrollY === before) return outcome(true);
      }
      return outcome(false);
    },
    { pauseMs, maxMs },
  );
  if (!result.reachedBottom) {
    throw new Error(
      `scrollThrough: footer not reached in ${result.ms} ms (${result.steps} steps, page ${result.height}px tall) — is the main thread starved?`,
    );
  }
  await settle(page);
}

export interface Transfer {
  url: string;
  status: number;
  type: string;
  /** Encoded (compressed) response body bytes — what actually crossed the wire. */
  bytes: number;
}

function isScript(t: Transfer): boolean {
  return t.type === 'script' || /\.m?js(\?|$)/.test(t.url);
}

/**
 * Record every response's transfer size. `request().sizes()` resolves once the
 * body has finished, so call `flush()` before reading, and take a `snapshot()`
 * when a measurement must not include what arrives later.
 */
export function trackTransfers(page: Page) {
  const entries: Transfer[] = [];
  const pending: Promise<void>[] = [];
  page.on('response', (response) => {
    const request = response.request();
    pending.push(
      request
        .sizes()
        .then((s) => {
          entries.push({ url: response.url(), status: response.status(), type: request.resourceType(), bytes: s.responseBodySize });
        })
        .catch(() => {
          /* aborted before it finished: nothing reached the page */
        }),
    );
  });
  const total = (list: Transfer[] = entries) => list.reduce((sum, t) => sum + t.bytes, 0);
  const describe = (list: Transfer[]) =>
    list
      .slice()
      .sort((a, b) => b.bytes - a.bytes)
      .map((t) => `  ${kb(t.bytes).padStart(10)}  ${t.type.padEnd(10)} ${t.url}`)
      .join('\n');
  return {
    entries,
    async flush() {
      await Promise.all(pending.slice());
    },
    snapshot: () => entries.slice(),
    js: (list: Transfer[] = entries) => list.filter(isScript),
    matching: (re: RegExp, list: Transfer[] = entries) => list.filter((t) => re.test(t.url)),
    largest: (n: number, list: Transfer[] = entries) => list.slice().sort((a, b) => b.bytes - a.bytes).slice(0, n),
    total,
    describe,
  };
}

/** Console errors, uncaught exceptions, failed requests and HTTP >= 400, as they happen. */
export function watchErrors(page: Page) {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];
  const badResponses: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(String(error)));
  page.on('requestfailed', (request) => failedRequests.push(`${request.url()} — ${request.failure()?.errorText ?? 'failed'}`));
  page.on('response', (response) => {
    if (response.status() >= 400) badResponses.push(`${response.status()} ${response.url()}`);
  });
  return { consoleErrors, pageErrors, failedRequests, badResponses };
}

export interface LongTask {
  start: number;
  duration: number;
}

/**
 * Observe `longtask` entries from document start. `buffered: true` hands over
 * anything that ran before the observer attached, so parsing and hydration are
 * in the record, not only what happens after the load event.
 */
export async function installLongTaskObserver(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const w = window as unknown as { __y4dLongTasks: LongTask[]; __y4dLongTasksUnsupported?: boolean };
    w.__y4dLongTasks = [];
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) w.__y4dLongTasks.push({ start: entry.startTime, duration: entry.duration });
      }).observe({ type: 'longtask', buffered: true });
    } catch {
      w.__y4dLongTasksUnsupported = true;
    }
  });
}

export async function readLongTasks(page: Page): Promise<{ tasks: LongTask[]; unsupported: boolean; loadEventEnd: number }> {
  return page.evaluate(() => {
    const w = window as unknown as { __y4dLongTasks?: LongTask[]; __y4dLongTasksUnsupported?: boolean };
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
    return {
      tasks: w.__y4dLongTasks ?? [],
      unsupported: Boolean(w.__y4dLongTasksUnsupported),
      loadEventEnd: nav?.loadEventEnd ?? 0,
    };
  });
}

/** Seed the visitor's tier record before the page's <head> bootstrap reads it. */
export async function seedTierRecord(page: Page, record: Record<string, unknown> | null): Promise<void> {
  await page.addInitScript(
    ([key, value]) => {
      if (value === null) window.localStorage.removeItem(key);
      else window.localStorage.setItem(key, value);
    },
    [TIER_STORAGE_KEY, record === null ? null : JSON.stringify(record)] as const,
  );
}

export async function readTierRecord(page: Page): Promise<Record<string, unknown> | null> {
  return page.evaluate((key) => {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  }, TIER_STORAGE_KEY);
}

/** What the page's own classifier (inlined in <head>) says about THIS browser's cheap signals. */
export async function signalTier(page: Page): Promise<Tier> {
  return page.evaluate(() => {
    const g = globalThis as unknown as { classifyTier: (s: unknown) => Tier; readCheapSignals: (w: Window) => unknown };
    return g.classifyTier(g.readCheapSignals(window));
  });
}
