/* global Buffer */
import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage, getSearchParams, waitForAppReady } from '../../helpers/test-utils.js'

/**
 * Navigate to a URL with ?p= param and ensure controls are ready.
 * Uses a 3-segment hash (#/project/preset/mode) to ensure the correct mode
 * is active immediately, bypassing the fallback manifest mode issue.
 */
async function goToWithParams(page, url) {
  await page.goto(url)
  await waitForAppReady(page)
  // Wait for mock manifest to load
  await page.locator('header h1', { hasText: 'Test Project' })
    .waitFor({ timeout: 8000 }).catch(() => { })
  // Ensure a mode tab is active (fallback manifest may set wrong mode)
  const activeTab = page.locator('[role="tab"][data-state="active"]')
  if (await activeTab.count() === 0) {
    const firstTab = page.locator('[role="tab"]').first()
    if (await firstTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstTab.click()
      await page.waitForTimeout(500)
    }
  }
  // Wait for sliders to render (they only appear for the correct mode)
  await page.locator('[role="slider"]').first()
    .waitFor({ timeout: 5000 }).catch(() => { })
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
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    await sidebar.editSliderValue('width', 100)
    await page.waitForTimeout(300)
    await header.clickShare()
    await page.waitForTimeout(500)
    // The clipboard should contain a URL with ?p=
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
    expect(clipboardText).toContain('p=')
  })

  test('loading URL with ?p= restores params', async ({ page, sidebar }) => {
    const diff = Buffer.from(JSON.stringify({ width: 100 })).toString('base64url')
    // Use 3-segment hash to explicitly set mode to 'single'
    await goToWithParams(page, `/?p=${diff}#/test/small/single`)
    await page.waitForTimeout(800)
    const valEl = sidebar.sliderValue('width')
    await expect(valEl).toHaveText('100', { timeout: 8000 })
  })

  test('?p= with default values is equivalent to no params', async ({ page, sidebar }) => {
    const diff = Buffer.from(JSON.stringify({ width: 50 })).toString('base64url')
    // Use 3-segment hash to explicitly set mode to 'single'
    await goToWithParams(page, `/?p=${diff}#/test/small/single`)
    await page.waitForTimeout(800)
    const valEl = sidebar.sliderValue('width')
    await expect(valEl).toHaveText('50', { timeout: 8000 })
  })

  test('invalid ?p= value is gracefully ignored', async ({ page }) => {
    await page.goto('/?p=not-valid-base64#/test')
    await page.waitForSelector('header')
    // App should load without crashing
    await expect(page.locator('header h1')).toBeVisible()
  })

  test('empty ?p= value is ignored', async ({ page }) => {
    await page.goto('/?p=#/test')
    await page.waitForSelector('header')
    await expect(page.locator('header h1')).toBeVisible()
  })

  test('shared URL preserves mode in hash', async ({ page, sidebar, header }) => {
    await goToStudio(page)
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    await sidebar.selectMode('grid')
    await page.waitForTimeout(300)
    await header.clickShare()
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
    expect(clipboardText).toContain('grid')
  })

  test('shared URL preserves project slug', async ({ page, header }) => {
    await goToStudio(page)
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    await header.clickShare()
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
    expect(clipboardText).toContain('test')
  })

  test('multiple params are encoded together', async ({ page, sidebar, header }) => {
    await goToStudio(page)
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    await sidebar.editSliderValue('width', 100)
    await page.waitForTimeout(200)
    await sidebar.editSliderValue('height', 60)
    await page.waitForTimeout(200)
    await header.clickShare()
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
    expect(clipboardText).toContain('p=')
  })

  test('legacy 2-segment URL format still works', async ({ page }) => {
    await page.goto('/#/small/single')
    await page.waitForSelector('header')
    await expect(page.locator('header h1')).toBeVisible()
  })
})
