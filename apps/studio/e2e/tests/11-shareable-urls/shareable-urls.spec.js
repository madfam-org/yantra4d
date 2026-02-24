/* global Buffer */
import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage, getSearchParams, waitForAppReady, enableClipboard, readClipboard } from '../../helpers/test-utils.js'

/**
 * Navigate to a URL with ?p= param and ensure controls are ready.
 * Uses a path-based URL (/project/test) to avoid preset overrides.
 * The pre-mount hash redirect in main.jsx converts any legacy hash
 * URLs to path-based equivalents before React mounts.
 */
async function goToWithParams(page, url) {
  await page.goto(url)
  await waitForAppReady(page)
  // Wait for mock manifest to load — header shows "Test Project"
  await page.locator('header h1', { hasText: 'Test Project' })
    .waitFor({ timeout: 8000 }).catch(() => { })

  // Wait for URL to settle (auto-redirect adds preset/mode segments)
  await page.waitForURL(/\/project\/[^/]+\/[^/]+\/[^/]+/, { timeout: 5000 })
    .catch(() => { })

  // Wait for sliders to render
  await page.locator('[role="slider"]').first()
    .waitFor({ timeout: 5000 }).catch(() => { })

  // Allow React state to settle after redirect and param restoration
  await page.waitForTimeout(500)
}

test.describe('Shareable URLs', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  test('default params produce no ?p= query', async ({ page }) => {
    await goToStudio(page)
    const search = await getSearchParams(page)
    expect(search).not.toContain('p=')
  })

  test('non-default params encode ?p= query via share', async ({ page, sidebar, header }) => {
    await goToStudio(page)
    await enableClipboard(page)
    await sidebar.editSliderValue('width', 100)
    await page.waitForTimeout(300)
    await header.clickShare()
    await page.waitForTimeout(500)
    const clipboardText = await readClipboard(page)
    expect(clipboardText).toContain('p=')
  })

  test('loading URL with ?p= restores params', async ({ page, sidebar }) => {
    const diff = Buffer.from(JSON.stringify({ width: 100 })).toString('base64url')
    // Use path-based URL to avoid preset override
    await goToWithParams(page, `/project/test?p=${diff}`)
    await page.waitForTimeout(800)
    const valEl = sidebar.sliderValue('width')
    await expect(valEl).toHaveText('100', { timeout: 8000 })
  })

  test('?p= with default values is equivalent to no params', async ({ page, sidebar }) => {
    const diff = Buffer.from(JSON.stringify({ width: 50 })).toString('base64url')
    // Use path-based URL to avoid preset override
    await goToWithParams(page, `/project/test?p=${diff}`)
    await page.waitForTimeout(800)
    const valEl = sidebar.sliderValue('width')
    await expect(valEl).toHaveText('50', { timeout: 8000 })
  })

  test('invalid ?p= value is gracefully ignored', async ({ page }) => {
    await page.goto('/project/test?p=not-valid-base64')
    await page.waitForSelector('header')
    // App should load without crashing
    await expect(page.locator('header h1')).toBeVisible()
  })

  test('empty ?p= value is ignored', async ({ page }) => {
    await page.goto('/project/test?p=')
    await page.waitForSelector('header')
    await expect(page.locator('header h1')).toBeVisible()
  })

  test('shared URL preserves mode in path', async ({ page, sidebar, header }) => {
    await goToStudio(page)
    await enableClipboard(page)
    await sidebar.selectMode('grid')
    await page.waitForTimeout(300)
    await header.clickShare()
    const clipboardText = await readClipboard(page)
    expect(clipboardText).toContain('grid')
  })

  test('shared URL preserves project slug', async ({ page, header }) => {
    await goToStudio(page)
    await enableClipboard(page)
    await header.clickShare()
    const clipboardText = await readClipboard(page)
    expect(clipboardText).toContain('test')
  })

  test('multiple params are encoded together', async ({ page, sidebar, header }) => {
    await goToStudio(page)
    await enableClipboard(page)
    await sidebar.editSliderValue('width', 100)
    await page.waitForTimeout(200)
    await sidebar.editSliderValue('height', 60)
    await page.waitForTimeout(200)
    await header.clickShare()
    const clipboardText = await readClipboard(page)
    expect(clipboardText).toContain('p=')
  })

  test('legacy 3-segment hash URL format still works via redirect', async ({ page }) => {
    // Use 3-segment hash (slug/preset/mode) which correctly maps to path-based routing
    await page.goto('/#/test/small/single')
    await page.waitForSelector('header', { timeout: 15000 })
    await expect(page.locator('header h1')).toBeVisible({ timeout: 10000 })
  })
})
