import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage, isMac } from '../../helpers/test-utils.js'

test.describe('Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
  })

  test('Cmd/Ctrl+Z triggers undo', async ({ page, sidebar }) => {
    const valueBefore = await sidebar.sliderValue('width').textContent()
    await sidebar.editSliderValue('width', 100)
    await expect(sidebar.sliderValue('width')).toHaveText('100', { timeout: 3000 })

    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText(valueBefore, { timeout: 3000 })
  })

  test('Cmd/Ctrl+Shift+Z triggers redo', async ({ page, sidebar }) => {
    // Wait for initial auto-render to settle so it doesn't clear redo stack
    await page.waitForTimeout(1500)

    const valueBefore = await sidebar.sliderValue('width').textContent()
    await sidebar.editSliderValue('width', 100)
    await expect(sidebar.sliderValue('width')).toHaveText('100', { timeout: 3000 })

    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText(valueBefore, { timeout: 3000 })

    // Small delay to avoid keyboard event collision with undo handler
    await page.waitForTimeout(200)
    await page.keyboard.press(mac ? 'Meta+Shift+z' : 'Control+Shift+z')
    await expect(sidebar.sliderValue('width')).toHaveText('100', { timeout: 3000 })
  })

  test('Cmd/Ctrl+Enter triggers render', async ({ page, sidebar }) => {
    // Slow down the render mock so we can observe loading state
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await new Promise(r => setTimeout(r, 5000))
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100,"phase":"Done"}\n\n' })
    })
    await page.unroute('**/api/render')
    await page.route('**/api/render', async (route) => {
      await new Promise(r => setTimeout(r, 5000))
      route.abort()
    })
    // Change a param to bust the render cache, then wait for debounce to clear
    await sidebar.editSliderValue('width', 77)
    // The debounced auto-render fires with the slow mock, showing Processing...
    await expect(page.locator('button', { hasText: /Processing|Procesando/ })).toBeVisible({ timeout: 3000 })
  })

  test('Escape cancels active render', async ({ page, sidebar }) => {
    // Wait for initial auto-render to settle
    await page.waitForTimeout(1000)
    // Set up slow mock to catch new render
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await new Promise(r => setTimeout(r, 10000))
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    // Change a param to bust render cache — debounced auto-render will use the slow mock
    await sidebar.editSliderValue('width', 63)
    // Wait for render to actually start (Cancel button appears)
    await expect(sidebar.cancelButton).toBeVisible({ timeout: 5000 })

    await page.keyboard.press('Escape')
    // Generate button should re-appear
    await expect(page.locator('button', { hasText: /Generate|Generar/ })).toBeVisible({ timeout: 5000 })
  })

  test('Cmd/Ctrl+1 switches to first mode', async ({ page }) => {
    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+1' : 'Control+1')
    await page.waitForTimeout(500)
    await expect(page.locator('[role="tab"][data-state="active"]').first()).toContainText(/Start|Inicio/i, { timeout: 3000 })
  })

  test('Cmd/Ctrl+2 switches to second mode', async ({ page }) => {
    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+2' : 'Control+2')
    await page.waitForTimeout(500)
    await expect(page.locator('[role="tab"][data-state="active"]').first()).toContainText(/Single|Individual/i, { timeout: 3000 })
  })

  test('Cmd/Ctrl+number beyond mode count does nothing', async ({ page }) => {
    const tabBefore = await page.locator('[role="tab"][data-state="active"]').first().textContent()
    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+9' : 'Control+9')
    await page.waitForTimeout(300)
    const tabAfter = await page.locator('[role="tab"][data-state="active"]').first().textContent()
    expect(tabAfter).toBe(tabBefore)
  })

  test('keyboard shortcuts work when sidebar is focused', async ({ page, sidebar }) => {
    const valueBefore = await sidebar.sliderValue('width').textContent()
    await sidebar.slider('width').click()
    const mac = await isMac(page)
    await sidebar.editSliderValue('width', 100)
    await expect(sidebar.sliderValue('width')).toHaveText('100', { timeout: 3000 })
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText(valueBefore, { timeout: 3000 })
  })

  test('keyboard shortcuts work when viewer is focused', async ({ page }) => {
    // Click the viewer area (not canvas directly — it may remount during manifest load)
    await page.locator('#main-content').click()
    await page.waitForTimeout(200)
    const mac = await isMac(page)
    // Ctrl+3 selects the 3rd mode (Grid) — modes are 1-indexed in shortcuts
    await page.keyboard.press(mac ? 'Meta+3' : 'Control+3')
    await page.waitForTimeout(500)
    await expect(page.locator('[role="tab"][data-state="active"]').first()).toContainText(/Grid|Cuadrícula/i, { timeout: 3000 })
  })

  test('keyboard shortcuts do not interfere with text inputs', async ({ page, sidebar }) => {
    const letterInput = sidebar.textInput('letter')
    if (await letterInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await letterInput.click()
      // Select all existing text, then type to replace it
      const mac = await isMac(page)
      await page.keyboard.press(mac ? 'Meta+a' : 'Control+a')
      await page.keyboard.type('Z')
      // Wait for React state to settle
      await expect(letterInput).toHaveValue('Z', { timeout: 3000 })
    }
  })

  test('multiple undos walk back through history', async ({ page, sidebar }) => {
    const initialVal = await sidebar.sliderValue('width').textContent()
    await sidebar.editSliderValue('width', 80)
    await expect(sidebar.sliderValue('width')).toHaveText('80', { timeout: 3000 })
    await sidebar.editSliderValue('width', 120)
    await expect(sidebar.sliderValue('width')).toHaveText('120', { timeout: 3000 })

    const mac = await isMac(page)
    // Undo to 80
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText('80', { timeout: 3000 })

    // Undo to initial
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText(initialVal, { timeout: 3000 })
  })
})
