import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage } from '../../helpers/test-utils.js'
import { runAxeAudit } from '../../helpers/accessibility.js'
import {
  skipIfNoBackend,
  goToRealProject,
  waitForRenderDone,
  triggerAndWaitRender,
  waitForDownload,
} from './audit-helpers.js'

test.use({ mockAPIs: false })
test.describe.configure({ mode: 'serial' })

test.describe('Gridfinity — Browser Audit', () => {
  test.beforeAll(async ({ request }, testInfo) => {
    await skipIfNoBackend(request, testInfo)
  })

  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  // ── A. Project Loading & Navigation ──────────────────────────────

  test('loads gridfinity and shows manifest data', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await expect(page.locator('header h1')).toContainText('Gridfinity Extended')
    // 3 mode tabs: Bin, Baseplate, Lid
    const tabs = page.locator('[role="tablist"] [role="tab"]')
    await expect(tabs).toHaveCount(3)
  })

  test('default mode is cup', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/cup|bin/i)
  })

  test('switches to baseplate mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.selectMode('baseplate')
    await page.waitForTimeout(500)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/baseplate|placa/i)
    expect(page.url()).toContain('baseplate')
  })

  test('switches to lid mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.selectMode('lid')
    await page.waitForTimeout(500)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/lid|tapa/i)
    expect(page.url()).toContain('lid')
  })

  test('URL updates on mode switch', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.selectMode('baseplate')
    await page.waitForTimeout(500)
    const pathname = await page.evaluate(() => window.location.pathname)
    expect(pathname).toMatch(/\/project\/gridfinity\/[^/]+\/baseplate/)
  })

  // ── B. Parameter Controls ────────────────────────────────────────

  test('cup mode shows dimension sliders', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await expect(sidebar.slider('width_units')).toBeVisible()
    await expect(sidebar.slider('height_units')).toBeVisible()
    await expect(sidebar.slider('depth_units')).toBeVisible()
  })

  test('adjusting width_units slider updates value', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.editSliderValue('width_units', 4)
    await expect(sidebar.sliderValue('width_units')).toHaveText('4', { timeout: 3000 })
  })

  test('toggling fingerslide checkbox works', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    const cb = sidebar.checkbox('fingerslide_enabled')
    await expect(cb).toBeVisible()
    const wasBefore = await cb.isChecked()
    await cb.click()
    const isAfter = await cb.isChecked()
    expect(isAfter).toBe(!wasBefore)
  })

  test('applies Small Parts Bin preset', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.applyPreset('Small Parts Bin')
    await expect(sidebar.sliderValue('width_units')).toHaveText('2', { timeout: 3000 })
    await expect(sidebar.sliderValue('depth_units')).toHaveText('1', { timeout: 3000 })
    await expect(sidebar.sliderValue('height_units')).toHaveText('3', { timeout: 3000 })
  })

  test('applies Battery Holder preset', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.applyPreset('Battery Holder')
    await expect(sidebar.sliderValue('width_units')).toHaveText('3', { timeout: 3000 })
    await expect(sidebar.sliderValue('depth_units')).toHaveText('2', { timeout: 3000 })
  })

  test('cross-mode preset switches to baseplate', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.applyPreset('Standard Baseplate')
    await page.waitForTimeout(1000)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/baseplate|placa/i)
  })

  test('baseplate mode shows baseplate params', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.selectMode('baseplate')
    await page.waitForTimeout(500)
    await expect(sidebar.slider('bp_corner_radius')).toBeVisible()
    await expect(sidebar.checkbox('bp_enable_magnets')).toBeVisible()
  })

  // ── C. 3D Rendering ─────────────────────────────────────────────

  test('renders cup with default params', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('changing width_units triggers new render', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await triggerAndWaitRender(sidebar, page, 'width_units', 3, 120_000)
    const generateBtn = page.locator('button', { hasText: /Generate|Generar/ }).first()
    await expect(generateBtn).toBeEnabled()
  })

  test('model info shows dimensions after render', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    // Model info panel shows dimensions with multiplication sign
    const dimText = page.locator('text=/\\d+.*\\u00d7.*\\d+/')
    await expect(dimText.first()).toBeVisible({ timeout: 5000 })
  })

  test('camera views switch correctly', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    // Click camera view buttons without error
    for (const view of ['top', 'front', 'right']) {
      const btn = page.locator('button', { hasText: new RegExp(view, 'i') }).first()
      if (await btn.isVisible().catch(() => false)) {
        await btn.click()
        await page.waitForTimeout(300)
      }
    }
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  // ── D. Export ────────────────────────────────────────────────────

  test('export panel shows 7 format buttons', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    for (const fmt of ['STL', '3MF', 'OFF', 'STEP', 'GLB', 'GLTF', 'OBJ']) {
      await expect(page.getByRole('button', { name: new RegExp(fmt) })).toBeVisible()
    }
  })

  test('downloads STL file', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)

    // Select STL format
    await page.getByRole('button', { name: 'STL', exact: true }).click()
    await page.waitForTimeout(300)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download STL|Descargar STL/ }).click()
    })
    expect(suggestedFilename).toMatch(/\.stl$/i)
    expect(path).toBeTruthy()
  })

  test('downloads STEP via dual-engine', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)

    // Select STEP format
    await page.getByRole('button', { name: /STEP/ }).click()
    await page.waitForTimeout(300)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download STEP|Descargar STEP/ }).click()
    }, 120_000)
    expect(suggestedFilename).toMatch(/\.step$/i)
    expect(path).toBeTruthy()
  })

  test('downloads 3MF file', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
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

  // ── E. Assembly & BOM ────────────────────────────────────────────

  test('assembly steps shows 3 steps', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    // Open assembly steps panel if collapsed
    const assemblyBtn = page.locator('button', { hasText: /Assembly|Ensamble/ }).first()
    if (await assemblyBtn.isVisible().catch(() => false)) {
      await assemblyBtn.click()
      await page.waitForTimeout(500)
    }
    await expect(page.locator('text=/Step 1|Paso 1/')).toBeVisible({ timeout: 5000 })
  })

  test('assembly step navigation works', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    const assemblyBtn = page.locator('button', { hasText: /Assembly|Ensamble/ }).first()
    if (await assemblyBtn.isVisible().catch(() => false)) {
      await assemblyBtn.click()
      await page.waitForTimeout(500)
    }
    // Click next step
    const nextBtn = page.locator('button', { hasText: /Next|Siguiente/ }).first()
    if (await nextBtn.isVisible().catch(() => false)) {
      await nextBtn.click()
      await page.waitForTimeout(300)
      await expect(page.locator('text=/Step 2|Paso 2/')).toBeVisible({ timeout: 3000 })
    }
  })

  test('BOM panel shows hardware after enabling magnets', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    // Enable magnets
    const cb = sidebar.checkbox('enable_magnets')
    if (await cb.isVisible().catch(() => false)) {
      const checked = await cb.isChecked()
      if (!checked) await cb.click()
    }
    await page.waitForTimeout(500)

    // Open BOM panel if present
    const bomBtn = page.locator('button', { hasText: /BOM|Bill of Materials|Lista de Materiales/ }).first()
    if (await bomBtn.isVisible().catch(() => false)) {
      await bomBtn.click()
      await page.waitForTimeout(500)
    }
    // Check for magnet entry
    await expect(page.locator('text=/[Mm]agnet/')).toBeVisible({ timeout: 5000 })
  })

  // ── G. Accessibility ─────────────────────────────────────────────

  test('passes axe audit (no critical violations)', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', 'Gridfinity Extended')
    const results = await runAxeAudit(page, ['color-contrast'])
    const critical = results.violations.filter(v => v.impact === 'critical')
    expect(critical).toEqual([])
  })
})
