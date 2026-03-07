import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage } from '../../helpers/test-utils.js'
import { skipIfNoBackend, goToRealProject } from './audit-helpers.js'

test.use({
  mockAPIs: false,
  viewport: { width: 375, height: 812 },
})
test.describe.configure({ mode: 'serial' })

test.describe('Responsive (Mobile) — Browser Audit', () => {
  test.beforeAll(async ({ request }, testInfo) => {
    await skipIfNoBackend(request, testInfo)
  })

  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  // ── Gridfinity ───────────────────────────────────────────────────

  test('gridfinity: mobile bar and viewer visible', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    // Canvas (viewer) should be visible
    await expect(page.locator('canvas').first()).toBeVisible()
    // Header should be visible
    await expect(page.locator('header').first()).toBeVisible()
  })

  test('gridfinity: controls accessible via bottom sheet', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    // On mobile, controls are in a bottom sheet or hamburger menu
    // Look for the mobile sidebar trigger (hamburger or controls button)
    const mobileTrigger = page.locator('[data-testid="studio-sidebar"] button').first()
      .or(page.locator('button', { hasText: /Controls|Controles/ }).first())
      .or(page.locator('[role="tab"]').first())

    if (await mobileTrigger.isVisible().catch(() => false)) {
      await mobileTrigger.click()
      await page.waitForTimeout(500)
    }
    // A slider should become visible (either in sheet or sidebar)
    const slider = page.locator('[role="slider"]').first()
    await expect(slider).toBeVisible({ timeout: 5000 })
  })

  // ── Tablaco ──────────────────────────────────────────────────────

  test('tablaco: mobile bar and viewer visible', async ({ page }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await expect(page.locator('canvas').first()).toBeVisible()
    await expect(page.locator('header').first()).toBeVisible()
  })

  test('tablaco: preset buttons are tappable (44px targets)', async ({ page }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    // Find preset buttons on mobile
    const presetBtn = page.locator('button', { hasText: /Standard|Mini/ }).first()
    if (await presetBtn.isVisible().catch(() => false)) {
      const box = await presetBtn.boundingBox()
      // WCAG 2.5.8: minimum 44px touch target
      expect(box.height).toBeGreaterThanOrEqual(44)
    }
  })

  // ── Custom MSH ───────────────────────────────────────────────────

  test('custom-msh: 6 mode tabs scroll/wrap on mobile', async ({ page }) => {
    await goToRealProject(page, 'custom-msh', 'Custom MSH')
    const tabs = page.locator('[role="tablist"] [role="tab"]')
    const count = await tabs.count()
    expect(count).toBe(6)
    // First and last tab should both be in DOM (scroll/wrap handles overflow)
    await expect(tabs.first()).toBeAttached()
    await expect(tabs.last()).toBeAttached()
  })

  test('custom-msh: 3D viewer is interactive on mobile', async ({ page }) => {
    await goToRealProject(page, 'custom-msh', 'Custom MSH')
    const canvas = page.locator('canvas').first()
    await expect(canvas).toBeVisible()
    // Verify touch-action: none is set on viewer container (prevents browser gestures)
    const touchAction = await canvas.evaluate(el => {
      const container = el.closest('[style*="touch-action"]') || el.parentElement
      return getComputedStyle(container).touchAction
    })
    expect(touchAction).toBe('none')
  })
})
