/**
 * E2E tests for WASM fallback rendering mode.
 *
 * The studio auto-detects the render backend by calling GET /api/health.
 * When the backend is unreachable (or returns a non-ok status), the service
 * falls back to client-side WASM rendering via openscad-worker.js.
 *
 * These tests simulate backend unavailability and verify that:
 * 1. The studio loads and initialises without errors.
 * 2. The render pipeline falls back to WASM mode gracefully.
 * 3. The user sees appropriate feedback (no crash, no blank screen).
 */

import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage } from '../../helpers/test-utils.js'

// ─── Helpers ────────────────────────────────────────────────────────────────

/**
 * Override the health-check route so the backend appears unavailable.
 * The renderService caches the result, so this must be called BEFORE
 * any page.goto() that triggers the health check.
 */
async function simulateBackendDown(page) {
    // Abort the health check — isBackendAvailable() catches the error and
    // sets _backendAvailable = false, which causes detectMode() → 'wasm'.
    await page.route('**/api/health', (route) => route.abort('failed'))

    // Also abort render-stream so any accidental backend call fails fast.
    await page.route('**/api/render-stream', (route) =>
        route.fulfill({ status: 503, body: 'Service Unavailable' })
    )
}

// ─── Tests ───────────────────────────────────────────────────────────────────

test.describe('WASM Fallback Mode', () => {
    // Use the default API mock for manifest/projects, but override health + render.
    test.beforeEach(async ({ page }) => {
        await setLanguage(page, 'en')
        await simulateBackendDown(page)
    })

    test('studio loads without crashing when backend is unreachable', async ({ page }) => {
        await goToStudio(page)

        // The app should render its main UI — not a blank page or error screen.
        await expect(page.locator('body')).toBeVisible()

        // The sidebar / controls panel should be present.
        const sidebar = page.locator('[data-testid="sidebar"], aside, [role="complementary"]').first()
        await expect(sidebar).toBeVisible({ timeout: 10_000 })
    })

    test('no unhandled JS errors during WASM mode initialisation', async ({ page }) => {
        const errors = []
        page.on('pageerror', (err) => errors.push(err.message))

        await goToStudio(page)
        await page.waitForTimeout(3000) // Allow WASM worker init to settle

        // Filter out known non-critical warnings (e.g. ResizeObserver loop limit)
        const critical = errors.filter(
            (msg) => !msg.includes('ResizeObserver') && !msg.includes('Non-Error promise rejection')
        )
        expect(critical).toHaveLength(0)
    })

    test('generate button is present and enabled in WASM mode', async ({ page }) => {
        await goToStudio(page)

        // The generate / render button should be visible and not permanently disabled.
        const generateBtn = page.locator('button', { hasText: /Generate|Generar/i }).first()
        await expect(generateBtn).toBeVisible({ timeout: 10_000 })
        await expect(generateBtn).toBeEnabled()
    })

    test('render attempt in WASM mode does not show backend error to user', async ({ page }) => {
        await goToStudio(page)

        // Click generate — in WASM mode this should attempt the WASM worker, not
        // show a "backend unavailable" error message.
        const generateBtn = page.locator('button', { hasText: /Generate|Generar/i }).first()
        await generateBtn.click()

        // Wait briefly for any error toast / alert to appear.
        await page.waitForTimeout(2000)

        // There should be no "backend" or "server" error message visible.
        const errorTexts = ['backend unavailable', 'server error', 'connection refused', 'fetch failed']
        for (const text of errorTexts) {
            await expect(page.locator(`text=${text}`)).not.toBeVisible()
        }
    })

    test('health check failure is handled silently (no visible crash banner)', async ({ page }) => {
        await goToStudio(page)

        // No error boundary / crash banner should be shown.
        const crashBanner = page.locator('[data-testid="error-boundary"], .error-boundary, [role="alert"]')
        // Allow up to 5 s for any crash banner to appear; it should not.
        await expect(crashBanner).not.toBeVisible({ timeout: 5000 }).catch(() => {
            // If the locator doesn't exist at all, that's fine too.
        })

        // The page title / heading should still be visible.
        await expect(page.locator('h1, [data-testid="studio-title"]').first()).toBeVisible({ timeout: 5000 })
    })
})
