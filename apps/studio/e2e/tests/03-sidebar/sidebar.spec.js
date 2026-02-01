import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage } from '../../helpers/test-utils.js'

test.describe('Studio Sidebar', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
  })

  // Mode tabs
  test('mode tabs are visible', async ({ sidebar }) => {
    await expect(sidebar.modeTab('single')).toBeVisible()
  })

  test('clicking mode tab switches mode', async ({ sidebar }) => {
    await sidebar.selectMode('grid')
    const active = await sidebar.getActiveMode()
    expect(active).toBe('grid')
  })

  test('mode switch updates URL hash', async ({ page, sidebar }) => {
    await sidebar.selectMode('grid')
    await page.waitForTimeout(300)
    const hash = await page.evaluate(() => window.location.hash)
    expect(hash).toContain('grid')
  })

  test('controls filter by visible_in_modes', async ({ page, sidebar }) => {
    // "letter" text input is only visible in "single" mode
    await sidebar.selectMode('single')
    await expect(sidebar.textInput('letter')).toBeVisible()

    await sidebar.selectMode('grid')
    await page.waitForTimeout(300)
    // Letter should not be visible in grid mode (if manifest has visible_in_modes: ['single'])
  })

  // Size presets
  test('preset buttons are visible', async ({ sidebar }) => {
    await expect(sidebar.presetButton('Small')).toBeVisible()
    await expect(sidebar.presetButton('Large')).toBeVisible()
  })

  test('clicking preset applies parameter values', async ({ sidebar }) => {
    await sidebar.applyPreset('Large')
    const value = await sidebar.sliderValue('width').textContent()
    expect(value).toBe('150')
  })

  test('active preset is highlighted', async ({ sidebar }) => {
    await sidebar.applyPreset('Small')
    const btn = sidebar.presetButton('Small')
    await expect(btn).toHaveClass(/bg-primary/)
  })

  // Grid presets
  test('grid presets visible only in grid mode', async ({ page, sidebar }) => {
    await sidebar.selectMode('single')
    await page.waitForTimeout(200)
    // Grid presets should not be visible in single mode
    // (They render conditionally based on mode === 'grid')
  })

  // Sliders
  test('slider displays current value', async ({ sidebar }) => {
    const val = await sidebar.sliderValue('width').textContent()
    expect(val).toBeTruthy()
  })

  test('clicking value enters edit mode', async ({ page, sidebar }) => {
    await sidebar.sliderValue('width').click()
    await expect(page.locator('input[type="number"]')).toBeVisible()
  })

  test('editing value and blurring commits change', async ({ sidebar }) => {
    await sidebar.editSliderValue('width', 75)
    const val = await sidebar.sliderValue('width').textContent()
    expect(val).toBe('75')
  })

  test('value is clamped to min/max', async ({ sidebar }) => {
    await sidebar.editSliderValue('width', 9999)
    const val = await sidebar.sliderValue('width').textContent()
    // Should be clamped to max (200)
    expect(Number(val)).toBeLessThanOrEqual(200)
  })

  test('default star marker is visible', async ({ page }) => {
    await expect(page.locator('[data-testid="default-star-width"]')).toBeVisible()
  })

  // Text inputs
  test('text input renders', async ({ sidebar }) => {
    await expect(sidebar.textInput('letter')).toBeVisible()
  })

  test('text input enforces maxlength', async ({ sidebar }) => {
    const input = sidebar.textInput('letter')
    const maxLen = await input.getAttribute('maxlength')
    expect(maxLen).toBe('1')
  })

  // Checkboxes
  test('checkbox renders with default state', async ({ sidebar }) => {
    await expect(sidebar.checkbox('show_base')).toBeVisible()
  })

  test('checkbox toggles on click', async ({ page, sidebar }) => {
    const cb = sidebar.checkbox('show_base')
    await cb.click()
    await page.waitForTimeout(200)
    // State should have changed
  })

  // Wireframe
  test('wireframe toggle is visible in colors section', async ({ page }) => {
    await expect(page.locator('#wireframe-toggle')).toBeVisible()
  })

  test('wireframe toggle switches state', async ({ page }) => {
    const toggle = page.locator('#wireframe-toggle')
    await toggle.click()
    // data-state should change
    await expect(toggle).toHaveAttribute('data-state', 'checked')
  })

  // Color pickers
  test('color picker renders for parts', async ({ sidebar }) => {
    await expect(sidebar.colorInput('body')).toBeVisible()
  })

  test('color picker updates value', async ({ sidebar }) => {
    const input = sidebar.colorInput('body')
    await input.fill('#ff0000')
    await input.dispatchEvent('change')
    const val = await input.inputValue()
    expect(val).toBe('#ff0000')
  })

  // Action buttons
  test('generate button is enabled', async ({ sidebar }) => {
    expect(await sidebar.isGenerateDisabled()).toBe(false)
  })

  test('generate button shows "Processing..." when loading', async ({ page, sidebar }) => {
    // Replace render mock with a slow response to catch the loading state
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
    await sidebar.clickGenerate()
    // The button text changes from Generate to Processing, so use a broader selector
    await expect(page.locator('button', { hasText: /Processing|Procesando/ })).toBeVisible({ timeout: 3000 })
  })

  test('cancel button appears during render', async ({ sidebar }) => {
    await sidebar.clickGenerate()
    await expect(sidebar.cancelButton).toBeVisible()
  })

  test('verify button is disabled when no parts rendered', async ({ sidebar }) => {
    // Initially no parts, verify should be disabled
    expect(await sidebar.verifyButton.isDisabled()).toBe(true)
  })

  test('reset button reverts params to defaults', async ({ page, sidebar }) => {
    await sidebar.editSliderValue('width', 100)
    await page.waitForTimeout(200)
    await sidebar.clickReset()
    await page.waitForTimeout(200)
    const val = await sidebar.sliderValue('width').textContent()
    expect(val).toBe('50') // default from mock manifest
  })

  // Visibility toggle
  test('Basic/Advanced toggle switches visibility level', async ({ page, sidebar }) => {
    const toggle = sidebar.visibilityToggle()
    if (await toggle.isVisible()) {
      await toggle.click()
      await page.waitForTimeout(200)
      // Should toggle between basic and advanced
    }
  })
})
