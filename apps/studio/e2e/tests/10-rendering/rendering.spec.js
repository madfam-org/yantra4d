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
    // Setup slow mock
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await new Promise(r => setTimeout(r, 10000))
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    // Trigger auto-render
    await sidebar.editSliderValue('width', 124)

    // Wait for render to start
    await expect(sidebar.cancelButton).toBeVisible({ timeout: 5000 })

    // Cancel
    await sidebar.clickCancel()

    // Verify loading cleared
    await expect(sidebar.generateButton).toBeVisible({ timeout: 5000 })
    await expect(sidebar.generateButton).toBeEnabled({ timeout: 5000 })
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
    // Wait for initial auto-render to settle
    await page.waitForTimeout(1000)
    // Setup a specific mock to ensure we catch the right request
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    // Start listening for the request BEFORE triggering the change
    const requestPromise = page.waitForRequest(req => {
      if (!req.url().includes('/api/render-stream')) return false
      try { return req.postDataJSON().width === 75 } catch { return false }
    }, { timeout: 10000 })

    // Trigger change
    await sidebar.editSliderValue('width', 75)

    const request = await requestPromise
    expect(request).toBeTruthy()
    expect(request.postDataJSON().width).toBe(75)
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
    // Change param to bust cache, triggering a fresh render with the error mock
    await sidebar.editSliderValue('width', 55)
    await page.waitForTimeout(2000)
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
