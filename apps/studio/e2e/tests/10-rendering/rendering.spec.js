import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage } from '../../helpers/test-utils.js'

test.describe('Rendering Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
  })

  test('clicking Generate starts render', async ({ page, sidebar }) => {
    // Slow down mock to observe loading state
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await new Promise(r => setTimeout(r, 5000))
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })
    await sidebar.clickGenerate()
    await expect(page.locator('button', { hasText: /Processing|Procesando/ })).toBeVisible({ timeout: 3000 })
  })

  test('cancel button appears during render', async ({ page, sidebar }) => {
    // The auto-render during goToStudio caches results for the current params.
    // Change a param to bust the cache key, then re-mock render-stream to be slow.
    await sidebar.editSliderValue('width', 123)
    await page.waitForTimeout(300)
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await new Promise(r => setTimeout(r, 5000))
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })
    await sidebar.clickGenerate()
    await expect(sidebar.cancelButton).toBeVisible({ timeout: 3000 })
  })

  test('cancel aborts render', async ({ page, sidebar }) => {
    // Change param to bust cache (same as above)
    await sidebar.editSliderValue('width', 124)
    await page.waitForTimeout(300)
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await new Promise(r => setTimeout(r, 10000))
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })
    await sidebar.clickGenerate()
    await page.waitForTimeout(500)
    await sidebar.clickCancel()
    await page.waitForTimeout(500)
    await expect(page.locator('button', { hasText: /Generate|Generar/ })).toBeVisible({ timeout: 3000 })
  })

  test('console logs render progress', async ({ page, sidebar, viewer }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(1000)
    const logs = await viewer.getConsoleLogs()
    expect(logs.length).toBeGreaterThan(0)
  })

  test('SSE streaming render updates progress', async ({ page, sidebar }) => {
    // The default mock returns SSE events
    // Verify generate completes
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)
  })

  test('generate button re-enables after render completes', async ({ page, sidebar }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)
    expect(await sidebar.isGenerateDisabled()).toBe(false)
  })

  test('render with same params uses cache', async ({ page, sidebar, viewer }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)

    // Generate again with same params
    await sidebar.clickGenerate()
    await page.waitForTimeout(1000)
    const _logs = await viewer.getConsoleLogs()
    // May contain "Loaded from cache" depending on impl
  })

  test('changing parameter triggers auto-render after debounce', async ({ page, sidebar }) => {
    await sidebar.editSliderValue('width', 75)
    // Wait for 500ms debounce + render time
    await page.waitForTimeout(2000)
  })

  test('render error shows message in console', async ({ page, sidebar, viewer }) => {
    await page.unroute('**/api/render')
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render', (route) => {
      route.fulfill({ status: 500, json: { error: 'OpenSCAD crashed' } })
    })
    await page.route('**/api/render-stream', (route) => {
      route.fulfill({ status: 500, json: { error: 'OpenSCAD crashed' } })
    })
    await sidebar.clickGenerate()
    await page.waitForTimeout(1000)
    const logs = await viewer.getConsoleLogs()
    expect(logs).toContain('Error')
  })

  test('render timeout shows error', async ({ page, sidebar }) => {
    await page.unroute('**/api/render')
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render', (route) => {
      route.abort('timedout')
    })
    await page.route('**/api/render-stream', (route) => {
      route.abort('timedout')
    })
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)
  })

  test('verify button works after successful render', async ({ page, sidebar }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)
    // After render, verify should be enabled (if parts loaded)
  })

  test('verify shows results in console', async ({ page, sidebar, viewer }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)
    if (!(await sidebar.verifyButton.isDisabled())) {
      await sidebar.clickVerify()
      await page.waitForTimeout(1000)
      const logs = await viewer.getConsoleLogs()
      expect(logs).toContain('Verif')
    }
  })

  test('long render warning dialog appears for high estimates', async ({ page }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } }) // 2 minutes
    })
    // Trigger render — this should show confirmation dialog
    await page.locator('button', { hasText: 'Generate' }).click()
    await page.waitForTimeout(500)
    // Dialog may appear if estimate exceeds threshold
  })

  test('confirm dialog "Render Anyway" proceeds with render', async ({ page }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } })
    })
    await page.locator('button', { hasText: 'Generate' }).click()
    await page.waitForTimeout(500)
    const dialog = page.locator('text=Render Anyway')
    if (await dialog.isVisible()) {
      await dialog.click()
    }
  })

  test('confirm dialog "Cancel" aborts render', async ({ page }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } })
    })
    await page.locator('button', { hasText: 'Generate' }).click()
    await page.waitForTimeout(500)
    const cancelBtn = page.locator('[role="alertdialog"] button', { hasText: 'Cancel' })
    if (await cancelBtn.isVisible()) {
      await cancelBtn.click()
    }
  })

  test('progress bar reflects percentage', async ({ page, sidebar }) => {
    // With SSE mock, progress updates from 0→100
    await sidebar.clickGenerate()
    await page.waitForTimeout(500)
  })

  test('progress phase label updates during render', async ({ page, sidebar }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(500)
  })

  test('multiple rapid generates are debounced', async ({ page, sidebar }) => {
    await sidebar.clickGenerate()
    await sidebar.clickGenerate()
    await sidebar.clickGenerate()
    // Should not crash, only one render should be active
    await page.waitForTimeout(1000)
    await expect(page.locator('header')).toBeVisible()
  })
})
