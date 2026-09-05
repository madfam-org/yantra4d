import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage } from '../../helpers/test-utils.js'
import { runAxeAudit } from '../../helpers/accessibility.js'
import {
  skipIfNoBackend,
  goToRealProject,
  waitForRenderDone,
  triggerAndWaitRender,
  waitForDownload,
  clickGenerateWithWarning,
  fetchManifest,
  drainRenderQueue,
} from './audit-helpers.js'

test.use({ mockAPIs: false })
test.describe.configure({ mode: 'serial' })

// projects/gridfinity/project.json declares project.name "Gridfinity".
//
// Rewritten 2026-09-04: the cartridge is CadQuery-only now. Its OpenSCAD side
// (modes `cup`, `baseplate_scad`, `lid`, the "(OpenSCAD Extended)" labels, the
// width_units/depth_units/height_units trio, bp_corner_radius,
// bp_enable_magnets and the duplicated preset labels) left the commons with
// the gridfinity_extended gitlink. What remains is 2 modes, 10 parameters and
// 3 presets — every assertion below is read from that manifest.
const PROJECT_NAME = 'Gridfinity'

test.describe('Gridfinity — Browser Audit', () => {
  test.beforeAll(async ({ request }, testInfo) => {
    await skipIfNoBackend(request, testInfo, ['gridfinity'])
  })

  // One worker serves the whole suite and nothing else empties its queue: the
  // Studio does not cancel an in-flight render when the page goes away, so a
  // test that leaves mid-render abandons work the worker still has to finish.
  // Run #171 starved gridfinity's first render test that way, from custom-msh's
  // failing assembly group re-rendering every part on each serial-mode retry.
  // Drain after a failure — which is when work is abandoned — and once at the
  // end, so the next group starts on an empty queue.
  test.afterEach(async ({ request }, testInfo) => {
    if (testInfo.status !== testInfo.expectedStatus) {
      await drainRenderQueue(request, `failed test "${testInfo.title}"`)
    }
  })

  test.afterAll(async ({ request }) => {
    await drainRenderQueue(request, 'the gridfinity group')
  })

  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  // ── A. Project Loading & Navigation ──────────────────────────────

  test('loads gridfinity and shows manifest data', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await expect(page.locator('header h1')).toContainText(PROJECT_NAME)
    // 2 modes in project.json: bin and baseplate, both cadquery.
    // Scoped to the mode tablist and to what is on screen: the sidebar's
    // section tabs (Design/View/BOM/Export) are a [role="tablist"] too.
    const tabs = page.locator('[role="tablist"][aria-label="Mode selection"] [role="tab"]')
      .filter({ visible: true })
    await expect(tabs).toHaveCount(2)
  })

  // modes[0] is `bin`.
  test('default mode is bin', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/bin|contenedor/i)
  })

  test('switches to baseplate mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await sidebar.selectMode('baseplate')
    await page.waitForTimeout(500)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/baseplate|placa/i)
    expect(page.url()).toContain('baseplate')
  })

  // Was "switches to lid mode". Mode `lid` was OpenSCAD-only and left the
  // cartridge; `bin` and `baseplate` are the only modes now, so switching back
  // to bin is the remaining round-trip worth asserting.
  test('switches back to bin mode', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await sidebar.selectMode('baseplate')
    await page.waitForTimeout(500)
    await sidebar.selectMode('bin')
    await page.waitForTimeout(500)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/bin|contenedor/i)
    expect(page.url()).toContain('bin')
  })

  test('URL updates on mode switch', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await sidebar.selectMode('baseplate')
    await page.waitForTimeout(500)
    const pathname = await page.evaluate(() => window.location.pathname)
    // buildHash() writes /project/{slug}/{mode}[/{preset}] — mode first.
    expect(pathname).toMatch(/^\/project\/gridfinity\/baseplate(\/|$)/)
  })

  // ── B. Parameter Controls ────────────────────────────────────────

  // The `bin` mode is dimensioned by grid_x/grid_y/grid_z. The
  // width_units/depth_units/height_units trio was OpenSCAD-only and is gone;
  // no parameter declares visible_in_modes any more, so all ten show in both.
  test('bin mode shows dimension sliders', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await expect(sidebar.slider('grid_x')).toBeVisible()
    await expect(sidebar.slider('grid_y')).toBeVisible()
    await expect(sidebar.slider('grid_z')).toBeVisible()
  })

  test('adjusting grid_x slider updates value', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await sidebar.editSliderValue('grid_x', 4)
    await expect(sidebar.sliderValue('grid_x')).toHaveText('4', { timeout: 10000 })
  })

  // finger_scoop is the cadquery bin's scoop toggle (the OpenSCAD
  // fingerslide_enabled it used to sit beside is gone with the cup mode).
  test('toggling finger_scoop checkbox works', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    const cb = sidebar.checkbox('finger_scoop')
    await expect(cb).toBeVisible()
    const wasBefore = await cb.isChecked()
    await cb.click()
    const isAfter = await cb.isChecked()
    expect(isAfter).toBe(!wasBefore)
  })

  // Preset labels are unique again: the OpenSCAD duplicates ("Small Parts Bin"
  // and "Standard Baseplate" once per engine) left with their modes, so the
  // three remaining presets each match exactly one button.
  test('applies Small Parts Bin preset', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await sidebar.applyPreset('Small Parts Bin')
    await expect(sidebar.sliderValue('grid_x')).toHaveText('2', { timeout: 10000 })
    await expect(sidebar.sliderValue('grid_y')).toHaveText('1', { timeout: 10000 })
    await expect(sidebar.sliderValue('grid_z')).toHaveText('3', { timeout: 10000 })
  })

  // Was "applies Standard Lid preset" (mode `lid`, width_units/depth_units) —
  // all three left with the OpenSCAD side. "Deep Bin (2×2×6)" is the same
  // shape of assertion on a preset that still exists: same mode, grid_* set.
  test('applies Deep Bin preset', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await sidebar.applyPreset('Deep Bin')
    await page.waitForTimeout(1000)
    expect(await sidebar.getActiveMode()).toMatch(/bin|contenedor/i)
    await expect(sidebar.sliderValue('grid_x')).toHaveText('2', { timeout: 10000 })
    await expect(sidebar.sliderValue('grid_y')).toHaveText('2', { timeout: 10000 })
    await expect(sidebar.sliderValue('grid_z')).toHaveText('6', { timeout: 10000 })
  })

  test('cross-mode preset switches to baseplate', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await sidebar.applyPreset('Standard Baseplate')
    await page.waitForTimeout(1000)
    const active = await sidebar.getActiveMode()
    expect(active).toMatch(/baseplate|placa/i)
  })

  // Was "baseplate (OpenSCAD) mode shows baseplate params" against
  // bp_corner_radius / bp_enable_magnets, both OpenSCAD-only and now gone.
  // bp_thickness is the baseplate parameter the cadquery cartridge still ships.
  test('baseplate mode shows baseplate params', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await sidebar.selectMode('baseplate')
    await page.waitForTimeout(500)
    await expect(sidebar.slider('bp_thickness')).toBeVisible()
  })

  // ── C. 3D Rendering ─────────────────────────────────────────────

  test('renders bin with default params', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await clickGenerateWithWarning(sidebar, page)
    await waitForRenderDone(page, 120_000)
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('changing grid_x triggers new render', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await triggerAndWaitRender(sidebar, page, 'grid_x', 3, 120_000)
    const generateBtn = page.locator('button', { hasText: /Generate|Generar/ }).first()
    await expect(generateBtn).toBeEnabled()
  })

  test('model info shows dimensions after render', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await clickGenerateWithWarning(sidebar, page)
    await waitForRenderDone(page, 120_000)
    // Model info panel shows dimensions with multiplication sign
    const dimText = page.locator('text=/\\d+.*\\u00d7.*\\d+/')
    await expect(dimText.first()).toBeVisible({ timeout: 5000 })
  })

  test('camera views switch correctly', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await clickGenerateWithWarning(sidebar, page)
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

  // export_formats in project.json is [stl, 3mf, step, glb, gltf, obj] — six,
  // no OFF. ExportPanel lives in the sidebar's "export" section tab, which
  // Radix only mounts once selected, so the panel is not in the DOM on load.
  test('export panel shows 6 format buttons', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await sidebar.selectSection('export')
    const panel = page.locator('[data-testid="export-panel"]').first()
    for (const fmt of ['STL', '3MF', 'STEP', 'GLB', 'GLTF', 'OBJ']) {
      // Anchored: an unanchored /STL/ also matches the "Download STL" button.
      await expect(panel.getByRole('button', { name: new RegExp(`^${fmt}\\b`) }).first())
        .toBeVisible()
    }
    await expect(panel.getByRole('button', { name: /^OFF\b/ })).toHaveCount(0)
  })

  test('downloads STL file', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await clickGenerateWithWarning(sidebar, page)
    await waitForRenderDone(page, 120_000)

    // Select STL format (ExportPanel is behind the "export" section tab)
    await sidebar.selectSection('export')
    await page.getByRole('button', { name: /^STL\b/ }).first().click()
    await page.waitForTimeout(300)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download STL|Descargar STL/ }).click()
    })
    expect(suggestedFilename).toMatch(/\.stl$/i)
    expect(path).toBeTruthy()
  })

  // STEP is a B-Rep format, so it comes from the CadQuery kernel. Retitled
  // 2026-09-04: gridfinity is no longer dual-engine (it is CadQuery-only),
  // but STEP export is exactly the capability that survived.
  test('downloads STEP from the CadQuery kernel', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await clickGenerateWithWarning(sidebar, page)
    await waitForRenderDone(page, 120_000)

    // Select STEP format (ExportPanel is behind the "export" section tab)
    await sidebar.selectSection('export')
    await page.getByRole('button', { name: /^STEP\b/ }).first().click()
    await page.waitForTimeout(300)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download STEP|Descargar STEP/ }).click()
    }, 120_000)
    expect(suggestedFilename).toMatch(/\.step$/i)
    expect(path).toBeTruthy()
  })

  test('downloads 3MF file', async ({ page, sidebar }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    await clickGenerateWithWarning(sidebar, page)
    await waitForRenderDone(page, 120_000)

    await sidebar.selectSection('export')
    await page.getByRole('button', { name: /^3MF\b/ }).first().click()
    await page.waitForTimeout(300)

    const { suggestedFilename, path } = await waitForDownload(page, async () => {
      await page.locator('button', { hasText: /Download 3MF|Descargar 3MF/ }).click()
    }, 120_000)
    expect(suggestedFilename).toMatch(/\.3mf$/i)
    expect(path).toBeTruthy()
  })

  // ── E. Assembly & BOM ────────────────────────────────────────────

  // gridfinity's project.json declares no `assembly_steps` — the key is simply
  // absent from the cartridge (its top level is project/modes/parts/
  // parameter_groups/parameters/presets/constraints/camera_views/
  // export_formats/estimate_constants/hyperobject/tags). Ask the live manifest
  // rather than hard-coding that: the test wakes up on its own if the cartridge
  // ships steps again.
  test('assembly steps shows 3 steps', async ({ page, request }) => {
    const manifest = await fetchManifest(request, 'gridfinity')
    test.skip(
      !(manifest?.assembly_steps || []).length,
      'gridfinity declares no assembly_steps — nothing to assemble in this cartridge',
    )
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    // Open assembly steps panel if collapsed
    const assemblyBtn = page.locator('button', { hasText: /Assembly|Ensamble/ }).first()
    if (await assemblyBtn.isVisible().catch(() => false)) {
      await assemblyBtn.click()
      await page.waitForTimeout(500)
    }
    await expect(page.locator('text=/Step 1|Paso 1/')).toBeVisible({ timeout: 5000 })
  })

  test('assembly step navigation works', async ({ page, request }) => {
    const manifest = await fetchManifest(request, 'gridfinity')
    test.skip(
      ((manifest?.assembly_steps || []).length) < 2,
      'gridfinity declares no assembly_steps — nothing to navigate',
    )
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
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
      await expect(page.locator('text=/Step 2|Paso 2/')).toBeVisible({ timeout: 10000 })
    }
  })

  // BomPanel renders rows from manifest.bom.hardware (and /api/projects/{slug}
  // /bom 404s without it) — gridfinity declares no `bom` key at all, so there
  // is no hardware list to show. Same live-manifest guard as the assembly pair.
  test('BOM panel shows hardware after enabling magnets', async ({ page, sidebar, request }) => {
    const manifest = await fetchManifest(request, 'gridfinity')
    test.skip(
      !(manifest?.bom?.hardware || []).length,
      'gridfinity declares no bom.hardware — the BOM panel has nothing to list',
    )
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    // Enable magnets
    const cb = sidebar.checkbox('enable_magnets')
    if (await cb.isVisible().catch(() => false)) {
      const checked = await cb.isChecked()
      if (!checked) await cb.click()
    }
    await page.waitForTimeout(500)

    // The BOM lives in the sidebar's "analysis" section tab.
    await sidebar.selectSection('analysis')
    // Check for magnet entry
    await expect(page.locator('text=/[Mm]agnet/').first()).toBeVisible({ timeout: 5000 })
  })

  // ── G. Accessibility ─────────────────────────────────────────────

  test('passes axe audit (no critical violations)', async ({ page }) => {
    await goToRealProject(page, 'gridfinity', PROJECT_NAME)
    const results = await runAxeAudit(page, ['color-contrast'])
    const critical = results.violations.filter(v => v.impact === 'critical')
    expect(critical).toEqual([])
  })
})
