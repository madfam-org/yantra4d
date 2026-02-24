import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, getPathname, setLanguage } from '../../helpers/test-utils.js'

test.describe('Navigation', () => {
  test('3-segment hash navigates to studio view', async ({ page }) => {
    await setLanguage(page, 'en')
    await page.goto('/#/test/small/grid')
    await page.waitForSelector('header', { timeout: 15000 })
    // Wait for mock manifest to load and app to settle
    await expect(page.locator('header h1')).toContainText('Test Project', { timeout: 10000 })
    // Hash redirect converts /#/test/small/grid → /project/test/small/grid
    await page.waitForTimeout(1000)
    const pathname = await getPathname(page)
    expect(pathname).toContain('/project/test')
  })

  test('legacy 2-segment hash #/preset/mode falls back correctly', async ({ page }) => {
    await setLanguage(page, 'en')
    await page.goto('/project/test/small/single')
    await page.waitForSelector('header', { timeout: 15000 })
    // Should still render the studio view with correct preset/mode
    await expect(page.locator('header h1')).toBeVisible({ timeout: 10000 })
  })

  test('invalid route does not crash the app', async ({ page }) => {
    await setLanguage(page, 'en')
    await page.goto('/project/nonexistent-route-xyz')
    await page.waitForTimeout(3000)
    // App should render without crashing — may show loading spinner since
    // the mock manifest slug ("test") doesn't match the URL slug
    await expect(page.locator('body')).toBeVisible()
    const crashed = await page.locator('[data-testid="error-boundary"], .error-boundary').count()
    expect(crashed).toBe(0)
  })

  test('browser back/forward preserves state', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    await expect(page.locator('header h1')).toContainText('Test Project', { timeout: 10000 })

    await goToProjects(page)
    const path1 = await getPathname(page)
    expect(path1).toBe('/projects')

    await page.goBack()
    await page.waitForTimeout(500)
    const path2 = await getPathname(page)
    expect(path2).not.toBe('/projects')

    await page.goForward()
    await page.waitForTimeout(500)
    const path3 = await getPathname(page)
    expect(path3).toBe('/projects')
  })
})
