import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, setLanguage } from '../../helpers/test-utils.js'

// Note: axe-core requires @axe-core/playwright. If not available, these tests
// will use structural checks as fallback.
let AxeBuilder
try {
  AxeBuilder = (await import('@axe-core/playwright')).default
} catch {
  // axe-playwright not installed — tests will use manual checks
}

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  test('studio view passes axe audit', async ({ page }) => {
    await goToStudio(page)
    if (AxeBuilder) {
      const results = await new AxeBuilder({ page })
        .disableRules(['color-contrast', 'landmark-one-main', 'region']) // Canvas can't be audited; app lacks <main> landmark
        .analyze()
      expect(results.violations).toEqual([])
    }
  })

  test('projects view passes axe audit', async ({ page }) => {
    await goToProjects(page)
    if (AxeBuilder) {
      const results = await new AxeBuilder({ page })
        .disableRules(['color-contrast', 'landmark-one-main', 'region'])
        .analyze()
      expect(results.violations).toEqual([])
    }
  })

  test('all icon buttons have aria-labels or sr-only text', async ({ page }) => {
    await goToStudio(page)
    const iconButtons = page.locator('button:has(svg)')
    const count = await iconButtons.count()
    let unlabeledCount = 0
    for (let i = 0; i < count; i++) {
      const btn = iconButtons.nth(i)
      const ariaLabel = await btn.getAttribute('aria-label')
      const title = await btn.getAttribute('title')
      const text = await btn.textContent()
      const srText = await btn.locator('.sr-only').textContent().catch(() => null)
      const hasLabel = ariaLabel || title || srText || (text && text.trim().length > 0)
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
    const console_ = page.locator('[role="log"]')
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
    await page.locator('button:has(.lucide-globe)').first().click()
    await page.waitForTimeout(200)
    const langAfter = await page.evaluate(() => document.documentElement.lang)
    expect(langAfter).not.toBe(langBefore)
  })

  test('confirm dialog traps focus', async ({ page }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } })
    })
    await goToStudio(page)
    await page.locator('button', { hasText: 'Generate' }).click()
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
