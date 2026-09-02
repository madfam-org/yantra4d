import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage } from '../../helpers/test-utils.js'
import {
  skipIfNoBackend,
  skipUnlessProject,
  goToRealProject,
  drainRenderQueue,
} from './audit-helpers.js'

test.use({
  mockAPIs: false,
  viewport: { width: 375, height: 812 },
})
test.describe.configure({ mode: 'serial' })

// projects/gridfinity/project.json declares project.name "Gridfinity".
const GRIDFINITY = 'Gridfinity'

/**
 * The viewer canvas the phone actually shows.
 *
 * Run #166 failed here on `locator('canvas').first()` resolving to a hidden
 * canvas. App.tsx and StudioMainView.tsx each rendered a desktop tree AND a
 * mobile tree and handed the same viewerContent to both, so four <canvas>
 * elements were mounted at 375 px with the first three inside display:none
 * subtrees — never a collapsed viewport: the controls sheet was shut in that
 * snapshot and the mobile viewer keeps its own flex:1.618 row. #81 now mounts
 * only the tree on screen, so there is one canvas again. The filter stays
 * because it states what the test means — a viewer the user can see — and
 * costs nothing when only one exists.
 */
const visibleCanvas = page => page.locator('canvas').filter({ visible: true }).first()

test.describe('Responsive (Mobile) — Browser Audit', () => {
  test.beforeAll(async ({ request }, testInfo) => {
    await skipIfNoBackend(request, testInfo, ['gridfinity'])
  })

  // One worker serves the whole suite and nothing else empties its queue: the
  // Studio does not cancel an in-flight render when the page goes away, so a
  // test that leaves mid-render abandons work the worker still has to finish.
  // Run #171 starved gridfinity's first render test that way, from custom-msh's
  // failing assembly group re-rendering every part on each serial-mode retry.
  // Drain after a failure — which is when work is abandoned — and once at the
  // end, so the next group starts on an empty queue.
  test.afterEach(async ({ request }, testInfo) => {
    if (testInfo.status !== testInfo.expectedStatus) {
      await drainRenderQueue(request, `failed test "${testInfo.title}"`)
    }
  })

  test.afterAll(async ({ request }) => {
    await drainRenderQueue(request, 'the responsive group')
  })

  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  // ── Gridfinity ───────────────────────────────────────────────────

  test('gridfinity: mobile bar and viewer visible', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', GRIDFINITY)
    // Canvas (viewer) should be visible
    await expect(visibleCanvas(page)).toBeVisible()
    // Header should be visible
    await expect(page.locator('header').first()).toBeVisible()
  })

  test('gridfinity: controls accessible via bottom sheet', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', GRIDFINITY)
    // The mobile bar's sheet trigger (StudioSidebar variant="mobile") is an
    // icon button whose only text is the sr-only t('btn.open_controls').
    // data-testid="studio-sidebar" is on the DESKTOP sidebar only — which at
    // this width was a display:none subtree before #81 and is not mounted at
    // all after it — so the old locator chain never found the trigger, matched
    // several elements at once, and its isVisible() threw strict-mode into the
    // catch: the sheet was never opened and the slider asserted below was one
    // the phone does not show.
    await page.getByRole('button', { name: /Open controls|Abrir controles/i })
      .first()
      .click()
    await page.waitForTimeout(500)
    // A slider must be on screen inside the sheet
    const slider = page.locator('[role="slider"]').filter({ visible: true }).first()
    await expect(slider).toBeVisible({ timeout: 5000 })
  })

  // ── Tablaco ──────────────────────────────────────────────────────

  test('tablaco: mobile bar and viewer visible', async ({ page }) => {
    skipUnlessProject(test, 'tablaco')
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await expect(visibleCanvas(page)).toBeVisible()
    await expect(page.locator('header').first()).toBeVisible()
  })

  test('tablaco: preset buttons are tappable (44px targets)', async ({ page }) => {
    skipUnlessProject(test, 'tablaco')
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
    // On a phone the mode tabs are the mobile bar's Radix TabsList, which
    // carries no aria-label — that is on the desktop ModeTabs, which this
    // width does not mount — so filter by what is on screen rather than by
    // label.
    const tabs = page.locator('[role="tablist"] [role="tab"]').filter({ visible: true })
    const count = await tabs.count()
    expect(count).toBe(6)
    // First and last tab should both be in DOM (scroll/wrap handles overflow)
    await expect(tabs.first()).toBeAttached()
    await expect(tabs.last()).toBeAttached()
  })

  test('custom-msh: 3D viewer is interactive on mobile', async ({ page }) => {
    await goToRealProject(page, 'custom-msh', 'Custom MSH')
    const canvas = visibleCanvas(page)
    await expect(canvas).toBeVisible()
    // Verify touch-action: none is set on viewer container (prevents browser gestures)
    const touchAction = await canvas.evaluate(el => {
      const container = el.closest('[style*="touch-action"]') || el.parentElement
      return getComputedStyle(container).touchAction
    })
    expect(touchAction).toBe('none')
  })
})
