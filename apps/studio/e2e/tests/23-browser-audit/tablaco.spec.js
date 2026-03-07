import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage } from '../../helpers/test-utils.js'
import { runAxeAudit } from '../../helpers/accessibility.js'
import {
  skipIfNoBackend,
  goToRealProject,
  waitForRenderDone,
  waitForDownload,
} from './audit-helpers.js'

test.use({ mockAPIs: false })
test.describe.configure({ mode: 'serial' })

test.describe('Tablaco — Browser Audit', () => {
  test.beforeAll(async ({ request }, testInfo) => {
    await skipIfNoBackend(request, testInfo)
  })

  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  // ── A. Loading & Navigation ──────────────────────────────────────

  test('loads tablaco and shows "Tablaco Studio"', async ({ page }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await expect(page.locator('header h1')).toContainText('Tablaco Studio')
    const tabs = page.locator('[role="tablist"] [role="tab"]')
    await expect(tabs).toHaveCount(3)
  })

  test('default mode is unit', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/unit|unidad/i)
  })

  test('switches to assembly mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.selectMode('assembly')
    await page.waitForTimeout(500)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/assembly|ensamble/i)
  })

  test('switches to grid mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.selectMode('grid')
    await page.waitForTimeout(500)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/grid|ret/i)
  })

  test('grid mode shows rows/cols params, unit mode does not', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    // Unit mode: no rows/cols
    await expect(sidebar.slider('rows')).not.toBeVisible()
    await expect(sidebar.slider('cols')).not.toBeVisible()

    // Switch to grid
    await sidebar.selectMode('grid')
    await page.waitForTimeout(500)
    await expect(sidebar.slider('rows')).toBeVisible()
    await expect(sidebar.slider('cols')).toBeVisible()
  })

  // ── B. Parameter Controls ────────────────────────────────────────

  test('unit mode shows size and thickness sliders', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await expect(sidebar.slider('size')).toBeVisible()
    await expect(sidebar.slider('thick')).toBeVisible()
  })

  test('adjusting size slider to 25 updates value', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.editSliderValue('size', 25)
    await expect(sidebar.sliderValue('size')).toHaveText('25', { timeout: 3000 })
  })

  test('toggling show_base checkbox works', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    const cb = sidebar.checkbox('show_base')
    await expect(cb).toBeVisible()
    const wasBefore = await cb.isChecked()
    await cb.click()
    const isAfter = await cb.isChecked()
    expect(isAfter).toBe(!wasBefore)
  })

  test('applies Standard preset', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.applyPreset('Standard')
    await expect(sidebar.sliderValue('size')).toHaveText('20', { timeout: 3000 })
    await expect(sidebar.sliderValue('thick')).toHaveText('2.5', { timeout: 3000 })
  })

  test('applies Mini preset', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.applyPreset('Mini')
    await expect(sidebar.sliderValue('size')).toHaveText('5', { timeout: 3000 })
    await expect(sidebar.sliderValue('thick')).toHaveText('0.8', { timeout: 3000 })
  })

  test('visibility toggle reveals advanced controls', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    // Click Advanced toggle to show advanced params
    const toggle = sidebar.visibilityToggle()
    if (await toggle.isVisible().catch(() => false)) {
      await toggle.click()
      await page.waitForTimeout(500)
    }
    // Advanced visibility params should now be visible
    await expect(sidebar.checkbox('show_wall_left')).toBeVisible({ timeout: 3000 })
    await expect(sidebar.checkbox('show_mech_base_ring')).toBeVisible({ timeout: 3000 })
  })

  // ── C. 3D Rendering ─────────────────────────────────────────────

  test('renders unit mode with defaults', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('renders grid mode with 2x2', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.selectMode('grid')
    await page.waitForTimeout(500)
    // Ensure 2x2 grid (defaults)
    await sidebar.editSliderValue('rows', 2)
    await sidebar.editSliderValue('cols', 2)
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('toggling visibility param triggers re-render', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    // Toggle show_base off
    const cb = sidebar.checkbox('show_base')
    await cb.click()
    await waitForRenderDone(page, 120_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  // ── D. Export ────────────────────────────────────────────────────

  test('export panel shows 5 format buttons', async ({ page }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    for (const fmt of ['STL', '3MF', 'OFF', 'GLB', 'OBJ']) {
      await expect(page.getByRole('button', { name: new RegExp(fmt) })).toBeVisible()
    }
  })

  test('downloads STL file', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)

    await page.getByRole('button', { name: 'STL', exact: true }).click()
    await page.waitForTimeout(300)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download STL|Descargar STL/ }).click()
    })
    expect(suggestedFilename).toMatch(/\.stl$/i)
    expect(path).toBeTruthy()
  })

  test('downloads 3MF file', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)

    await page.getByRole('button', { name: /3MF/ }).click()
    await page.waitForTimeout(300)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download 3MF|Descargar 3MF/ }).click()
    }, 120_000)
    expect(suggestedFilename).toMatch(/\.3mf$/i)
    expect(path).toBeTruthy()
  })

  // ── E. Assembly ──────────────────────────────────────────────────

  test('assembly steps panel shows 3 steps', async ({ page }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    const assemblyBtn = page.locator('button', { hasText: /Assembly|Ensamble/ }).first()
    if (await assemblyBtn.isVisible().catch(() => false)) {
      await assemblyBtn.click()
      await page.waitForTimeout(500)
    }
    await expect(page.locator('text=/Step 1|Paso 1/')).toBeVisible({ timeout: 5000 })
  })

  test('step navigation cycles through all 3', async ({ page }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    const assemblyBtn = page.locator('button', { hasText: /Assembly|Ensamble/ }).first()
    if (await assemblyBtn.isVisible().catch(() => false)) {
      await assemblyBtn.click()
      await page.waitForTimeout(500)
    }
    // Navigate through steps
    for (let step = 2; step <= 3; step++) {
      const nextBtn = page.locator('button', { hasText: /Next|Siguiente/ }).first()
      if (await nextBtn.isVisible().catch(() => false)) {
        await nextBtn.click()
        await page.waitForTimeout(300)
      }
    }
    await expect(page.locator('text=/Step 3|Paso 3/')).toBeVisible({ timeout: 3000 })
  })

  // ── G. Accessibility ─────────────────────────────────────────────

  test('passes axe audit (no critical violations)', async ({ page }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    const results = await runAxeAudit(page, ['color-contrast'])
    const critical = results.violations.filter(v => v.impact === 'critical')
    expect(critical).toEqual([])
  })
})
