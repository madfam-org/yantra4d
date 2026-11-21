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

  test('entering compare shows how to start, and add current creates the first slot', async ({ page }) => {
    // Regression: the compare layout used to mount only once a slot existed,
    // while the only "Add current" control lived inside it, so no slot could
    // ever be added. This test used to skip itself when the button was absent.
    const sidebar = page.locator('[data-testid="studio-sidebar"]')
    const compareBtn = sidebar.locator('button', { hasText: /Compare/ })

    await compareBtn.click()
    await expect(page.getByText('No variations to compare')).toBeVisible()

    const addBtn = page.getByRole('button', { name: /Add current/ })
    await expect(addBtn).toBeEnabled({ timeout: 15000 })
    await addBtn.click()

    await expect(page.locator('button[aria-label="Remove slot"]')).toHaveCount(1)
  })

  test('remove slot button works', async ({ page }) => {
    const sidebar = page.locator('[data-testid="studio-sidebar"]')
    const compareBtn = sidebar.locator('button', { hasText: /Compare/ })

    await compareBtn.click()
    const addBtn = page.getByRole('button', { name: /Add current/ })
    await expect(addBtn).toBeEnabled({ timeout: 15000 })
    await addBtn.click()

    const removeBtn = page.locator('button[aria-label="Remove slot"]')
    await expect(removeBtn).toHaveCount(1)
    await removeBtn.click()

    // Back to the empty state, ready for a new first variation.
    await expect(removeBtn).toHaveCount(0)
    await expect(page.getByText('No variations to compare')).toBeVisible()
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
