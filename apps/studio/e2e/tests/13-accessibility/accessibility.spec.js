import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, setLanguage } from '../../helpers/test-utils.js'

// A STATIC import, deliberately. This used to be a `try { await import(...) }
// catch {}` that left `AxeBuilder` undefined, and both axe tests below were
// wrapped in `if (AxeBuilder)` — so dropping the dependency (or renaming its
// entry point, or breaking its install) turned the entire axe gate into two
// tests that ran no assertions and reported green. A missing dependency must
// be RED. `@axe-core/playwright` is a declared devDependency of apps/studio;
// if this import throws, the fix is to install it, not to guard it.
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  test('studio view passes axe audit', async ({ page }) => {
    await goToStudio(page)
    const results = await new AxeBuilder({ page })
      .disableRules([
        // The ONLY rule disabled here, and only because this run does not pin
        // a theme: contrast is computed from rendered colours, the studio ships
        // light and dark palettes, and the beforeEach sets a language but no
        // theme — so the same source would pass or fail depending on which
        // palette the run happened to load. Re-enable it together with a
        // per-theme axe run (one Playwright project per theme), not on its own.
        'color-contrast',
      ])
      .analyze()
    // Log every violation at every impact level. The gate below is
    // critical+serious; the rest still belong in the log so the backlog stays
    // visible rather than silently excluded.
    if (results.violations.length > 0) {
      console.log('Axe violations:', JSON.stringify(results.violations.map(v => ({
        id: v.id, impact: v.impact, description: v.description,
        nodes: v.nodes.length
      })), null, 2))
    }
    // critical AND serious. `serious` is where the failures that actually stop
    // a screen-reader or keyboard user live (nested-interactive, unlabelled
    // controls, focus order); gating on `critical` alone let every one of them
    // through.
    //
    // Eight rules that used to be disabled here are gone, because the reasons
    // recorded against them do not hold up against this source:
    //   - aria-allowed-attr was excused as "Radix custom data-state
    //     attributes", but that rule inspects aria-* attributes only; data-*
    //     is outside its scope entirely.
    //   - aria-valid-attr-value was excused as "Radix aria-controls
    //     references"; axe reports those as INCOMPLETE rather than violations
    //     when the trigger carries aria-selected="false", which Radix Tabs
    //     sets on every inactive trigger.
    //   - nested-interactive was excused as "Shadcn compound components", but
    //     every compound trigger reachable from the studio view
    //     (StudioHeader's DropdownMenuTrigger, StudioSidebar's SheetTrigger)
    //     passes `asChild`, so no interactive element nests inside another.
    //   - aria-required-children / aria-required-parent were excused as "Radix
    //     UI custom component roles"; StudioSidebar's ModeTabs is a hand-rolled
    //     role="tablist" over role="tab" children, and StudioHeader's language
    //     menu is role="listbox" over role="option" children. Both are exactly
    //     the shape those rules ask for.
    //   - landmark-one-main / region / page-has-heading-one are all
    //     moderate-impact, so they cannot move a critical+serious gate in
    //     either direction; disabling them only hid them from the log above.
    //     (StudioHeader renders an <h1>, so "Projects view uses h2" never
    //     described this view to begin with.)
    const blocking = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    )
    expect(blocking.map(v => `${v.impact}: ${v.id} (${v.nodes.length} nodes)`)).toEqual([])
  })

  test('projects view passes axe audit', async ({ page }) => {
    await goToProjects(page)
    // Unchanged apart from the vacuous `if (AxeBuilder)` guard: this view
    // already asserts on violations at EVERY impact level, which is stricter
    // than the studio gate above. Narrowing its three exclusions is a separate
    // change with a separate blast radius.
    const results = await new AxeBuilder({ page })
      .disableRules(['color-contrast', 'landmark-one-main', 'region'])
      .analyze()
    expect(results.violations).toEqual([])
  })

  test('all icon buttons have aria-labels or sr-only text', async ({ page }) => {
    await goToStudio(page)
    // Wait for studio to fully render
    await page.waitForTimeout(1000)
    const allButtons = page.locator('button:has(svg)')
    const totalCount = await allButtons.count()
    let unlabeledCount = 0
    let checkedCount = 0
    for (let i = 0; i < totalCount && checkedCount < 15; i++) {
      const btn = allButtons.nth(i)
      // Skip hidden buttons
      if (!await btn.isVisible({ timeout: 500 }).catch(() => false)) continue
      checkedCount++
      const ariaLabel = await btn.getAttribute('aria-label')
      const title = await btn.getAttribute('title')
      const srText = await btn.locator('.sr-only').first().textContent({ timeout: 500 }).catch(() => null)
      const text = (await btn.textContent()).trim()
      const hasLabel = ariaLabel || title || srText || text.length > 0
      if (!hasLabel) unlabeledCount++
    }
    // Allow up to 2 unlabeled icon buttons (some may be decorative)
    expect(unlabeledCount).toBeLessThanOrEqual(2)
  })

  test('sliders have aria-labelledby', async ({ page }) => {
    await goToStudio(page)
    const sliders = page.locator('[role="slider"]')
    const count = await sliders.count()
    for (let i = 0; i < count; i++) {
      const labelledBy = await sliders.nth(i).getAttribute('aria-labelledby')
      expect(labelledBy).toBeTruthy()
    }
  })

  test('checkboxes have aria-labels', async ({ page }) => {
    await goToStudio(page)
    const checkboxes = page.locator('[role="checkbox"]')
    const count = await checkboxes.count()
    for (let i = 0; i < count; i++) {
      const label = await checkboxes.nth(i).getAttribute('aria-label')
      expect(label).toBeTruthy()
    }
  })

  test('console has role="log" and aria-live', async ({ page }) => {
    await goToStudio(page)
    // StudioMainView renders a desktop and a mobile console, both role="log".
    const console_ = page.locator('[role="log"]:visible')
    await expect(console_).toHaveAttribute('aria-live', 'polite')
    await expect(console_).toHaveAttribute('aria-label', 'Render console')
  })

  test('tab navigation reaches all interactive elements', async ({ page }) => {
    await goToStudio(page)
    // Press Tab multiple times and verify focus moves
    const focusedElements = []
    for (let i = 0; i < 15; i++) {
      await page.keyboard.press('Tab')
      const tag = await page.evaluate(() => document.activeElement?.tagName)
      focusedElements.push(tag)
    }
    // Should include BUTTON, INPUT, SELECT elements
    const hasFocusableElements = focusedElements.some(t =>
      ['BUTTON', 'INPUT', 'SELECT', 'A'].includes(t)
    )
    expect(hasFocusableElements).toBe(true)
  })

  test('html lang attribute is set correctly', async ({ page }) => {
    await goToStudio(page)
    const lang = await page.evaluate(() => document.documentElement.lang)
    expect(['en', 'es']).toContain(lang)
  })

  test('html lang updates when language is toggled', async ({ page }) => {
    await goToStudio(page)
    const langBefore = await page.evaluate(() => document.documentElement.lang)
    // Open globe dropdown and select a different language
    await page.locator('button:has(.lucide-globe)').first().click()
    const dropdown = page.locator('.absolute.top-full')
    // 10s, not 3s: WebKit renders the dropdown slower than Chromium and this
    // wait exhausted all 3 retries on the webkit shard (per the config's own
    // note that tight timeouts flake across shards). A passing run is unaffected.
    await dropdown.first().waitFor({ timeout: 10000 })
    const options = dropdown.locator('button')
    const count = await options.count()
    for (let i = 0; i < count; i++) {
      const isBold = await options.nth(i).evaluate(el => el.classList.contains('font-semibold'))
      if (!isBold) {
        await options.nth(i).click()
        break
      }
    }
    await page.waitForTimeout(500)
    const langAfter = await page.evaluate(() => document.documentElement.lang)
    expect(langAfter).not.toBe(langBefore)
  })

  test('confirm dialog traps focus', async ({ page, sidebar }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } })
    })
    await goToStudio(page)
    // Scoped to the sidebar. The bare match used to resolve to 2 elements and
    // fail strict mode, because Generate was rendered once per layout tree and
    // both trees were mounted. Only the tree on screen is mounted now, so there
    // is a single Generate at this viewport; the scoping stays because naming
    // the sidebar is what makes the click unambiguous if the mobile sheet or a
    // compare slot ever grows a Generate of its own.
    await sidebar.generateButton.click()
    await page.waitForTimeout(500)
    const dialog = page.locator('[role="alertdialog"]')
    if (await dialog.isVisible()) {
      // Focus should be within the dialog
      await page.keyboard.press('Tab')
      const focused = await page.evaluate(() => {
        const el = document.activeElement
        return el?.closest('[role="alertdialog"]') !== null
      })
      expect(focused).toBe(true)
    }
  })

  test('project selector has aria-label', async ({ page }) => {
    await goToStudio(page)
    const select = page.locator('select[aria-label="Select project"]')
    if (await select.isVisible()) {
      await expect(select).toHaveAttribute('aria-label', 'Select project')
    }
  })

  test('color inputs have associated labels', async ({ page }) => {
    await goToStudio(page)
    const colorInputs = page.locator('input[type="color"]')
    const count = await colorInputs.count()
    for (let i = 0; i < count; i++) {
      const id = await colorInputs.nth(i).getAttribute('id')
      if (id) {
        const label = page.locator(`label[for="${id}"]`)
        await expect(label).toBeVisible()
      }
    }
  })

  test('value display spans are keyboard accessible', async ({ page }) => {
    await goToStudio(page)
    const valueSpans = page.locator('[role="button"][tabindex="0"]')
    const count = await valueSpans.count()
    expect(count).toBeGreaterThan(0)
    // Verify they have aria-labels
    for (let i = 0; i < count; i++) {
      const label = await valueSpans.nth(i).getAttribute('aria-label')
      expect(label).toBeTruthy()
    }
  })
})
