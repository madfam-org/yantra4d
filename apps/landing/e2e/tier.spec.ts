/**
 * Device tier: the `<html data-tier data-tier-source>` contract.
 *
 *   override > stored record > cheap signals; the markup ships `still` and only
 *   JavaScript can raise it. `?tier=` is QA's and is never persisted. A visitor's
 *   choice (the toggle) is stored under TIER_STORAGE_KEY with `user: true` and
 *   wins over measurements but never over `?tier=`.
 *
 * `data-tier-source` vocabulary exercised here: override, signals, stored, user,
 * and the no-JavaScript case where the attribute is absent (the markup default).
 */
import {
  test,
  expect,
  landingPath,
  effectiveTier,
  settle,
  seedTierRecord,
  readTierRecord,
  signalTier,
  TIER_STORAGE_KEY,
  TIER_VERSION,
} from './fixtures';

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

test.describe('device tier', () => {
  test('the html carries the tier this profile asks for, and says where it came from', async ({ page, tier }) => {
    await page.goto(landingPath('/', tier));
    const html = page.locator('html');
    await expect(html).toHaveAttribute('data-tier', effectiveTier(tier));
    await expect(html).toHaveAttribute('data-tier-source', tier ? 'override' : 'signals');
    if (!tier) {
      // The still profile emulates prefers-reduced-motion and nothing else:
      // the page's own classifier must agree that this browser is `still`.
      expect(await signalTier(page)).toBe('still');
    }
  });

  test('?tier=lite overrides the signals, whatever they say', async ({ page }) => {
    await page.goto('/?tier=lite');
    await expect(page.locator('html')).toHaveAttribute('data-tier', 'lite');
    await expect(page.locator('html')).toHaveAttribute('data-tier-source', 'override');
    // Never persisted: the override belongs to the URL, not to the visitor.
    expect(await readTierRecord(page)).toBeNull();
  });

  test('an unknown ?tier= value is ignored rather than coerced', async ({ page }) => {
    await page.goto('/?tier=ultra');
    const html = page.locator('html');
    await expect(html).toHaveAttribute('data-tier-source', 'signals');
    await expect(html).toHaveAttribute('data-tier', await signalTier(page));
  });

  test('a stored measured record is honoured for a week, then the signals decide again', async ({ page }) => {
    await seedTierRecord(page, { version: TIER_VERSION, tier: 'lite', at: Date.now(), probed: true });
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('data-tier', 'lite');
    await expect(page.locator('html')).toHaveAttribute('data-tier-source', 'stored');

    await seedTierRecord(page, { version: TIER_VERSION, tier: 'lite', at: Date.now() - WEEK_MS - 60_000, probed: true });
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('data-tier-source', 'signals');

    // Another schema version is not this page's business.
    await seedTierRecord(page, { version: TIER_VERSION + 1, tier: 'lite', at: Date.now(), probed: true });
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('data-tier-source', 'signals');
  });

  test('the toggle stores the visitor choice and the reload lands on still', async ({ page }) => {
    // Start from a chosen `full` so the click means "turn 3D off" in every profile.
    await seedTierRecord(page, { version: TIER_VERSION, tier: 'full', at: Date.now(), user: true });
    await page.goto('/');
    await settle(page);
    const html = page.locator('html');
    await expect(html).toHaveAttribute('data-tier', 'full');
    await expect(html).toHaveAttribute('data-tier-source', 'user');

    const toggle = page.getByTestId('tier-toggle');
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');

    const reloaded = page.waitForEvent('load');
    await toggle.click();
    await reloaded;

    expect(await readTierRecord(page)).toEqual({
      version: TIER_VERSION,
      tier: 'still',
      at: expect.any(Number),
      user: true,
    });
    await expect(html).toHaveAttribute('data-tier', 'still');
    await expect(html).toHaveAttribute('data-tier-source', 'user');
    await expect(page.getByTestId('tier-toggle')).toHaveAttribute('aria-pressed', 'true');
  });

  test('turning 3D back on clears the choice and returns to automatic', async ({ page }) => {
    await seedTierRecord(page, { version: TIER_VERSION, tier: 'still', at: Date.now(), user: true });
    await page.goto('/');
    await settle(page);
    await expect(page.locator('html')).toHaveAttribute('data-tier-source', 'user');
    const toggle = page.getByTestId('tier-toggle');
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');

    const reloaded = page.waitForEvent('load');
    await toggle.click();
    await reloaded;

    expect(await readTierRecord(page), `${TIER_STORAGE_KEY} should be cleared`).toBeNull();
    await expect(page.locator('html')).toHaveAttribute('data-tier-source', 'signals');
    await expect(page.locator('html')).toHaveAttribute('data-tier', await signalTier(page));
  });

  test('on a device the signals classify still, the toggle asks for lite explicitly', async ({ page }) => {
    // Reduced motion makes any profile `still` by signals.
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');
    await settle(page);
    await expect(page.locator('html')).toHaveAttribute('data-tier', 'still');
    await expect(page.locator('html')).toHaveAttribute('data-tier-source', 'signals');
    const toggle = page.getByTestId('tier-toggle');
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');

    const reloaded = page.waitForEvent('load');
    await toggle.click();
    await reloaded;

    expect(await readTierRecord(page)).toEqual({ version: TIER_VERSION, tier: 'lite', at: expect.any(Number), user: true });
    await expect(page.locator('html')).toHaveAttribute('data-tier', 'lite');
    await expect(page.locator('html')).toHaveAttribute('data-tier-source', 'user');
  });

  test('under a ?tier= override the toggle is inert — QA owns the page', async ({ page }) => {
    await page.goto('/?tier=full');
    await settle(page);
    const toggle = page.getByTestId('tier-toggle');
    await expect(toggle).toBeVisible();
    await page.evaluate(() => {
      (window as unknown as { __y4dSamePage: boolean }).__y4dSamePage = true;
    });
    await toggle.click();
    await page.waitForTimeout(500);
    // No reload happened, nothing was stored, the override still stands.
    expect(await page.evaluate(() => (window as unknown as { __y4dSamePage?: boolean }).__y4dSamePage)).toBe(true);
    expect(await readTierRecord(page)).toBeNull();
    await expect(page.locator('html')).toHaveAttribute('data-tier', 'full');
    await expect(page.locator('html')).toHaveAttribute('data-tier-source', 'override');
  });

  test('without JavaScript the page is still, by construction', async ({ browser, baseURL }) => {
    const context = await browser.newContext({ javaScriptEnabled: false, baseURL });
    const page = await context.newPage();
    await page.goto('/?tier=full');
    const html = page.locator('html');
    await expect(html).toHaveAttribute('data-tier', 'still');
    // The bootstrap never ran, so it never said where the tier came from.
    await expect(html).not.toHaveAttribute('data-tier-source', /.+/);
    // And there is no 3D to turn off, so the control stays hidden.
    await expect(page.getByTestId('tier-toggle')).toBeHidden();
    await context.close();
  });
});
