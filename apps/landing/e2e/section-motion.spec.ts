import { test, expect, landingPath, settle, effectiveTier } from './fixtures';

for (const path of ['/', '/en/']) {
  test(`decorative diagrams run only while visible on ${path}`, async ({ page, tier }) => {
    await page.goto(landingPath(path, tier));
    await settle(page);
    const commons = page.locator('#hyper-commons');
    const cdg = page.locator('#cdg-section');
    const shape = commons.locator('.hc-shape-morph');
    await expect(commons).not.toHaveAttribute('data-motion-visible', '');
    if (effectiveTier(tier) === 'still') {
      await expect(shape).toHaveCSS('animation-name', 'none');
    } else {
      await expect(shape).toHaveCSS('animation-play-state', 'paused');
    }

    await shape.scrollIntoViewIfNeeded();
    await expect(commons).toHaveAttribute('data-motion-visible', '');
    await expect(commons.locator('h2')).toBeVisible();
    await expect(commons.locator('.hc-fade-in').first()).toHaveCSS('opacity', '1');
    if (effectiveTier(tier) === 'still') {
      await expect(shape).toHaveCSS('animation-name', 'none');
    } else {
      await expect(shape).toHaveCSS('animation-play-state', 'running');
      await expect(shape).not.toHaveCSS('animation-name', 'none');
    }

    await cdg.locator('.cdg-pulse-ring').scrollIntoViewIfNeeded();
    await expect(cdg).toHaveAttribute('data-motion-visible', '');
    await expect(cdg.locator('h2')).toBeVisible();
    await expect(cdg.locator('.cdg-fade-in').first()).toHaveCSS('opacity', '1');
    await page.locator('h1').scrollIntoViewIfNeeded();
    await expect(commons).not.toHaveAttribute('data-motion-visible', '');
    await expect(cdg).not.toHaveAttribute('data-motion-visible', '');
    if (effectiveTier(tier) === 'still') {
      await expect(shape).toHaveCSS('animation-name', 'none');
    } else {
      await expect(shape).toHaveCSS('animation-play-state', 'paused');
    }
  });
}
