import { test, expect } from '../../fixtures/app.fixture.js'
import { goToProjects, setLanguage } from '../../helpers/test-utils.js'
import { catalogResponse } from '../../helpers/api-mocker.js'

// ProjectsView is a faceted catalog browser over /api/catalog/search, not the
// card grid over /api/admin/projects these tests were written against. Three
// consequences, all of which showed up as failures here:
//
//   1. Every mock in this file addressed **/api/admin/projects, an endpoint the
//      page no longer calls — so the loading/empty/error tests overrode nothing
//      and the rest ran against the live catalog (326 cartridges).
//   2. A catalog result has no `version` and no `has_manifest`, so "v1.0.0" and
//      the "Manifest" badge assert markup that no longer has a data source.
//   3. Results carry mode_count/part_count, but the row renders name,
//      description, domain and tags — not a "2 modes / 4 params" metadata line.
//
// The mock now lives in api-mocker (catalogResponse) so it applies by default;
// the per-test routes below only override it for the state under test.
const CATALOG = '**/api/catalog/search**'

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

  test('project result displays name and description', async ({ page }) => {
    await goToProjects(page)
    await expect(page.getByText('Test Project').first()).toBeVisible({ timeout: 8000 })
    await expect(page.getByText('A test').first()).toBeVisible({ timeout: 5000 })
  })

  test('result count reflects the catalog response', async ({ page }) => {
    await goToProjects(page)
    // catalogResponse() returns 2 results → "2 results" / "2 in catalog".
    await expect(page.getByText('2 results')).toBeVisible({ timeout: 8000 })
    await expect(page.getByText('2 in catalog')).toBeVisible({ timeout: 5000 })
  })

  test('facet rails render counts from the response', async ({ page }) => {
    await goToProjects(page)
    // The Domain rail is driven by facets.domain, which the old
    // /api/admin/projects payload had no equivalent of at all.
    await expect(page.getByRole('heading', { name: 'Domain' })).toBeVisible({ timeout: 8000 })
    await expect(page.getByText('household').first()).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('industrial').first()).toBeVisible({ timeout: 5000 })
  })

  test('clicking project card navigates to studio', async ({ page, projectsView }) => {
    await goToProjects(page)
    await projectsView.selectProject('test')
    await page.waitForTimeout(500)
    const pathname = await page.evaluate(() => window.location.pathname)
    expect(pathname).toContain('test')
  })

  test('empty state shows message', async ({ page }) => {
    // Override the mock to return empty array
    await page.unroute(CATALOG)
    await page.route(CATALOG, (route) => {
      route.fulfill({ json: catalogResponse([]) })
    })
    await goToProjects(page)
    await expect(page.getByText('No projects found').or(page.getByText('No se encontraron proyectos'))).toBeVisible({ timeout: 10000 })
    // CTA button (Import) is behind AuthGate tier="pro" — not visible for guest users
  })

  test('loading state shows loading text', async ({ page }) => {
    // Delay the response to catch loading state
    await page.unroute(CATALOG)
    await page.route(CATALOG, async (route) => {
      await new Promise(r => setTimeout(r, 3000))
      route.fulfill({ json: catalogResponse([]) })
    })
    await goToProjects(page)
    await expect(page.getByText('Loading').or(page.getByText('Cargando'))).toBeVisible({ timeout: 2000 })
  })

  test('error state shows error message with retry and demo buttons', async ({ page }) => {
    await page.unroute(CATALOG)
    await page.route(CATALOG, (route) => {
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    })
    await goToProjects(page)
    // The fetch handler throws Error(`HTTP ${status}`) before reading JSON body
    await expect(page.locator('.text-destructive').or(page.getByText('HTTP 500')).or(page.getByText('Server error'))).toBeVisible({ timeout: 10000 })
    // Retry and Open Demo buttons should be present
    await expect(page.getByText(/Retry|Reintentar/i)).toBeVisible({ timeout: 5000 })
    await expect(page.getByText(/Open Demo|Abrir Proyecto Demo/i)).toBeVisible({ timeout: 5000 })
  })

  test('retry button re-fetches projects after error', async ({ page }) => {
    // Force 500 → error state
    await page.unroute(CATALOG)
    await page.route(CATALOG, (route) => {
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    })
    await goToProjects(page)
    await expect(page.getByText(/Retry|Reintentar/i)).toBeVisible({ timeout: 10000 })

    // Restore healthy response
    await page.unroute(CATALOG)
    await page.route(CATALOG, (route) => {
      route.fulfill({ json: catalogResponse() })
    })

    // Click retry → projects should load
    await page.getByText(/Retry|Reintentar/i).click()
    await expect(page.getByText('Test Project')).toBeVisible({ timeout: 10000 })
  })

  test('demo button navigates to fallback project', async ({ page }) => {
    await page.unroute(CATALOG)
    await page.route(CATALOG, (route) => {
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    })
    await goToProjects(page)
    await expect(page.getByText(/Open Demo|Abrir Proyecto Demo/i)).toBeVisible({ timeout: 10000 })

    // Click demo → navigates to gridfinity
    await page.getByText(/Open Demo|Abrir Proyecto Demo/i).click()
    await page.waitForURL('**/project/gridfinity**', { timeout: 10000 })
    const pathname = await page.evaluate(() => window.location.pathname)
    expect(pathname).toContain('/project/gridfinity')
  })
})
