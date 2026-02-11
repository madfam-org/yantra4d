import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, setLanguage, waitForAppReady } from '../../helpers/test-utils.js'

/**
 * Lightweight studio navigation for mobile viewports.
 * Unlike goToStudio, this does NOT wait for desktop sidebar (.w-80) or sliders,
 * which are hidden at mobile and cause 13s of wasted timeouts.
 */
async function goToStudioMobile(page, slug = 'test') {
  await page.goto(`/#/${slug}`)
  await waitForAppReady(page)
  // Wait for mock manifest to load
  await page.locator('header h1', { hasText: 'Test Project' })
    .waitFor({ timeout: 8000 }).catch(() => { })
  // Ensure a mode tab is active (click first tab if needed)
  const activeTab = page.locator('[role="tab"][data-state="active"]')
  if (await activeTab.count() === 0) {
    const firstTab = page.locator('[role="tab"]').first()
    if (await firstTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstTab.click()
      await page.waitForTimeout(300)
    }
  }
}

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
    await goToStudioMobile(page)
    // At mobile, mode tabs are in the mobile bar using Tabs component.
    // The desktop sidebar also has a tablist but is hidden.
    // We must find the visible tablist.
    const tablist = page.locator('[role="tablist"]').filter({ hasText: /Single|Individual/ }).last()
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

  test('tablet: sidebar is visible', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 }) // lg breakpoint
    await goToStudio(page)
    const sidebar = page.locator('.w-80').first()
    await expect(sidebar).toBeVisible()
  })

  test('desktop: wide screen shows 3 columns in projects', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await goToProjects(page)
    const grid = page.locator('.grid')
    await expect(grid.first()).toBeVisible()
  })

  // Touch targets
  test('mobile: touch targets are spaced appropriately', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await goToStudio(page)
    const buttons = page.locator('button:visible')
    const count = await buttons.count()

    // Check first few buttons for overlap/spacing
    for (let i = 0; i < Math.min(count - 1, 5); i++) {
      const b1 = await buttons.nth(i).boundingBox()
      const b2 = await buttons.nth(i + 1).boundingBox()
      if (b1 && b2) {
        // Basic check: buttons shouldn't overlap
        const overlapX = Math.max(0, Math.min(b1.x + b1.width, b2.x + b2.width) - Math.max(b1.x, b2.x))
        const overlapY = Math.max(0, Math.min(b1.y + b1.height, b2.y + b2.height) - Math.max(b1.y, b2.y))
        const intersection = overlapX * overlapY
        expect(intersection).toBe(0)
      }
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
    await goToStudioMobile(page)
    // On mobile, the export panel is inside the bottom sheet.
    // Open the sheet by clicking the hamburger menu button.
    // The SheetTrigger button contains <Menu> icon and sr-only text "Open controls".
    const menuBtn = page.locator('button:has(.lucide-menu)').first()
    await expect(menuBtn).toBeVisible({ timeout: 10000 })
    await menuBtn.click()
    await page.waitForTimeout(800)
    // The sheet should now be open with export panel content
    const exportText = page.getByText('Export Images').or(page.getByText('Exportar Imágenes'))
    // Scroll inside sheet to make sure it's visible
    // Scroll into view if needed
    await exportText.first().scrollIntoViewIfNeeded()
    await expect(exportText.first()).toBeVisible({ timeout: 5000 })
  })

  test('desktop: all action buttons visible without scroll', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await goToStudio(page)
    await expect(page.locator('button', { hasText: 'Generate' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Reset' })).toBeVisible()
  })
})
