import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage, setTheme, enableClipboard, readClipboard } from '../../helpers/test-utils.js'
import {
  skipIfNoBackend,
  skipUnlessProject,
  hasProject,
  PUBLIC_AUDIT_SLUGS,
  PRIVATE_AUDIT_SLUGS,
  goToRealProject,
  waitForRenderDone,
  clickGenerateWithWarning,
  dismissRenderWarning,
} from './audit-helpers.js'

test.use({ mockAPIs: false })
test.describe.configure({ mode: 'serial' })

// projects/gridfinity/project.json declares project.name "Gridfinity"; the
// "Extended" name now belongs only to its three OpenSCAD modes.
const GRIDFINITY = 'Gridfinity'

// The mode tabs, and only those: the sidebar's section tabs
// (Design/View/BOM/Export) are a [role="tablist"] too and come FIRST in the
// DOM, so an unscoped `[role="tab"]`.first() reads "Design"/"Diseño".
const modeTabs = page =>
  page.locator('[role="tablist"][aria-label="Mode selection"] [role="tab"]').filter({ visible: true })

test.describe('Cross-Cutting — Browser Audit', () => {
  test.beforeAll(async ({ request }, testInfo) => {
    await skipIfNoBackend(request, testInfo)
  })

  // ── Theme ────────────────────────────────────────────────────────

  test('dark theme persists across page reload', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToRealProject(page, 'gridfinity', GRIDFINITY)
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
    await goToRealProject(page, 'gridfinity', GRIDFINITY)
    // Toggle to Spanish
    await header.toggleLanguage()
    await page.waitForTimeout(500)
    // Mode tabs should show Spanish labels
    const tabText = await modeTabs(page).first().textContent()
    // gridfinity modes[0] is `bin`, whose es label is "Contenedor"
    expect(tabText).toMatch(/Contenedor|Placa|Tapa/i)
  })

  test('Spanish persists across project navigation', async ({ page }) => {
    skipUnlessProject(test, 'tablaco')
    await setLanguage(page, 'es')
    await goToRealProject(page, 'gridfinity', GRIDFINITY)
    // Verify Spanish
    const tabText1 = await modeTabs(page).first().textContent()
    expect(tabText1).toMatch(/Contenedor|Placa|Tapa/i)

    // Navigate to tablaco
    await page.goto('/project/tablaco')
    await page.waitForSelector('header', { timeout: 15_000 })
    await page.waitForTimeout(1000)
    // Verify still Spanish
    const tabText2 = await modeTabs(page).first().textContent()
    expect(tabText2).toMatch(/Unidad|Ensamble|Ret/i)
  })

  // ── Share URL ────────────────────────────────────────────────────

  test('share URL generation has ?p= parameter', async ({ page, header, sidebar }) => {
    await setLanguage(page, 'en')
    await goToRealProject(page, 'gridfinity', GRIDFINITY)
    await enableClipboard(page)

    // Change a parameter to create a non-default state. grid_x, not
    // width_units: the default `bin` mode is cadquery and width_units is
    // declared visible_in_modes ["cup", "baseplate_scad", "lid"].
    await sidebar.editSliderValue('grid_x', 4)
    await page.waitForTimeout(500)

    // The edit re-arms the auto-generate, which asks before a long render — and
    // that dialog is modal, so the share click below would never land.
    await dismissRenderWarning(page, 'cancel', 3000)

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
    await goToRealProject(page, 'gridfinity', GRIDFINITY)
    await clickGenerateWithWarning(sidebar, page)
    await waitForRenderDone(page, 120_000)

    // Print estimate should appear after render
    const estimateText = page.locator('text=/Print Estimate|Estimaci/')
    await expect(estimateText).toBeVisible({ timeout: 10_000 })
  })

  // ── Projects View ────────────────────────────────────────────────

  test('projects view shows every available audit project', async ({ page }) => {
    await setLanguage(page, 'en')
    await page.goto('/projects')
    await page.waitForSelector('header', { timeout: 15_000 })
    await page.waitForTimeout(1000)

    // Verify a card for every audit project the backend serves (the private
    // cartridges only appear when this checkout includes them)
    for (const slug of [...PUBLIC_AUDIT_SLUGS, ...PRIVATE_AUDIT_SLUGS.filter(hasProject)]) {
      await expect(page.locator(`a[href="/project/${slug}"]`)).toBeVisible({ timeout: 5000 })
    }
  })
})
