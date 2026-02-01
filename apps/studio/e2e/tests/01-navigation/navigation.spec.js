import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, getHash, setLanguage } from '../../helpers/test-utils.js'

test.describe('Navigation', () => {
  test('3-segment hash navigates to studio view', async ({ page }) => {
    await setLanguage(page, 'en')
    await page.goto('/#/test/small/grid')
    await page.waitForSelector('header', { timeout: 15000 })
    // Wait for mock manifest to load and app to settle
    await expect(page.locator('header h1')).toContainText('Test Project', { timeout: 10000 })
    // Hash should contain project slug and mode after app resolves
    const hash = await getHash(page)
    expect(hash).toContain('/grid')
  })

  test('legacy 2-segment hash #/preset/mode falls back correctly', async ({ page }) => {
    await setLanguage(page, 'en')
    await page.goto('/#/small/single')
    await page.waitForSelector('header', { timeout: 15000 })
    // Should still render the studio view
    await expect(page.locator('header h1')).toBeVisible()
  })

  test('invalid route redirects to default view', async ({ page }) => {
    await setLanguage(page, 'en')
    await page.goto('/#/nonexistent-route-xyz')
    await page.waitForSelector('header', { timeout: 15000 })
    // App should render without crashing
    await expect(page.locator('header')).toBeVisible()
  })

  test('browser back/forward preserves state', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    await expect(page.locator('header h1')).toContainText('Test Project', { timeout: 10000 })

    await goToProjects(page)
    const hash1 = await getHash(page)
    expect(hash1).toBe('#/projects')

    await page.goBack()
    await page.waitForTimeout(500)
    const hash2 = await getHash(page)
    expect(hash2).not.toBe('#/projects')

    await page.goForward()
    await page.waitForTimeout(500)
    const hash3 = await getHash(page)
    expect(hash3).toBe('#/projects')
  })
})
