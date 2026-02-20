import { test, expect } from '../../fixtures/app.fixture.js'
import { goToProjects, setLanguage } from '../../helpers/test-utils.js'

test.describe('Projects View', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  test('displays projects title', async ({ page }) => {
    await goToProjects(page)
    await expect(page.locator('h2', { hasText: 'Projects' })).toBeVisible({ timeout: 8000 })
  })

  test('shows project cards grid', async ({ page, projectsView }) => {
    await goToProjects(page)
    const count = await projectsView.getCardCount()
    expect(count).toBeGreaterThan(0)
  })

  test('project card displays name and version', async ({ page }) => {
    await goToProjects(page)
    await expect(page.getByText('Test Project')).toBeVisible({ timeout: 8000 })
    await expect(page.getByText('v1.0.0')).toBeVisible({ timeout: 5000 })
  })

  test('project card displays metadata (modes, params, scad count)', async ({ page }) => {
    await goToProjects(page)
    await expect(page.getByText('2 modes')).toBeVisible({ timeout: 8000 })
    await expect(page.getByText('4 params')).toBeVisible({ timeout: 5000 })
  })

  test('project card shows manifest badge', async ({ page }) => {
    await goToProjects(page)
    await expect(page.getByText('Manifest').first()).toBeVisible({ timeout: 8000 })
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
    await page.unroute('**/api/admin/projects**')
    await page.route('**/api/admin/projects**', (route) => {
      route.fulfill({ json: [] })
    })
    await goToProjects(page)
    await expect(page.getByText('No projects found').or(page.getByText('No se encontraron proyectos'))).toBeVisible({ timeout: 8000 })
    await expect(page.locator('a[href="#/onboard"]')).toBeVisible({ timeout: 5000 })
  })

  test('loading state shows loading text', async ({ page }) => {
    // Delay the response to catch loading state
    await page.unroute('**/api/admin/projects**')
    await page.route('**/api/admin/projects**', async (route) => {
      await new Promise(r => setTimeout(r, 3000))
      route.fulfill({ json: [] })
    })
    await goToProjects(page)
    await expect(page.getByText('Loading').or(page.getByText('Cargando'))).toBeVisible({ timeout: 2000 })
  })

  test('error state shows error message', async ({ page }) => {
    await page.unroute('**/api/admin/projects**')
    await page.route('**/api/admin/projects**', (route) => {
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    })
    await goToProjects(page)
    await expect(page.getByText('Server error')).toBeVisible({ timeout: 8000 })
  })
})
