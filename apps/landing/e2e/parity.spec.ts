/**
 * Still/full parity: the stage is decoration, the HTML is canonical.
 *
 * Whatever the full tier draws, a visitor on still — and a crawler, and a
 * screen reader — must get the same headings and the same numbers. Both pages
 * are loaded in the same context, one after the other (the override lives in
 * the URL and is never persisted), with the gallery scrolled into view so the
 * stage or the still strip has mounted, and compared. Each page is closed once
 * read: two live canvases in one browser starve each other's main thread.
 */
import { test, expect, settle, type Tier } from './fixtures';
import type { Page } from '@playwright/test';

const PAGES = ['/', '/en/'];
const FACT_SECTIONS = ['#hyper-commons', '#cdg-section'];

function normalise(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

/** Every number in a block of text, in order — "502 cartridges", "1 archivo", "4.5:1". */
function numbers(text: string): string[] {
  return text.match(/\d[\d.,]*/g) ?? [];
}

async function snapshot(page: Page, path: string, tier: Tier) {
  try {
    await page.goto(`${path}?tier=${tier}`);
    await settle(page);
    await expect(page.locator('html')).toHaveAttribute('data-tier', tier);
    await page.getByTestId('commons-search').scrollIntoViewIfNeeded();
    await settle(page);
    const headings = (await page.locator('h1, h2').allInnerTexts()).map(normalise).filter(Boolean);
    const facts: Record<string, string[]> = {};
    for (const selector of FACT_SECTIONS) facts[selector] = numbers(await page.locator(selector).innerText());
    return { headings, facts };
  } finally {
    await page.close();
  }
}

for (const path of PAGES) {
  test(`still and full expose the same headings and facts on ${path}`, async ({ context }) => {
    const still = await snapshot(await context.newPage(), path, 'still');
    const full = await snapshot(await context.newPage(), path, 'full');

    // Guard against a trivially equal empty comparison.
    expect(still.headings.length, 'headings on the still page').toBeGreaterThan(3);
    expect(full.headings, 'h1/h2 text, full vs still').toEqual(still.headings);

    for (const selector of FACT_SECTIONS) {
      expect(still.facts[selector].length, `numeric facts in ${selector} on still`).toBeGreaterThan(0);
      expect(full.facts[selector], `numeric facts in ${selector}, full vs still`).toEqual(still.facts[selector]);
    }
  });
}
