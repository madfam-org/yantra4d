/**
 * Transfer and runtime budgets, measured in a real browser against the built
 * site. Every threshold comes from perf-budgets.json.
 *
 * Bytes for text resources are the body re-compressed with brotli (what
 * Cloudflare serves in production and what perf-budgets.json is written in);
 * binary resources count their encoded body. See `trackTransfers` in
 * fixtures.ts. `astro preview` itself only speaks gzip, which would read ~10%
 * high and make the same build pass the CI bundle step yet fail here.
 */
import {
  test,
  expect,
  BUDGETS,
  COMMONS_JSON_RE,
  THREE_CHUNK_RE,
  effectiveTier,
  installLongTaskObserver,
  kb,
  landingPath,
  readLongTasks,
  scrollThrough,
  settle,
  trackTransfers,
  watchErrors,
} from './fixtures';

const { transfer, runtime } = BUDGETS;

test.describe('transfer budgets', () => {
  test('JavaScript requested before any scroll fits transfer.initialJsBytes', async ({ page, tier }) => {
    const transfers = trackTransfers(page);
    await page.goto(landingPath('/', tier));
    await settle(page);
    await transfers.flush();
    const snapshot = transfers.snapshot();
    const js = transfers.js(snapshot);
    const total = transfers.total(js);
    expect(
      total,
      `initial JS on ${effectiveTier(tier)}: ${kb(total)} against ${kb(transfer.initialJsBytes)}\n${transfers.describe(js)}`,
    ).toBeLessThanOrEqual(transfer.initialJsBytes);

    // The initial PAGE: document + stylesheets + that JavaScript. Images are
    // deliberately excluded — Chrome's lazy-load distance fetches the first
    // grid thumbnails on a tall viewport, and they have their own budget
    // (perf-budgets.json `images`).
    const page_ = snapshot.filter((r) => r.type === 'document' || r.type === 'stylesheet' || /\.css(\?|$)/.test(r.url));
    const pageTotal = transfers.total(page_) + total;
    expect(
      pageTotal,
      `initial page (document + css + js) on ${effectiveTier(tier)}: ${kb(pageTotal)} against ${kb(transfer.initialPageBytes)}\n${transfers.describe([...page_, ...js])}`,
    ).toBeLessThanOrEqual(transfer.initialPageBytes);
  });

  test('the 3D chunk: never on still; only once the gallery is in view on lite/full, within transfer.threeChunkBytes', async ({ page, tier }) => {
    test.slow(); // the still branch scrolls the whole page
    const transfers = trackTransfers(page);
    await page.goto(landingPath('/', tier));
    await settle(page);
    await transfers.flush();
    expect(
      transfers.matching(THREE_CHUNK_RE).map((t) => t.url),
      'vendor-three must not be requested before the gallery is in view',
    ).toEqual([]);

    if (effectiveTier(tier) === 'still') {
      await scrollThrough(page);
      await transfers.flush();
      expect(transfers.matching(THREE_CHUNK_RE).map((t) => t.url), 'vendor-three must never be requested on tier still').toEqual([]);
      await expect(page.getByTestId('commons-still'), 'the still tier shows the thumbnail strip').toBeVisible();
      await expect(page.getByTestId('commons-stage'), 'the still tier mounts no stage').toHaveCount(0);
      return;
    }

    // Scroll the island itself into view: the section is taller than any
    // viewport, so centring `#gallery` can leave the toolbar (the island's
    // root) above the fold and the client:visible observer never fires.
    await page.getByTestId('commons-search').scrollIntoViewIfNeeded();
    await expect(page.getByTestId('commons-stage'), 'the stage mounts once the gallery is in view').toBeVisible({ timeout: 30_000 });
    await settle(page);
    await transfers.flush();
    const three = transfers.matching(THREE_CHUNK_RE);
    expect(three.map((t) => t.url), 'exactly one vendor-three request').toHaveLength(1);
    expect(three[0].bytes, `vendor-three transfer ${kb(three[0].bytes)} against ${kb(transfer.threeChunkBytes)}`).toBeLessThanOrEqual(
      transfer.threeChunkBytes,
    );
    await expect(page.getByTestId('commons-still'), 'a 3D tier does not also render the still strip').toHaveCount(0);
  });

  test('a full scroll to the footer stays within transfer.fullScrollBytes[tier] and is clean', async ({ page, tier }) => {
    test.slow(); // a full scroll of a 3D page on a software GPU is minutes, not seconds
    const t = effectiveTier(tier);
    const transfers = trackTransfers(page);
    const errors = watchErrors(page);
    await page.goto(landingPath('/', tier));
    await settle(page);
    await scrollThrough(page);
    await transfers.flush();

    const total = transfers.total();
    expect
      .soft(total, `full-scroll transfer on ${t}: ${kb(total)} against ${kb(transfer.fullScrollBytes[t])}; largest:\n${transfers.describe(transfers.largest(15))}`)
      .toBeLessThanOrEqual(transfer.fullScrollBytes[t]);
    expect.soft(await page.locator('canvas').count(), `canvas elements (runtime.maxWebglContexts = ${runtime.maxWebglContexts})`).toBeLessThanOrEqual(
      runtime.maxWebglContexts,
    );
    expect.soft(errors.consoleErrors, 'console errors during load and scroll').toEqual([]);
    expect.soft(errors.pageErrors, 'uncaught exceptions during load and scroll').toEqual([]);
    expect.soft(errors.failedRequests, 'failed requests during load and scroll').toEqual([]);
    expect.soft(errors.badResponses, 'HTTP >= 400 during load and scroll').toEqual([]);
  });

  for (const [path, lang] of [
    ['/', 'es'],
    ['/en/', 'en'],
  ] as const) {
    test(`commons.json is fetched on demand only (${path})`, async ({ page, tier }) => {
      const transfers = trackTransfers(page);
      await page.goto(landingPath(path, tier));
      await settle(page);
      await page.getByTestId('commons-search').scrollIntoViewIfNeeded();
      await settle(page);
      await transfers.flush();
      expect(transfers.matching(COMMONS_JSON_RE).map((t) => t.url), 'commons.json before any search, filter or "show more"').toEqual([]);

      const search = page.getByTestId('commons-search');
      await expect(search).toBeVisible();
      // The island hydrates on scroll and stamps `data-tier` on its root once it
      // has settled the tier; typing before that would test the SSR input, not
      // the island (the island replays such a value, but the assertion here is
      // about the fetch, so wait for the handler to exist).
      await expect(page.getByTestId('commons-gallery')).toHaveAttribute('data-tier', /still|lite|full/, { timeout: 30_000 });
      const responded = page.waitForResponse((r) => COMMONS_JSON_RE.test(r.url()));
      await search.fill('grid');
      const response = await responded;
      expect(response.ok()).toBe(true);
      expect(new URL(response.url()).pathname).toBe(`/data/${lang}/commons.json`);
    });
  }

  test(`no long task exceeds runtime.maxLongTaskMs after load`, async ({ page, tier }) => {
    await installLongTaskObserver(page);
    await page.goto(landingPath('/', tier));
    await settle(page);
    // Hydration's tail can land after networkidle; give it a moment to show up.
    await page.waitForTimeout(1_000);
    const { tasks, unsupported, loadEventEnd } = await readLongTasks(page);
    expect(unsupported, 'PerformanceObserver("longtask") is unsupported in this browser').toBe(false);
    // The budget is about the page AFTER it has loaded: the parse-and-hydrate
    // work that runs before loadEventEnd is what Lighthouse's TBT budget
    // (vitals.tbtMs) measures, on a throttled CPU. Counting it here too would
    // fail the page on the banner's one-time react-dom evaluation and say
    // nothing about the stage.
    const over = tasks.filter((task) => task.start >= loadEventEnd && task.duration > runtime.maxLongTaskMs);
    const describe = tasks
      .map((task) => `${Math.round(task.duration)} ms at ${Math.round(task.start)} ms${task.start > loadEventEnd ? ' (after load)' : ''}`)
      .join(', ');
    expect(over, `long tasks over ${runtime.maxLongTaskMs} ms — all long tasks: ${describe || 'none'}`).toEqual([]);
  });
});
