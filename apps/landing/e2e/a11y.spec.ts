/**
 * axe-core on the four representative pages, in the still and full profiles
 * (playwright.config.ts leaves this spec out of mobile-lite).
 *
 * The gate is `serious` + `critical`: the failures that stop a screen-reader or
 * keyboard user. `minor` and `moderate` findings are attached to the test as
 * annotations so they show in the report without being silently dropped.
 *
 * A static import, deliberately: a missing @axe-core/playwright must be RED,
 * not a suite that quietly runs no assertions (see the studio's accessibility
 * spec for the history).
 */
import AxeBuilder from '@axe-core/playwright';
import { test, expect, landingPath, settle } from './fixtures';

const PAGES = ['/', '/en/', '/concepts/hyperobjects/', '/en/concepts/commons/'];
const GATED = new Set(['serious', 'critical']);

type Violation = Awaited<ReturnType<AxeBuilder['analyze']>>['violations'][number];

function describe(v: Violation): string {
  const targets = v.nodes
    .slice(0, 5)
    .map((n) => n.target.join(' '))
    .join(' | ');
  return `${v.id} [${v.impact}] ${v.help} — ${v.nodes.length} node(s): ${targets} (${v.helpUrl})`;
}

for (const path of PAGES) {
  test(`axe: ${path} has no serious or critical violation`, async ({ page, tier }, testInfo) => {
    await page.goto(landingPath(path, tier));
    await settle(page);
    // Lazily mounted UI (the stage, "show more") has to be in the DOM to be
    // audited, and it mounts once the gallery is in view. Everything below the
    // gallery is static HTML, so no full scroll is needed for the audit.
    const gallery = page.getByTestId('commons-search');
    if (await gallery.count()) {
      await gallery.scrollIntoViewIfNeeded();
      await settle(page);
    }

    // Only violations are read, so only violations are collected in full —
    // markedly cheaper on a page with hundreds of cards.
    const results = await new AxeBuilder({ page }).options({ resultTypes: ['violations'] }).analyze();
    const gated = results.violations.filter((v) => GATED.has(v.impact ?? ''));
    const rest = results.violations.filter((v) => !GATED.has(v.impact ?? ''));

    for (const v of rest) testInfo.annotations.push({ type: `axe-${v.impact ?? 'unknown'}`, description: describe(v) });

    expect(gated.map(describe), 'serious/critical axe violations').toEqual([]);
  });
}
