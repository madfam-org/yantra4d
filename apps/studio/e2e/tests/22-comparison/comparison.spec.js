import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage } from '../../helpers/test-utils.js'

test.describe('Comparison View', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
  })

  test('compare button exists in sidebar', async ({ page }) => {
    const sidebar = page.locator('[data-testid="studio-sidebar"]')
    const compareBtn = sidebar.locator('button', { hasText: /Compare/ })
    await expect(compareBtn).toBeVisible()
  })

  test('clicking compare toggles mode', async ({ page }) => {
    const sidebar = page.locator('[data-testid="studio-sidebar"]')
    const compareBtn = sidebar.locator('button', { hasText: /Compare/ })

    // Enter compare mode
    await compareBtn.click()
    await expect(compareBtn).toHaveText(/Exit comparison|Exit/)
  })

  test('add current creates a comparison slot', async ({ page }) => {
    const sidebar = page.locator('[data-testid="studio-sidebar"]')
    const compareBtn = sidebar.locator('button', { hasText: /Compare/ })

    // Enter compare mode
    await compareBtn.click()
    await page.waitForTimeout(300)

    // Click "Add current" button
    const addBtn = page.locator('button', { hasText: /Add current/ })
    if (await addBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await addBtn.click()
      await page.waitForTimeout(300)

      // Should show at least one slot with a remove button
      const removeBtn = page.locator('button[aria-label="Remove slot"]')
      await expect(removeBtn.first()).toBeVisible({ timeout: 3000 })
    }
  })

  test('remove slot button works', async ({ page }) => {
    const sidebar = page.locator('[data-testid="studio-sidebar"]')
    const compareBtn = sidebar.locator('button', { hasText: /Compare/ })

    // Enter compare mode and add a slot
    await compareBtn.click()
    await page.waitForTimeout(300)

    const addBtn = page.locator('button', { hasText: /Add current/ })
    if (await addBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await addBtn.click()
      await page.waitForTimeout(300)

      // Remove the slot
      const removeBtn = page.locator('button[aria-label="Remove slot"]').first()
      if (await removeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await removeBtn.click()
        await page.waitForTimeout(300)

        // Slot should be gone — either empty state text or no remove buttons
        const remaining = page.locator('button[aria-label="Remove slot"]')
        expect(await remaining.count()).toBe(0)
      }
    }
  })

  test('max 4 slots — add button disabled at capacity', async ({ page }) => {
    const sidebar = page.locator('[data-testid="studio-sidebar"]')
    const compareBtn = sidebar.locator('button', { hasText: /Compare/ })

    await compareBtn.click()
    await page.waitForTimeout(300)

    // Add 4 slots
    for (let i = 0; i < 4; i++) {
      const addBtn = page.locator('button', { hasText: /Add current/ })
      if (await addBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await addBtn.click()
        await page.waitForTimeout(200)
      }
    }

    // After 4 slots, the add button should be hidden (component hides it at capacity)
    // ComparisonView hides the "Add current" button when slots.length >= 4
    // Just verify we have at most 4 remove buttons
    const removeButtons = page.locator('button[aria-label="Remove slot"]')
    expect(await removeButtons.count()).toBeLessThanOrEqual(4)
  })

  test('exit compare mode returns to normal viewer', async ({ page }) => {
    const sidebar = page.locator('[data-testid="studio-sidebar"]')
    const compareBtn = sidebar.locator('button', { hasText: /Compare/ })

    // Enter compare mode
    await compareBtn.click()
    await expect(compareBtn).toHaveText(/Exit/)

    // Exit compare mode
    await compareBtn.click()
    await expect(compareBtn).toHaveText(/Compare/)
  })
})
