import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage } from '../../helpers/test-utils.js'

test.describe('Export Panel', () => {
  // ExportPanel renders inside <TabsContent value="export"> in StudioSidebar,
  // which defaults to "config". Nothing in this file selected that tab, so the
  // panel was never in the DOM and every assertion failed with "element(s) not
  // found" rather than anything to do with export. The old comment on the first
  // test — "Geometry accordion section is open by default" — described a
  // layout that no longer exists.
  test.beforeEach(async ({ page, sidebar }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    await sidebar.selectSection('export')
  })

  test('export panel is visible', async ({ page }) => {
    await expect(page.locator('text=Geometry')).toBeVisible()
  })

  // Format selector
  test('format selector shows STL/3MF/OFF when manifest declares export_formats', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'STL', exact: true })).toBeVisible()
    // 3MF/OFF may show lock icon for non-pro users — use partial match
    await expect(page.getByRole('button', { name: /3MF/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /OFF/ })).toBeVisible()
  })

  test('clicking format button highlights it', async ({ page }) => {
    const stlBtn = page.getByRole('button', { name: 'STL', exact: true })
    await expect(stlBtn).toBeVisible()
    // STL is default and should already have bg-primary
    await expect(stlBtn).toHaveClass(/bg-primary/, { timeout: 3000 })
  })

  test('STL is default format', async ({ page }) => {
    const stlBtn = page.locator('button', { hasText: 'STL' }).first()
    await expect(stlBtn).toHaveClass(/bg-primary/)
  })

  // Download buttons
  test('download STL button is visible', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Download STL' })).toBeVisible()
  })

  test('download STL button is disabled when no parts', async ({ page }) => {
    const btn = page.locator('button', { hasText: 'Download STL' })
    expect(await btn.isDisabled()).toBe(true)
  })

  test('download SCAD button is visible', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Download SCAD' })).toBeVisible()
  })

  // Image export buttons (inside collapsed "Images" accordion section)
  test('image export view buttons are visible after opening Images section', async ({ page, sidebar }) => {
    // Scoped to the sidebar: the viewer carries its own Isometric/Top/Front/
    // Right camera buttons, so an unscoped match spans both and .last() was a
    // guess about DOM order rather than a statement about which button is meant.
    await page.getByRole('button', { name: 'Images' }).click()
    for (const view of ['Isometric', 'Top', 'Front', 'Right']) {
      await expect(sidebar.sidebar.locator('button', { hasText: view }).last()).toBeVisible()
    }
  })

  test('export all views button is visible after opening Images section', async ({ page }) => {
    await page.getByRole('button', { name: 'Images' }).click()
    await expect(page.locator('button', { hasText: 'Export All Views' })).toBeVisible()
  })

  test('image export buttons are enabled after render produces parts', async ({ page, sidebar }) => {
    // Force backend rendering mode — WASM has no binary in the E2E test
    // environment, so it fails silently. By lowering hardwareConcurrency,
    // detectMode() picks 'backend' and the SSE mock produces real parts.
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'hardwareConcurrency', { value: 2 })
    })
    await goToStudio(page)
    // goToStudio renavigates, which resets the sidebar to its default "config"
    // tab and takes ExportPanel back out of the DOM.
    await sidebar.selectSection('export')

    // Wait for auto-render to complete (Generate button re-enables)
    const generateBtn = page.locator('button', { hasText: /Generate|Generar/i }).first()
    await expect(generateBtn).toBeEnabled({ timeout: 15000 })

    // Open Images section and check Export All Views is enabled
    await page.getByRole('button', { name: 'Images' }).click()
    const btn = page.locator('button', { hasText: 'Export All Views' })
    await expect(btn).toBeVisible()
    await expect(btn).toBeEnabled({ timeout: 15000 })
  })

  // Auth gate
  test('offers either a download control or a sign-in prompt, never neither', async ({ page }) => {
    // Which of the two appears depends on auth config, so the test asserts the
    // invariant that holds either way: the panel always gives the user a way
    // forward. It previously ended in expect(true).toBe(true), which passes
    // just as happily when the panel renders nothing at all.
    //
    // Polled, not counted once: `locator.count()` does not retry, so this was
    // really asserting that the export tabpanel had mounted by the instant the
    // beforeEach's selectSection() returned (a click plus a 150ms sleep). On
    // WebKit under ARC load it had not, and the sum read 0 on all three
    // attempts (run 32565668502, webkit shard 1) — while 'download STL button
    // is visible' above, which uses the auto-retrying toBeVisible(), passed in
    // the same run.
    const signIn = page.locator('text=Sign in to download')
    const download = page.locator('button', { hasText: 'Download STL' })
    await expect.poll(
      async () => (await signIn.count()) + (await download.count()),
      { timeout: 15_000, message: 'export panel offered neither a download control nor a sign-in prompt' },
    ).toBeGreaterThan(0)
  })

  test('format label shows "Format:" prefix', async ({ page }) => {
    await expect(page.locator('text=Format:')).toBeVisible()
  })

  test('download STL shows (ZIP) for multi-part modes', async ({ page, sidebar }) => {
    // Grid mode has 2 parts (body, rod), so should show ZIP
    await sidebar.selectMode('grid')
    await expect(page.locator('text=Download STL (ZIP)')).toBeVisible()
  })
})
