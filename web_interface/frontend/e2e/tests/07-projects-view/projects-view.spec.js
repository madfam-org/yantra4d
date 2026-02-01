import { test, expect } from '../../fixtures/app.fixture.js'
import { goToProjects, setLanguage } from '../../helpers/test-utils.js'

test.describe('Projects View', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  test('displays projects title', async ({ page }) => {
    await goToProjects(page)
    await expect(page.locator('h2', { hasText: 'Projects' })).toBeVisible()
  })

  test('shows project cards grid', async ({ page, projectsView }) => {
    await goToProjects(page)
    const count = await projectsView.getCardCount()
    expect(count).toBeGreaterThan(0)
  })

  test('project card displays name and version', async ({ page }) => {
    await goToProjects(page)
    await expect(page.locator('text=Test Project')).toBeVisible()
    await expect(page.locator('text=v1.0.0')).toBeVisible()
  })

  test('project card displays metadata (modes, params, scad count)', async ({ page }) => {
    await goToProjects(page)
    await expect(page.locator('text=2 modes')).toBeVisible()
    await expect(page.locator('text=4 params')).toBeVisible()
  })

  test('project card shows manifest badge', async ({ page }) => {
    await goToProjects(page)
    await expect(page.locator('text=Manifest').first()).toBeVisible()
  })

  test('clicking project card navigates to studio', async ({ page, projectsView }) => {
    await goToProjects(page)
    await projectsView.selectProject('test')
    await page.waitForTimeout(500)
    const hash = await page.evaluate(() => window.location.hash)
    expect(hash).toContain('test')
  })

  test('empty state shows message and CTA', async ({ page }) => {
    // Override the mock to return empty array
    await page.route('**/api/admin/projects', (route) => {
      route.fulfill({ json: [] })
    })
    await goToProjects(page)
    await expect(page.locator('text=No projects found')).toBeVisible()
    await expect(page.locator('a[href="#/onboard"]')).toBeVisible()
  })

  test('loading state shows loading text', async ({ page }) => {
    // Delay the response to catch loading state
    await page.unroute('**/api/admin/projects')
    await page.route('**/api/admin/projects', async (route) => {
      await new Promise(r => setTimeout(r, 3000))
      route.fulfill({ json: [] })
    })
    await goToProjects(page)
    await expect(page.locator('text=Loading')).toBeVisible({ timeout: 2000 })
  })

  test('error state shows error message', async ({ page }) => {
    await page.unroute('**/api/admin/projects')
    await page.route('**/api/admin/projects', (route) => {
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    })
    await goToProjects(page)
    await expect(page.locator('.text-destructive')).toBeVisible()
  })
})
