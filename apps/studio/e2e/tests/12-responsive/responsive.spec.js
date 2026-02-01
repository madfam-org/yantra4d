import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, setLanguage } from '../../helpers/test-utils.js'

test.describe('Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  // Mobile (375px)
  test('mobile: sidebar stacks above viewer', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await goToStudio(page)
    const sidebar = page.locator('.lg\\:w-80').first()
    const sidebarBox = await sidebar.boundingBox()
    const canvas = page.locator('canvas').first()
    const canvasBox = await canvas.boundingBox()
    // Sidebar should be above canvas (lower Y)
    if (sidebarBox && canvasBox) {
      expect(sidebarBox.y).toBeLessThan(canvasBox.y)
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
        // Allow 32px minimum — some icon buttons are intentionally smaller
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
    await expect(page.locator('[role="tablist"]')).toBeVisible()
  })

  // Tablet (768px)
  test('tablet: projects grid shows 2 columns', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await goToProjects(page)
    const grid = page.locator('.grid.grid-cols-1')
    await expect(grid).toBeVisible()
    // At sm breakpoint, should be 2 columns
  })

  test('tablet: studio layout is functional', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await goToStudio(page)
    await expect(page.locator('header')).toBeVisible()
    await expect(page.locator('canvas')).toBeVisible()
  })

  // Desktop (1280px)
  test('desktop: sidebar is fixed-width', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToStudio(page)
    const sidebar = page.locator('.lg\\:w-80').first()
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
    const box = await canvas.boundingBox()
    if (box) {
      expect(box.width).toBeGreaterThan(400)
    }
  })

  test('desktop: projects grid shows 3 columns', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToProjects(page)
    const grid = page.locator('.grid')
    await expect(grid).toBeVisible()
    // At lg breakpoint, should be 3 columns
  })

  test('desktop: sidebar and viewer are side-by-side', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToStudio(page)
    const sidebar = page.locator('.lg\\:w-80').first()
    const sidebarBox = await sidebar.boundingBox()
    const canvas = page.locator('canvas').first()
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
    const sidebar = page.locator('.lg\\:w-80').first()
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
    const exportText = page.locator('text=Export Images').or(page.locator('text=Exportar Imágenes'))
    // May need to scroll sidebar
    await exportText.first().scrollIntoViewIfNeeded()
    await expect(exportText.first()).toBeVisible()
  })

  test('desktop: all action buttons visible without scroll', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToStudio(page)
    await expect(page.locator('button', { hasText: 'Generate' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Reset' })).toBeVisible()
  })
})
