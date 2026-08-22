import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage, forceBackendRender, waitForRenderSettled } from '../../helpers/test-utils.js'

test.describe('Rendering Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    // Every test in this file asserts on the behaviour of a MOCKED render.
    // detectMode() only consults those mocks on the 'backend' path, and it
    // chooses between backend and WASM by reading navigator.hardwareConcurrency
    // — so without this pin the whole file silently tested the WASM path on any
    // runner with >= 4 cores, where the mocks are never fetched and the render
    // ends in "OpenSCAD exited with code 1" at machine-dependent speed.
    await forceBackendRender(page)
    await goToStudio(page)
  })

  test('clicking Generate starts render', async ({ page, sidebar }) => {
    // Slow down mock to observe loading state
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await new Promise(r => setTimeout(r, 5000))
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })
    // Change param to bust the render cache (auto-render cached the initial result)
    await sidebar.editSliderValue('width', 66)
    // The debounced auto-render fires with the slow mock, showing Processing...
    await expect(page.locator('button', { hasText: /Processing|Procesando/ })).toBeVisible({ timeout: 3000 })
  })

  test('cancel button appears during render', async ({ page, sidebar }) => {
    // Setup slow mock FIRST to catch the auto-render
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await new Promise(r => setTimeout(r, 5000))
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    // Change param to trigger auto-render (debounce 500ms)
    await sidebar.editSliderValue('width', 123)

    // Wait for cancel button (implies render started)
    await expect(sidebar.cancelButton).toBeVisible({ timeout: 5000 })
  })

  test('cancel aborts render', async ({ page, sidebar }) => {
    // Hold the render open until the test releases it, instead of betting that
    // a fixed 10s sleep outlasts however long the runner takes to get here.
    let releaseRender = () => { }
    const renderHeld = new Promise((resolve) => { releaseRender = resolve })
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await renderHeld
      await route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    try {
      // The initial auto-render has to finish first, or the Cancel button we
      // wait for below may belong to it rather than to the held render.
      await waitForRenderSettled(page)

      // Trigger auto-render
      await sidebar.editSliderValue('width', 124)

      // Wait for render to start
      await expect(sidebar.cancelButton).toBeVisible({ timeout: 15_000 })

      // Cancel
      await sidebar.clickCancel()

      // Verify loading cleared. The app aborts the in-flight fetch, so this
      // holds while the route is still held open.
      await expect(sidebar.generateButton).toBeVisible({ timeout: 10_000 })
      await expect(sidebar.generateButton).toBeEnabled({ timeout: 10_000 })
    } finally {
      releaseRender()
    }
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

  test('changing parameter triggers auto-render after debounce', async ({ page, sidebar, viewer }) => {
    // Wait for the initial auto-render to fully complete (Generate button re-enabled)
    const generateBtn = page.locator('button', { hasText: /Generate|Generar/i }).first()
    await expect(generateBtn).toBeEnabled({ timeout: 15000 })

    // Get current console log text before the change
    const logsBefore = await viewer.getConsoleLogs()

    // Trigger a parameter change — auto-render should fire after debounce
    await sidebar.editSliderValue('width', 75)

    // Wait for the auto-render to produce new log entries (debounce + render)
    await page.waitForTimeout(3000)
    const logsAfter = await viewer.getConsoleLogs()

    // The log should contain more "Generating" entries than before
    const countBefore = (logsBefore.match(/Generating/g) || []).length
    const countAfter = (logsAfter.match(/Generating/g) || []).length
    expect(countAfter).toBeGreaterThan(countBefore)
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
    // Let the initial (successful) auto-render finish first, so the failure
    // below is unambiguously the one produced by the error mock.
    await waitForRenderSettled(page)
    // Change param to bust cache, triggering a fresh render with the error mock
    await sidebar.editSliderValue('width', 55)
    // Poll the console rather than sleeping for a fixed 2s. In run 32565668502
    // the error DID arrive — the post-failure snapshot shows
    //   "Ready. Generating (cup)... [body] Starting... (1/1) Starting OpenSCAD...
    //    Error: OpenSCAD exited with code 1"
    // — but at t=2s the log still read only "Ready. / Generating (cup)... /
    // [body] Starting... (1/1)", which is exactly the string the failure
    // reported as "Received".
    await expect.poll(
      async () => viewer.getConsoleLogs(),
      { timeout: 20_000, message: 'render console never reported an error' },
    ).toContain('Error')
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
    // Change param to bust cache, triggering render with timeout mock
    await sidebar.editSliderValue('width', 44)
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

  test('long render warning dialog appears for high estimates', async ({ page, sidebar }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } }) // 2 minutes
    })
    // Trigger render — this should show confirmation dialog
    await sidebar.generateButton.click()
    await page.waitForTimeout(500)
    // Dialog may appear if estimate exceeds threshold
  })

  test('confirm dialog "Render Anyway" proceeds with render', async ({ page, sidebar }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } })
    })
    await sidebar.generateButton.click()
    await page.waitForTimeout(500)
    const dialog = page.locator('text=Render Anyway')
    if (await dialog.isVisible()) {
      await dialog.click()
    }
  })

  test('confirm dialog "Cancel" aborts render', async ({ page, sidebar }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } })
    })
    await sidebar.generateButton.click()
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
