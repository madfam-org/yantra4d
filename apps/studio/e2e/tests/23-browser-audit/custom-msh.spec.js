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

const PROJECT_NAME = 'Custom MSH'

test.describe('Custom MSH — Browser Audit', () => {
  test.beforeAll(async ({ request }, testInfo) => {
    await skipIfNoBackend(request, testInfo)
  })

  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  // ── A. Loading & Navigation ──────────────────────────────────────

  test('loads custom-msh and shows project name', async ({ page }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await expect(page.locator('header h1')).toContainText(PROJECT_NAME)
    // 6 mode tabs
    const tabs = page.locator('[role="tablist"] [role="tab"]')
    await expect(tabs).toHaveCount(6)
  })

  test('default mode is holder', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/holder|soporte/i)
  })

  test('switches to rack mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.selectMode('rack')
    await page.waitForTimeout(500)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/rack/i)
  })

  test('switches to box mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.selectMode('box')
    await page.waitForTimeout(500)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/box|caja/i)
  })

  test('switches to assembly mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.selectMode('assembly')
    await page.waitForTimeout(500)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/assembly|ensambl/i)
  })

  test('all 6 modes are navigable', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    const modeIds = ['holder', 'rack', 'box', 'base', 'lid', 'assembly']
    for (const modeId of modeIds) {
      await sidebar.selectMode(modeId)
      await page.waitForTimeout(500)
      // Just verify no crash and URL updates
      expect(page.url()).toContain('custom-msh')
    }
  })

  // ── B. Parameter Controls ────────────────────────────────────────

  test('holder mode shows substrate_length, substrate_width, and holder_thickness', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await expect(sidebar.slider('substrate_length')).toBeVisible()
    await expect(sidebar.slider('substrate_width')).toBeVisible()
    await expect(sidebar.slider('holder_thickness')).toBeVisible()
  })

  test('adjusting substrate_length to 26 updates value', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.editSliderValue('substrate_length', 26)
    await expect(sidebar.sliderValue('substrate_length')).toHaveText('26', { timeout: 3000 })
  })

  test('toggling label_area checkbox works', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    const cb = sidebar.checkbox('label_area')
    await expect(cb).toBeVisible()
    const wasBefore = await cb.isChecked()
    await cb.click()
    const isAfter = await cb.isChecked()
    expect(isAfter).toBe(!wasBefore)
  })

  test('applies Default Holder preset', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.applyPreset('Default Holder')
    await expect(sidebar.sliderValue('substrate_length')).toHaveText('25.4', { timeout: 3000 })
    await expect(sidebar.sliderValue('holder_thickness')).toHaveText('2', { timeout: 3000 })
  })

  test('applies Default Staining Rack preset in rack mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.selectMode('rack')
    await page.waitForTimeout(500)
    await sidebar.applyPreset('Default Staining Rack')
    await expect(sidebar.sliderValue('num_slots')).toHaveText('10', { timeout: 3000 })
  })

  test('assembly presets control assembly_level', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.selectMode('assembly')
    await page.waitForTimeout(500)
    // Apply the rack+slides assembly preset (assembly_level=1)
    await sidebar.applyPreset('Staining rack WITH')
    await page.waitForTimeout(500)
    // Verify preset button is highlighted
    const presetBtn = sidebar.presetButton('Staining rack WITH')
    await expect(presetBtn).toHaveClass(/bg-primary/, { timeout: 3000 })
  })

  // ── C. 3D Rendering ─────────────────────────────────────────────

  test('renders holder mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('renders rack mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.selectMode('rack')
    await page.waitForTimeout(500)
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('renders box mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.selectMode('box')
    await page.waitForTimeout(500)
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('assembly mode renders (may be multi-part)', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.selectMode('assembly')
    await page.waitForTimeout(500)
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  // ── D. Export ────────────────────────────────────────────────────

  test('export panel shows 5 format buttons', async ({ page }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    for (const fmt of ['STL', '3MF', 'OFF', 'GLB', 'OBJ']) {
      await expect(page.getByRole('button', { name: new RegExp(fmt) })).toBeVisible()
    }
  })

  test('downloads STL for holder mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
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

  test('downloads GLB for holder mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    await sidebar.clickGenerate()
    await waitForRenderDone(page, 120_000)

    await page.getByRole('button', { name: /GLB/ }).click()
    await page.waitForTimeout(300)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download GLB|Descargar GLB/ }).click()
    })
    expect(suggestedFilename).toMatch(/\.glb$/i)
    expect(path).toBeTruthy()
  })

  // ── G. Accessibility ─────────────────────────────────────────────

  test('passes axe audit (no critical violations)', async ({ page }) => {
    await goToRealProject(page, 'custom-msh', PROJECT_NAME)
    const results = await runAxeAudit(page, ['color-contrast'])
    const critical = results.violations.filter(v => v.impact === 'critical')
    expect(critical).toEqual([])
  })
})
