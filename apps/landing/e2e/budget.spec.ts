/**
 * Transfer and runtime budgets, measured in a real browser against the built
 * site. Every threshold comes from perf-budgets.json.
 *
 * Bytes are `request.sizes().responseBodySize`: the ENCODED body, i.e. what the
 * server actually sent. `astro preview` speaks gzip, so these figures run ~10%
 * above the brotli numbers the budgets are written in — the gate errs on the
 * strict side, never the lenient one.
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
    const js = transfers.js(transfers.snapshot());
    const total = transfers.total(js);
    expect(
      total,
      `initial JS on ${effectiveTier(tier)}: ${kb(total)} against ${kb(transfer.initialJsBytes)}\n${transfers.describe(js)}`,
    ).toBeLessThanOrEqual(transfer.initialJsBytes);
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

    await page.locator('#gallery').scrollIntoViewIfNeeded();
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
      await page.locator('#gallery').scrollIntoViewIfNeeded();
      await settle(page);
      await transfers.flush();
      expect(transfers.matching(COMMONS_JSON_RE).map((t) => t.url), 'commons.json before any search, filter or "show more"').toEqual([]);

      const search = page.getByTestId('commons-search');
      await expect(search).toBeVisible();
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
    const over = tasks.filter((task) => task.duration > runtime.maxLongTaskMs);
    const describe = tasks
      .map((task) => `${Math.round(task.duration)} ms at ${Math.round(task.start)} ms${task.start > loadEventEnd ? ' (after load)' : ''}`)
      .join(', ');
    expect(over, `long tasks over ${runtime.maxLongTaskMs} ms — all long tasks: ${describe || 'none'}`).toEqual([]);
  });
});
