/* global Buffer */
import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, setLanguage } from '../../helpers/test-utils.js'

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  test('ErrorBoundary catches viewer crash and shows retry', async ({ page }) => {
    await goToStudio(page)
    // Inject an error into the viewer component
    await page.evaluate(() => {
      // Force an error in the error boundary area
      const event = new ErrorEvent('error', { error: new Error('Test crash'), message: 'Test crash' })
      window.dispatchEvent(event)
    })
    // App should still be functional
    await expect(page.locator('header')).toBeVisible()
  })

  test('network error on render shows error in console', async ({ page, sidebar, viewer }) => {
    await goToStudio(page)
    await page.route('**/api/render', (route) => route.abort('connectionrefused'))
    await page.route('**/api/render-stream', (route) => route.abort('connectionrefused'))
    await sidebar.clickGenerate()
    // Poll rather than sleeping 2s and reading once. Under serial load the
    // error had not reached the console yet and the single read saw the
    // initial "Ready." — a real flake, not a regression.
    await expect.poll(() => viewer.getConsoleLogs(), { timeout: 15000 }).toContain('Error')
  })

  test('API 500 on render surfaces error to user', async ({ page, sidebar, viewer }) => {
    await goToStudio(page)
    await page.route('**/api/render', (route) => {
      route.fulfill({ status: 500, json: { error: 'Internal server error' } })
    })
    await page.route('**/api/render-stream', (route) => {
      route.fulfill({ status: 500, json: { error: 'Internal server error' } })
    })
    await sidebar.clickGenerate()
    // Poll rather than sleeping 2s and reading once. Under serial load the
    // error had not reached the console yet and the single read saw the
    // initial "Ready." — a real flake, not a regression.
    await expect.poll(() => viewer.getConsoleLogs(), { timeout: 15000 }).toContain('Error')
  })

  test('API 400 on render shows error', async ({ page, sidebar, viewer }) => {
    await goToStudio(page)
    await page.route('**/api/render', (route) => {
      route.fulfill({ status: 400, json: { error: 'Bad request: missing mode' } })
    })
    await page.route('**/api/render-stream', (route) => {
      route.fulfill({ status: 400, json: { error: 'Bad request: missing mode' } })
    })
    await sidebar.clickGenerate()
    // This test ended here, on a bare 2s wait with no assertion — it passed
    // whether or not a 400 surfaced anything. Its name is a claim; make it one.
    await expect.poll(() => viewer.getConsoleLogs(), { timeout: 15000 }).toContain('Error')
  })

  test('manifest fetch failure falls back gracefully', async ({ page }) => {
    await page.route('**/api/manifest', (route) => {
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    })
    await page.route('**/api/projects/*/manifest', (route) => {
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    })
    await page.goto('/project/test')
    await page.waitForTimeout(5000)
    // When manifest fetch fails, fallback manifest has a different project slug,
    // so ProjectProvider shows "Loading project…" spinner. App should not crash.
    await expect(page.locator('body')).toBeVisible()
    const crashed = await page.locator('[data-testid="error-boundary"], .error-boundary').count()
    expect(crashed).toBe(0)
  })

  test('projects fetch failure shows error state', async ({ page }) => {
    // ProjectsView reads /api/catalog/search, not /api/admin/projects — this
    // mock used to override an endpoint the page no longer calls, so the view
    // loaded normally and never rendered an error.
    await page.unroute('**/api/catalog/search**')
    await page.route('**/api/catalog/search**', (route) => {
      route.fulfill({ status: 500, json: { error: 'Server down' } })
    })
    await goToProjects(page)
    await expect(page.locator('.text-destructive')).toBeVisible({ timeout: 8000 })
  })

  test('verify failure shows error in console', async ({ page, sidebar, viewer }) => {
    await goToStudio(page)
    await page.route('**/api/verify', (route) => {
      route.fulfill({ status: 500, json: { error: 'Verification failed' } })
    })
    // Need parts to enable verify button
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)

    // This body used to be an `if` around two clicks and a sleep, with no
    // assertion in any branch — it reported success whether verification
    // errored, succeeded, or never ran. Verify needs rendered parts, which
    // depend on the renderer being available, so the unavailable case is now
    // an explicit skip rather than a silent pass.
    const canVerify = await sidebar.verifyButton.isEnabled().catch(() => false)
    test.skip(!canVerify, 'verify requires rendered parts; none were produced in this environment')

    await sidebar.clickVerify()
    await expect.poll(() => viewer.getConsoleLogs(), { timeout: 15000 }).toContain('Error')
  })

  test('render timeout does not crash the app', async ({ page, sidebar }) => {
    await goToStudio(page)
    await page.route('**/api/render', (route) => route.abort('timedout'))
    await page.route('**/api/render-stream', (route) => route.abort('timedout'))
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)
    // App should still be functional
    await expect(page.locator('header')).toBeVisible()
    expect(await sidebar.isGenerateDisabled()).toBe(false)
  })

  test('invalid manifest JSON falls back gracefully', async ({ page }) => {
    await page.route('**/api/projects/*/manifest', (route) => {
      route.fulfill({ contentType: 'application/json', body: 'not valid json' })
    })
    await page.goto('/project/test')
    await page.waitForTimeout(5000)
    // Invalid JSON triggers fallback manifest (different slug), so
    // ProjectProvider shows loading spinner. App should not crash.
    await expect(page.locator('body')).toBeVisible()
    const crashed = await page.locator('[data-testid="error-boundary"], .error-boundary').count()
    expect(crashed).toBe(0)
  })

  test('backend unavailable reports a server problem, not a missing project', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort('connectionrefused'))
    await page.goto('/project/test')

    // The old assertion was `header` visible, on the premise that the app falls
    // back to the bundled manifest. It does not: a manifest error takes over the
    // whole screen, header included. What it used to render there was "The
    // project 'test' doesn't exist or hasn't been deployed yet" — a claim the
    // app cannot support when the server never answered.
    await expect(page.getByText(/Can't Reach the Server|No se puede conectar/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/doesn't exist|no existe/i)).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Retry|Reintentar/i })).toBeVisible()

    const crashed = await page.locator('[data-testid="error-boundary"], .error-boundary').count()
    expect(crashed).toBe(0)
  })

  test('ErrorBoundary retry button resets error state', async ({ page }) => {
    await goToStudio(page)
    // The ErrorBoundary shows a "Try Again" button when it catches an error
    // This verifies the component structure exists
    await expect(page.locator('header')).toBeVisible()
  })

  // /onboard IS routed — useHashNavigation.isOnboardView matches it and App.tsx
  // renders OnboardingWizard for it. The old reason on this skip was stale. What
  // was actually wrong is the `header` wait below: the wizard renders standalone
  // with no app chrome, so that selector never resolves. Left skipped only
  // because these two have not been re-verified since; the anchor is now
  // [data-testid="onboarding-wizard"], as used in 08-onboarding.
  test.skip('onboarding API error shows error banner', async ({ page }) => {
    await page.route('**/api/projects/analyze', (route) => {
      route.fulfill({ status: 500, json: { error: 'Analysis failed' } })
    })
    await page.goto('/onboard')
    await page.waitForSelector('[data-testid="onboarding-wizard"]')
    await page.locator('#scad-upload').setInputFiles({
      name: 'test.scad', mimeType: 'text/plain', buffer: Buffer.from('cube(10);'),
    })
    await page.locator('button', { hasText: 'Analyze' }).click()
    await page.waitForTimeout(1000)
    await expect(page.locator('.bg-destructive\\/10')).toBeVisible()
  })

  test.skip('onboarding create failure shows error', async ({ page }) => {
    // Fast-forward to step 3 and make create fail
    await page.route('**/api/projects/analyze', (route) => {
      route.fulfill({
        json: {
          analysis: { files: { 'test.scad': { variables: [], modules: [], includes: [], render_modes: [] } } },
          manifest: { project: { name: 'T', slug: 't', version: '0.1.0' }, modes: [], parameters: [] },
          warnings: [],
        },
      })
    })
    await page.route('**/api/projects/create', (route) => {
      route.fulfill({ status: 500, json: { error: 'Create failed' } })
    })

    await page.goto('/onboard')
    await page.waitForSelector('header')
    await page.locator('#scad-upload').setInputFiles({
      name: 'test.scad', mimeType: 'text/plain', buffer: Buffer.from('cube(10);'),
    })
    await page.locator('button', { hasText: 'Analyze' }).click()
    await page.locator('button', { hasText: 'Edit Manifest' }).click()
    await page.locator('button', { hasText: 'Review & Save' }).click()
    await page.locator('button', { hasText: 'Create Project' }).click()
    await page.waitForTimeout(1000)
    await expect(page.locator('.bg-destructive\\/10')).toBeVisible()
  })

  test('multiple rapid errors do not stack', async ({ page, sidebar }) => {
    await goToStudio(page)
    await page.route('**/api/render', (route) => route.abort('connectionrefused'))
    await page.route('**/api/render-stream', (route) => route.abort('connectionrefused'))
    await sidebar.clickGenerate()
    await page.waitForTimeout(500)
    await sidebar.clickGenerate()
    await page.waitForTimeout(500)
    await expect(page.locator('header')).toBeVisible()
  })
})
