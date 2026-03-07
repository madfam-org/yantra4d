import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage, setTheme, enableClipboard, readClipboard } from '../../helpers/test-utils.js'
import {
  skipIfNoBackend,
  goToRealProject,
  waitForRenderDone,
} from './audit-helpers.js'

test.use({ mockAPIs: false })
test.describe.configure({ mode: 'serial' })

test.describe('Cross-Cutting — Browser Audit', () => {
  test.beforeAll(async ({ request }, testInfo) => {
    await skipIfNoBackend(request, testInfo)
  })

  // ── Theme ────────────────────────────────────────────────────────

  test('dark theme persists across page reload', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    // Verify dark class is on html element
    await expect(page.locator('html')).toHaveClass(/dark/)
    // Reload and check persistence
    await page.reload()
    await page.waitForSelector('header', { timeout: 15_000 })
    await expect(page.locator('html')).toHaveClass(/dark/)
  })

  // ── Language ─────────────────────────────────────────────────────

  test('language toggle switches to Spanish', async ({ page, header }) => {
    await setLanguage(page, 'en')
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    // Toggle to Spanish
    await header.toggleLanguage()
    await page.waitForTimeout(500)
    // Mode tabs should show Spanish labels
    const tabText = await page.locator('[role="tablist"] [role="tab"]').first().textContent()
    // Gridfinity modes in ES: Contenedor, Placa Base, Tapa
    expect(tabText).toMatch(/Contenedor|Placa|Tapa/i)
  })

  test('Spanish persists across project navigation', async ({ page }) => {
    await setLanguage(page, 'es')
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    // Verify Spanish
    const tabText1 = await page.locator('[role="tablist"] [role="tab"]').first().textContent()
    expect(tabText1).toMatch(/Contenedor|Placa|Tapa/i)

    // Navigate to tablaco
    await page.goto('/project/tablaco')
    await page.waitForSelector('header', { timeout: 15_000 })
    await page.waitForTimeout(1000)
    // Verify still Spanish
    const tabText2 = await page.locator('[role="tablist"] [role="tab"]').first().textContent()
    expect(tabText2).toMatch(/Unidad|Ensamble|Ret/i)
  })

  // ── Share URL ────────────────────────────────────────────────────

  test('share URL generation has ?p= parameter', async ({ page, header, sidebar }) => {
    await setLanguage(page, 'en')
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await enableClipboard(page)

    // Change a parameter to create a non-default state
    await sidebar.editSliderValue('width_units', 4)
    await page.waitForTimeout(500)

    // Click share button
    await header.clickShare()
    await page.waitForTimeout(1000)

    // Check clipboard for share URL with ?p= parameter
    const clipText = await readClipboard(page)
    expect(clipText).toContain('?p=')
  })

  // ── Print Estimate ───────────────────────────────────────────────

  test('print estimate overlay shows after render', async ({ page, sidebar }) => {
    await setLanguage(page, 'en')
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)

    // Print estimate should appear after render
    const estimateText = page.locator('text=/Print Estimate|Estimaci/')
    await expect(estimateText).toBeVisible({ timeout: 10_000 })
  })

  // ── Projects View ────────────────────────────────────────────────

  test('projects view shows all three audit projects', async ({ page }) => {
    await setLanguage(page, 'en')
    await page.goto('/projects')
    await page.waitForSelector('header', { timeout: 15_000 })
    await page.waitForTimeout(1000)

    // Verify cards for all 3 audit projects
    for (const slug of ['gridfinity', 'tablaco', 'custom-msh']) {
      await expect(page.locator(`a[href="/project/${slug}"]`)).toBeVisible({ timeout: 5000 })
    }
  })
})
