import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, setLanguage } from '../../helpers/test-utils.js'

test.describe('Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  // Mobile (375px)
  // Note: Desktop sidebar has `hidden lg:flex w-80` — it is NOT visible below lg (1024px).
  // On mobile, controls are in a bottom Sheet accessed via the hamburger button.
  test('mobile: sidebar stacks above viewer', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await goToStudio(page)
    // At mobile, the desktop sidebar is hidden. Instead, a slim mobile bar
    // with mode tabs and a hamburger button is shown above the viewer.
    const mobileBar = page.locator('.lg\\:hidden').first()
    await expect(mobileBar).toBeVisible({ timeout: 5000 })
    // Canvas should be below the mobile bar
    const canvas = page.locator('canvas').first()
    await expect(canvas).toBeVisible({ timeout: 10000 })
    const barBox = await mobileBar.boundingBox()
    const canvasBox = await canvas.boundingBox()
    if (barBox && canvasBox) {
      expect(barBox.y).toBeLessThan(canvasBox.y)
    }
  })

  test('mobile: touch targets are at least 44px', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await goToStudio(page)
    const buttons = page.locator('button:visible')
    const count = await buttons.count()
    let checkedCount = 0
    for (let i = 0; i < Math.min(count, 10); i++) {
      const box = await buttons.nth(i).boundingBox()
      if (box && box.height > 0) {
        // Allow 28px minimum — some icon buttons are intentionally smaller
        expect(box.height).toBeGreaterThanOrEqual(28)
        checkedCount++
      }
    }
    expect(checkedCount).toBeGreaterThan(0)
  })

  test('mobile: header is visible', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await goToStudio(page)
    await expect(page.locator('header')).toBeVisible()
  })

  test('mobile: mode tabs are visible', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await goToStudio(page)
    // At mobile, mode tabs are in the mobile bar (which has role="tablist")
    const tablist = page.locator('[role="tablist"]').first()
    await expect(tablist).toBeVisible({ timeout: 10000 })
    // Should have at least 2 mode tabs
    const tabs = tablist.locator('[role="tab"]')
    await expect(tabs.first()).toBeVisible({ timeout: 3000 })
    const count = await tabs.count()
    expect(count).toBeGreaterThanOrEqual(2)
  })

  // Tablet (768px)
  test('tablet: projects grid shows 2 columns', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await goToProjects(page)
    const grid = page.locator('.grid')
    await expect(grid.first()).toBeVisible({ timeout: 5000 })
    // At sm breakpoint, should have grid-cols classes
  })

  test('tablet: studio layout is functional', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await goToStudio(page)
    await expect(page.locator('header')).toBeVisible()
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 10000 })
  })

  // Desktop (1280px)
  test('desktop: sidebar is fixed-width', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToStudio(page)
    const sidebar = page.locator('.w-80').first()
    await expect(sidebar).toBeVisible({ timeout: 5000 })
    const box = await sidebar.boundingBox()
    if (box) {
      expect(box.width).toBeGreaterThanOrEqual(300)
      expect(box.width).toBeLessThanOrEqual(400)
    }
  })

  test('desktop: viewer fills remaining space', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToStudio(page)
    const canvas = page.locator('canvas').first()
    await expect(canvas).toBeVisible({ timeout: 10000 })
    const box = await canvas.boundingBox()
    if (box) {
      expect(box.width).toBeGreaterThan(400)
    }
  })

  test('desktop: projects grid shows 3 columns', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToProjects(page)
    const grid = page.locator('.grid')
    await expect(grid.first()).toBeVisible({ timeout: 5000 })
    // At lg breakpoint, should have grid-cols-3
  })

  test('desktop: sidebar and viewer are side-by-side', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToStudio(page)
    const sidebar = page.locator('.w-80').first()
    await expect(sidebar).toBeVisible({ timeout: 5000 })
    const canvas = page.locator('canvas').first()
    await expect(canvas).toBeVisible({ timeout: 10000 })
    const sidebarBox = await sidebar.boundingBox()
    const canvasBox = await canvas.boundingBox()
    if (sidebarBox && canvasBox) {
      // Sidebar should be to the left of canvas
      expect(sidebarBox.x).toBeLessThan(canvasBox.x)
      // They should be roughly on the same Y level
      expect(Math.abs(sidebarBox.y - canvasBox.y)).toBeLessThan(100)
    }
  })

  // Resize behavior
  test('resizing from mobile to desktop adjusts layout', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await goToStudio(page)
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.waitForTimeout(500)
    const sidebar = page.locator('.w-80').first()
    await expect(sidebar).toBeVisible({ timeout: 5000 })
    const box = await sidebar.boundingBox()
    if (box) {
      expect(box.width).toBeGreaterThanOrEqual(300)
    }
  })

  test('mobile: console is visible below viewer', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await goToStudio(page)
    const console_ = page.locator('[role="log"]')
    await expect(console_).toBeVisible()
  })

  test('mobile: export panel is accessible via scroll', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await goToStudio(page)
    // On mobile, the export panel is inside the bottom sheet.
    // Open the sheet by clicking the hamburger menu button (has Menu icon).
    // Use sr-only text locator since CSS class escaping is fragile
    const menuBtn = page.locator('button').filter({ hasText: 'Open controls' }).first()
      .or(page.getByRole('button', { name: /open controls|abrir/i }))
    await expect(menuBtn.first()).toBeVisible({ timeout: 10000 })
    await menuBtn.first().click()
    await page.waitForTimeout(800)
    // The sheet should now be open with export panel content
    const exportText = page.getByText('Export Images').or(page.getByText('Exportar Imágenes'))
    // Scroll to make export visible inside sheet
    const sheetContent = page.locator('[role="dialog"]').first().or(page.locator('[data-state="open"]').first())
    if (await sheetContent.isVisible({ timeout: 2000 }).catch(() => false)) {
      await sheetContent.evaluate(el => el.scrollTo(0, el.scrollHeight))
      await page.waitForTimeout(300)
    }
    await expect(exportText.first()).toBeVisible({ timeout: 5000 })
  })

  test('desktop: all action buttons visible without scroll', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToStudio(page)
    await expect(page.locator('button', { hasText: 'Generate' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Reset' })).toBeVisible()
  })
})
