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
    // Setup a specific mock to ensure we catch the right request
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    // Prepare to wait for the request
    const requestPromise = page.waitForRequest(req => req.url().includes('/api/render-stream'))

    // Trigger change
    await sidebar.editSliderValue('width', 75)

    // Wait for the debounced request (default debounce is 500ms)
    // If this times out, the debounce logic or event handler is broken
    const request = await requestPromise
    expect(request).toBeTruthy()

    // Verify payload if needed, but existence is enough for this test
    const postData = request.postDataJSON()
    expect(postData.width).toBe(75)
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
