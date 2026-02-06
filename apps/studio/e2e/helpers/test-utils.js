/**
 * Shared test utilities for Playwright E2E tests.
 */

/**
 * Wait for the app to fully load (manifest fetched, UI rendered).
 * @param {import('@playwright/test').Page} page
 */
export async function waitForAppReady(page) {
  await page.waitForSelector('header', { timeout: 15_000 })
}

/**
 * Navigate to studio view and ensure mock manifest is loaded.
 * Clicks the first mode tab to activate it, since the fallback manifest's
 * modes may differ from the mock manifest, leaving tabs in inactive state.
 * @param {import('@playwright/test').Page} page
 * @param {string} [slug='test']
 */
export async function goToStudio(page, slug = 'test') {
  await page.goto(`/#/${slug}`)
  await waitForAppReady(page)
  // Wait for mock manifest to load (Test Project appears in header).
  // The fallback manifest loads instantly but the mock API response takes
  // ~500-1000ms to propagate through React state.
  await page.locator('header h1', { hasText: 'Test Project' })
    .waitFor({ timeout: 8000 })
    .catch(() => {}) // fallback: continue even if mock didn't load
  // Ensure a mode tab is active. After mock manifest loads, the mode state
  // may still reference the fallback's modes. Click the first tab to fix.
  const activeTab = page.locator('[role="tab"][data-state="active"]')
  if (await activeTab.count() === 0) {
    const firstTab = page.locator('[role="tab"]').first()
    if (await firstTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstTab.click()
      await page.waitForTimeout(500)
    }
  }
  // Wait for controls to render (sliders/buttons should be visible)
  await page.locator('[role="slider"]').first()
    .waitFor({ timeout: 5000 })
    .catch(() => {})
}

/**
 * Navigate to projects view.
 * @param {import('@playwright/test').Page} page
 */
export async function goToProjects(page) {
  // First load the app (initial mount overwrites hash), then navigate to projects
  await page.goto('/')
  await waitForAppReady(page)
  await page.waitForTimeout(500)
  await page.evaluate(() => { window.location.hash = '#/projects' })
  await page.waitForTimeout(500)
}

/**
 * Set language via localStorage before navigation.
 * Must be called BEFORE goToStudio/goToProjects to take effect on app init.
 * Uses addInitScript to inject into every page load.
 * @param {import('@playwright/test').Page} page
 * @param {'en'|'es'} lang
 */
export async function setLanguage(page, lang) {
  await page.addInitScript((l) => {
    // The app uses `${projectSlug}-lang` as the storage key.
    // Set all likely keys so language works regardless of which project loads.
    localStorage.setItem('yantra4d-lang', l)
    localStorage.setItem('test-lang', l)
    localStorage.setItem('demo-lang', l)
    localStorage.setItem('tablaco-lang', l)
    localStorage.setItem('null-lang', l)
    localStorage.setItem('undefined-lang', l)
  }, lang)
}

/**
 * Set theme via localStorage before navigation.
 * Must be called BEFORE goToStudio/goToProjects to take effect on app init.
 * @param {import('@playwright/test').Page} page
 * @param {'light'|'dark'|'system'} theme
 */
export async function setTheme(page, theme) {
  await page.addInitScript((t) => {
    // ThemeProvider uses 'vite-ui-theme' as storage key (passed via storageKey prop)
    localStorage.setItem('vite-ui-theme', t)
  }, theme)
}

/**
 * Get the current URL hash.
 * @param {import('@playwright/test').Page} page
 */
export async function getHash(page) {
  return page.evaluate(() => window.location.hash)
}

/**
 * Get the current URL search params.
 * @param {import('@playwright/test').Page} page
 */
export async function getSearchParams(page) {
  return page.evaluate(() => window.location.search)
}

/**
 * Simulate keyboard shortcut.
 * @param {import('@playwright/test').Page} page
 * @param {string} key - e.g. 'z', 'Enter'
 * @param {{meta?: boolean, shift?: boolean, control?: boolean}} modifiers
 */
export async function pressShortcut(page, key, { meta = false, shift = false, control = false } = {}) {
  const modifierKeys = []
  if (meta) modifierKeys.push('Meta')
  if (control) modifierKeys.push('Control')
  if (shift) modifierKeys.push('Shift')
  const combo = [...modifierKeys, key].join('+')
  await page.keyboard.press(combo)
}

/**
 * Check if platform is macOS (for keyboard shortcuts).
 * @param {import('@playwright/test').Page} page
 */
export async function isMac(page) {
  return page.evaluate(() => navigator.platform.includes('Mac'))
}
