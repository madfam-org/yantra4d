import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage } from '../../helpers/test-utils.js'
import { runAxeAudit } from '../../helpers/accessibility.js'
import {
  skipIfNoBackend,
  goToRealProject,
  waitForRenderDone,
  triggerAndWaitRender,
  clickGenerateWithWarning,
  dismissRenderWarning,
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
    // Mode tabs are in the second tablist (first is header nav)
    const modeTabs = page.locator('[role="tablist"]').nth(1).locator('[role="tab"]')
    await expect(modeTabs).toHaveCount(3)
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

  test('letter_bottom text input accepts single character', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    const input = sidebar.textInput('letter_bottom')
    await expect(input).toBeVisible()
    await expect(input).toHaveAttribute('maxlength', '1')
  })

  test('letter_emboss checkbox toggles', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    const cb = sidebar.checkbox('letter_emboss')
    await expect(cb).toBeVisible()
    expect(await cb.isChecked()).toBe(false)
    // Scroll into view above sticky Generate bar, then click
    await cb.scrollIntoViewIfNeeded()
    await page.waitForTimeout(200)
    await cb.dispatchEvent('click')
    await page.waitForTimeout(300)
    expect(await cb.isChecked()).toBe(true)
  })

  test('assembly mode shows show_bottom/show_top checkboxes', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.selectMode('assembly')
    await page.waitForTimeout(500)
    const bottom = sidebar.checkbox('show_bottom')
    const top = sidebar.checkbox('show_top')
    await expect(bottom).toBeVisible()
    await expect(top).toBeVisible()
    expect(await bottom.isChecked()).toBe(true)
    expect(await top.isChecked()).toBe(true)
  })

  test('grid mode shows grid-specific sliders', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.selectMode('grid')
    await page.waitForTimeout(500)
    await expect(sidebar.slider('rod_extension')).toBeVisible()
    await expect(sidebar.slider('rotation_clearance')).toBeVisible()
    await expect(sidebar.slider('tubing_H')).toBeVisible()
    await expect(sidebar.slider('tubing_wall')).toBeVisible()
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
    await page.waitForTimeout(1000)
    await clickGenerateWithWarning(sidebar, page)
    await waitForRenderDone(page, 180_000)
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

  test('renders assembly mode with both halves', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.selectMode('assembly')
    await page.waitForTimeout(1000)
    await clickGenerateWithWarning(sidebar, page)
    await waitForRenderDone(page, 180_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('changing size to 15 triggers re-render', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await triggerAndWaitRender(sidebar, page, 'size', 15, 120_000)
    const generateBtn = page.locator('button', { hasText: /Generate|Generar/ }).first()
    await expect(generateBtn).toBeEnabled()
  })

  test('model info shows dimensions after render', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    // Model info panel shows dimensions with multiplication sign
    const dimText = page.locator('text=/\\d+.*\\u00d7.*\\d+/')
    await expect(dimText.first()).toBeVisible({ timeout: 5000 })
  })

  test('assembly renders at size 25mm', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    // Set size to 25 in unit mode (before switching to assembly) to avoid dialog race
    await sidebar.editSliderValue('size', 25)
    await sidebar.selectMode('assembly')
    await page.waitForTimeout(1000)
    await clickGenerateWithWarning(sidebar, page)
    await waitForRenderDone(page, 180_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  // ── D. Export ────────────────────────────────────────────────────

  test('export panel shows 5 format buttons', async ({ page }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    // Switch to Export section tab (format buttons live inside it)
    await page.locator('[data-testid="studio-sidebar"] [role="tab"]', { hasText: /Export|Exportar/ }).click()
    await page.waitForTimeout(300)
    for (const fmt of ['STL', '3MF', 'OFF', 'GLB', 'OBJ']) {
      await expect(page.getByRole('button', { name: fmt, exact: true })).toBeVisible()
    }
  })

  test('downloads STL file', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)

    // Switch to Export section tab
    await page.locator('[data-testid="studio-sidebar"] [role="tab"]', { hasText: /Export|Exportar/ }).click()
    await page.waitForTimeout(500)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download STL|Descargar STL/ }).click()
    })
    // Backend auto-converts STL→GLB for web delivery; accept either format
    expect(suggestedFilename).toMatch(/\.(stl|glb)$/i)
    expect(path).toBeTruthy()
  })

  test('downloads 3MF file', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)

    // Switch to Export section tab
    await page.locator('[data-testid="studio-sidebar"] [role="tab"]', { hasText: /Export|Exportar/ }).click()
    await page.waitForTimeout(500)
    await page.getByRole('button', { name: '3MF', exact: true }).click()
    await page.waitForTimeout(500)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download 3MF|Descargar 3MF/ }).click()
    }, 120_000)
    // Backend may auto-convert to GLB for web delivery; accept either format
    expect(suggestedFilename).toMatch(/\.(3mf|glb)$/i)
    expect(path).toBeTruthy()
  })

  // ── E. Assembly ──────────────────────────────────────────────────

  test('assembly steps panel shows steps', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.selectMode('assembly')
    await dismissRenderWarning(page)
    // Click BOM/Analysis section tab where assembly steps are rendered
    await page.locator('[data-testid="studio-sidebar"] [role="tab"]', { hasText: /BOM/ }).click()
    await page.waitForTimeout(500)
    await expect(page.locator('text=/Step 1|Paso 1/')).toBeVisible({ timeout: 5000 })
  })

  test('step navigation cycles through all 3', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.selectMode('assembly')
    await dismissRenderWarning(page)
    // Click BOM/Analysis section tab
    await page.locator('[data-testid="studio-sidebar"] [role="tab"]', { hasText: /BOM/ }).click()
    await page.waitForTimeout(500)
    // Navigate through steps using the next-step button (aria-label="Next step")
    for (let step = 2; step <= 3; step++) {
      const nextBtn = page.locator('button[aria-label*="Next"], button[aria-label*="Siguiente"]').first()
      await nextBtn.click()
      await page.waitForTimeout(300)
    }
    await expect(page.locator('text=/Step 3|Paso 3/')).toBeVisible({ timeout: 3000 })
  })

  // ── F. URL & Camera ─────────────────────────────────────────

  test('URL updates on mode switch', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.selectMode('assembly')
    await dismissRenderWarning(page)
    const assemblyPath = await page.evaluate(() => window.location.pathname)
    expect(assemblyPath).toContain('/project/tablaco/')
    expect(assemblyPath).toContain('assembly')

    await sidebar.selectMode('grid')
    await dismissRenderWarning(page)
    const gridPath = await page.evaluate(() => window.location.pathname)
    expect(gridPath).toContain('/project/tablaco/')
    expect(gridPath).toContain('grid')
  })

  test('camera views switch correctly', async ({ page, sidebar }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    for (const view of ['top', 'front', 'right']) {
      const btn = page.locator('button', { hasText: new RegExp(view, 'i') }).first()
      if (await btn.isVisible().catch(() => false)) {
        await btn.click()
        await page.waitForTimeout(300)
      }
    }
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  // ── G. Accessibility ─────────────────────────────────────────────

  test('passes axe audit (no critical violations)', async ({ page }) => {
    await goToRealProject(page, 'tablaco', 'Tablaco Studio')
    const results = await runAxeAudit(page, ['color-contrast'])
    const critical = results.violations.filter(v => v.impact === 'critical')
    expect(critical).toEqual([])
  })
})
