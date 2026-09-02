import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage } from '../../helpers/test-utils.js'

/**
 * A private project answers the manifest fetch with 403 and
 * `error_code: "project_locked"`. The studio must say so — the "project
 * doesn't exist" page would be wrong (the project exists, it is just not
 * visible to this caller) and so would the "can't reach the server" page (the
 * server answered).
 *
 * The fixture's mockAPIs stay ON: /api/projects and /api/catalog/search must
 * keep answering, because ManifestProvider only fetches a manifest once the
 * projects list has resolved, and "Browse Projects" needs the catalog.
 * Only the two manifest routes are replaced.
 */
const LOCKED_BODY = {
  status: 'error',
  error: 'This project is private',
  error_code: 'project_locked',
  auth_required: true,
  request_id: 'e2e-private-project',
}

async function lockManifest(page, body = LOCKED_BODY) {
  // Unroute first: the fixture registered its own manifest handlers before this
  // hook ran, and replacing them is clearer than relying on match ordering.
  await page.unroute('**/api/projects/*/manifest')
  await page.unroute('**/api/manifest')
  await page.route('**/api/projects/*/manifest', (route) => {
    route.fulfill({ status: 403, json: body })
  })
  await page.route('**/api/manifest', (route) => {
    route.fulfill({ status: 403, json: body })
  })
}

test.describe('Private project', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  test('a locked manifest shows the private-project screen, not "not found"', async ({ page }) => {
    await lockManifest(page)
    await page.goto('/project/private-demo')

    await expect(page.getByRole('heading', { name: /Private Project/i })).toBeVisible()
    await expect(page.getByText(/Sign in with an authorized account/i)).toBeVisible()
    // The two pre-existing error pages must not be what the user sees.
    await expect(page.getByText(/doesn't exist/i)).toHaveCount(0)
    await expect(page.getByText(/Can't Reach the Server/i)).toHaveCount(0)
    // Reloading anonymously gets the same 403, so no Retry is offered.
    await expect(page.getByRole('button', { name: /^Retry$/ })).toHaveCount(0)
  })

  test('a locked manifest for an authorized-but-denied account explains why', async ({ page }) => {
    await lockManifest(page, { ...LOCKED_BODY, auth_required: false })
    await page.goto('/project/private-demo')

    await expect(page.getByRole('heading', { name: /Private Project/i })).toBeVisible()
    await expect(page.getByText(/is private and this account/i)).toBeVisible()
    await expect(page.getByText(/Sign in with an authorized account/i)).toHaveCount(0)
  })

  test('the private-project screen offers a way back to the public catalog', async ({ page }) => {
    await lockManifest(page)
    await page.goto('/project/private-demo')

    await page.getByRole('button', { name: /Browse Projects/i }).click()
    await expect(page).toHaveURL(/\/projects/)
  })
})
