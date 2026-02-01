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
    await page.waitForTimeout(300)

    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await page.waitForTimeout(300)

    const val = await sidebar.sliderValue('width').textContent()
    expect(val).toBe(valueBefore)
  })

  test('Cmd/Ctrl+Shift+Z triggers redo', async ({ page, sidebar }) => {
    await sidebar.editSliderValue('width', 100)
    await page.waitForTimeout(300)

    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await page.waitForTimeout(200)
    await page.keyboard.press(mac ? 'Meta+Shift+z' : 'Control+Shift+z')
    await page.waitForTimeout(200)

    const val = await sidebar.sliderValue('width').textContent()
    expect(val).toBe('100')
  })

  test('Cmd/Ctrl+Enter triggers render', async ({ page }) => {
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

    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+Enter' : 'Control+Enter')
    await expect(page.locator('button', { hasText: /Processing|Procesando/ })).toBeVisible({ timeout: 3000 })
  })

  test('Escape cancels active render', async ({ page }) => {
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await new Promise(r => setTimeout(r, 10000))
      route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+Enter' : 'Control+Enter')
    await page.waitForTimeout(500)
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
    // Generate button should re-appear
    await expect(page.locator('button', { hasText: /Generate|Generar/ })).toBeVisible({ timeout: 3000 })
  })

  test('Cmd/Ctrl+1 switches to first mode', async ({ page }) => {
    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+1' : 'Control+1')
    await page.waitForTimeout(300)
    const activeTab = await page.locator('[role="tab"][data-state="active"]').textContent()
    expect(activeTab.toLowerCase()).toContain('single')
  })

  test('Cmd/Ctrl+2 switches to second mode', async ({ page }) => {
    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+2' : 'Control+2')
    await page.waitForTimeout(300)
    const activeTab = await page.locator('[role="tab"][data-state="active"]').textContent()
    expect(activeTab.toLowerCase()).toContain('grid')
  })

  test('Cmd/Ctrl+number beyond mode count does nothing', async ({ page }) => {
    const mac = await isMac(page)
    const tabBefore = await page.locator('[role="tab"][data-state="active"]').textContent()
    await page.keyboard.press(mac ? 'Meta+9' : 'Control+9')
    await page.waitForTimeout(200)
    const tabAfter = await page.locator('[role="tab"][data-state="active"]').textContent()
    expect(tabAfter).toBe(tabBefore)
  })

  test('keyboard shortcuts work when sidebar is focused', async ({ page, sidebar }) => {
    await sidebar.slider('width').click()
    await page.waitForTimeout(100)
    const mac = await isMac(page)
    await sidebar.editSliderValue('width', 100)
    await page.waitForTimeout(300)
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await page.waitForTimeout(300)
    const val = await sidebar.sliderValue('width').textContent()
    expect(val).not.toBe('100')
  })

  test('keyboard shortcuts work when viewer is focused', async ({ page }) => {
    await page.locator('canvas').click()
    await page.waitForTimeout(100)
    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+2' : 'Control+2')
    await page.waitForTimeout(300)
    const activeTab = await page.locator('[role="tab"][data-state="active"]').textContent()
    expect(activeTab.toLowerCase()).toContain('grid')
  })

  test('keyboard shortcuts do not interfere with text inputs', async ({ page, sidebar }) => {
    const letterInput = sidebar.textInput('letter')
    if (await letterInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await letterInput.focus()
      await letterInput.fill('Z')
      await page.waitForTimeout(200)
      const val = await letterInput.inputValue()
      expect(val).toBe('Z')
    }
  })

  test('multiple undos walk back through history', async ({ page, sidebar }) => {
    const initialVal = await sidebar.sliderValue('width').textContent()
    await sidebar.editSliderValue('width', 80)
    await page.waitForTimeout(300)
    await sidebar.editSliderValue('width', 120)
    await page.waitForTimeout(300)

    const mac = await isMac(page)
    // Undo to 80
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await page.waitForTimeout(200)
    expect(await sidebar.sliderValue('width').textContent()).toBe('80')

    // Undo to initial
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await page.waitForTimeout(200)
    expect(await sidebar.sliderValue('width').textContent()).toBe(initialVal)
  })
})
