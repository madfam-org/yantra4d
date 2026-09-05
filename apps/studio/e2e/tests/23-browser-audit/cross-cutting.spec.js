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
  drainRenderQueue,
} from './audit-helpers.js'

test.use({ mockAPIs: false })
test.describe.configure({ mode: 'serial' })

// projects/gridfinity/project.json declares project.name "Gridfinity". Its
// OpenSCAD modes (and the "Extended" name) left the cartridge on 2026-09-04;
// it is CadQuery-only, modes `bin` and `baseplate`.
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
    await drainRenderQueue(request, 'the cross-cutting group')
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

    // Change a parameter to create a non-default state. grid_x dimensions the
    // `bin` mode; width_units was the OpenSCAD equivalent and left the
    // cartridge with the OpenSCAD side on 2026-09-04.
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

    // Search for each one rather than expecting it on the landing page. The
    // catalogue is 496 cartridges served (495 commons + the private tablaco
    // mount) and ProjectsView pages at PAGE_SIZE = 60 sorted by name, so the
    // first page ends around "Bag Reseal & Pour Clip" — run #170 failed here
    // 3/3 looking for a gridfinity card that was ~440 cards further down.
    // Scrolling 495 cards in would test the pager, not the catalogue; the
    // search box is how a user finds a known project, and the slug is in the
    // server-side haystack (services/core/catalog_index.py).
    const search = page.getByRole('searchbox', { name: /Search projects|Buscar proyectos/i })
    await expect(search).toBeVisible({ timeout: 10_000 })

    // Verify a card for every audit project the backend serves (the private
    // cartridges only appear when this checkout includes them)
    for (const slug of [...PUBLIC_AUDIT_SLUGS, ...PRIVATE_AUDIT_SLUGS.filter(hasProject)]) {
      await search.fill(slug)
      // Covers the 250 ms input debounce plus the /api/catalog/search round trip.
      await expect(page.locator(`a[href="/project/${slug}"]`)).toBeVisible({ timeout: 15_000 })
      await search.fill('')
    }
  })
})
