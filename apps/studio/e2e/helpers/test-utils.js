/**
 * Shared test utilities for Playwright E2E tests.
 */
import { expect } from '@playwright/test'

/**
 * Wait for the app to fully load (manifest fetched, UI rendered).
 * @param {import('@playwright/test').Page} page
 */
export async function waitForAppReady(page) {
  await page.waitForSelector('header', { timeout: 15_000 })
}

/**
 * Pages that asked for the backend render path, so goToStudio knows to append
 * `?render=backend`. A WeakMap rather than a flag on the page object: it keeps
 * the marker out of Playwright's own surface and lets it be collected with the
 * page. Set by forceBackendRender, read by studioUrl.
 */
const _forcedBackendPages = new WeakMap()

/**
 * Build the studio URL for a slug, carrying the render-mode override when the
 * test asked for one. Kept next to goToStudio because they must agree about
 * where the `render` param goes.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} slug
 */
function studioUrl(page, slug) {
  const base = `/project/${slug}`
  return _forcedBackendPages.get(page) ? `${base}?render=backend` : base
}

/**
 * Pin the render pipeline to the backend (SSE) path so route mocks govern it.
 *
 * PRIMARY MECHANISM: the app's own `?render=backend` override, which
 * detectMode() consults before it probes /api/health and before the hardware
 * heuristic. This is a supported product feature (see apps/studio/README.md,
 * "Render Mode Override"), so the tests now pin the path the same way support
 * tells a user to, instead of lying to the app about the machine.
 *
 * Why the override was needed at all: detectMode() picks between 'backend' and
 * 'wasm', and with no VITE_API_BASE set (the E2E build) the deciding branch was
 *
 *   hasWasmCapabilities() = navigator.hardwareConcurrency >= 4 && deviceMemory >= 4
 *
 * which makes the render path a property of the RUNNER, not of the test. On a
 * GitHub-hosted runner (2 cores) the app chose 'backend' and every
 * `page.route('**\/api/render-stream')` mock in the suite applied; on the
 * madfam-runners-blue ARC pods — and on any developer laptop with >= 4 cores —
 * it chose 'wasm' instead, the render never touched the network, and the mocks
 * were dead code. The WASM path then fails with "OpenSCAD exited with code 1"
 * (no WASM binary is shipped to the E2E environment) after an unbounded,
 * machine-dependent delay.
 *
 * FALLBACK: the hardwareConcurrency spoof stays, deliberately. It is what makes
 * this helper work for a navigation that does NOT go through goToStudio — a
 * bare `page.goto('/project/test')`, a `page.goto(landingUrl())`, an in-app
 * click-through — since only goToStudio knows to append the query param. It
 * also keeps the helper honest against a build predating the override. The two
 * agree by construction: both select 'backend', so whichever one the app reads
 * first gives the same answer.
 *
 * Must be called BEFORE the navigation whose render it should govern:
 * addInitScript only applies to subsequent page loads, and the URL is only read
 * at app startup.
 *
 * 05-export still does the spoof inline for one test; this is the shared version.
 *
 * Do NOT use it in 19-wasm-fallback, which deliberately exercises the WASM path
 * (it forces it by aborting /api/health, independent of both mechanisms here).
 *
 * @param {import('@playwright/test').Page} page
 */
export async function forceBackendRender(page) {
  _forcedBackendPages.set(page, true)
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'hardwareConcurrency', { value: 2, configurable: true })
  })
}

/**
 * Locator for the sidebar's Generate button (the ActionDock primary action).
 *
 * While a render is in flight the same button renders `t("btn.proc")`
 * ("Processing...") instead, so its presence is the app's own "render idle"
 * signal — see StudioSidebar.ActionDock.
 *
 * @param {import('@playwright/test').Page | import('@playwright/test').Locator} scope
 */
export function generateButton(scope) {
  return scope.locator('button').filter({ hasText: /Generate|Generar/ }).first()
}

/**
 * Wait until no render is in flight: the Generate button is back and enabled.
 *
 * Replaces `await page.waitForTimeout(n)` before render-dependent assertions.
 * A fixed sleep encodes one machine's render speed; on the slower ARC pods the
 * auto-render that fires on manifest load was still running when the test
 * looked, so the sidebar showed "Processing..." and every locator asking for
 * "Generate" reported "element(s) not found" (run 32565668502:
 * 12-responsive:281, 12-responsive:254, 09-keyboard:56).
 *
 * @param {import('@playwright/test').Page} page
 * @param {number} [timeout]
 */
export async function waitForRenderSettled(page, timeout = 30_000) {
  const generate = generateButton(page)
  await generate.waitFor({ state: 'visible', timeout })
  await page.waitForFunction(
    () => {
      const btns = [...document.querySelectorAll('button')]
      const gen = btns.find((b) => /Generate|Generar/.test(b.textContent || ''))
      return !!gen && !gen.disabled
    },
    null,
    { timeout },
  )
}

/**
 * Navigate to studio view and ensure mock manifest is loaded.
 * Clicks the first mode tab to activate it, since the fallback manifest's
 * modes may differ from the mock manifest, leaving tabs in inactive state.
 * Carries `?render=backend` when forceBackendRender() was called for this page.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} [slug='test']
 */
export async function goToStudio(page, slug = 'test') {
  await page.goto(studioUrl(page, slug))
  await waitForAppReady(page)
  // Wait for mock manifest to load (Test Project appears in header).
  // The fallback manifest loads instantly but the mock API response takes
  // ~500-1000ms to propagate through React state.
  await page.locator('header h1', { hasText: 'Test Project' })
    .waitFor({ timeout: 8000 })
    .catch(() => { }) // fallback: continue even if mock didn't load

  // Wait for URL to fully settle (auto-redirect adds preset/mode segments).
  // This prevents the race condition where preset application fires after
  // goToStudio returns, overwriting values the test just edited.
  await page.waitForURL(/\/project\/[^/]+\/[^/]+\/[^/]+/, { timeout: 5000 })
    .catch(() => { })

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
    .catch(() => { })
  // Wait for slider values to be populated (guards against manifest-params race)
  await page.locator('[role="button"]').filter({ hasText: /^\d/ }).first()
    .waitFor({ timeout: 3000 })
    .catch(() => { })

  // Give React time to apply preset values and settle after all waits
  await page.waitForTimeout(500)
}

/**
 * Wait until the mode tabs the app is showing come from the LOADED manifest
 * rather than the fallback one, and return their ids in order.
 *
 * Why this exists: ManifestProvider seeds its state with
 * src/config/fallback-manifest.json (gridfinity: bin, baseplate, cup,
 * baseplate_scad, lid) and only later swaps in the fetched/mocked manifest
 * (test: cup, single, grid). useKeyboardShortcuts closes over that `modes`
 * array and maps Cmd/Ctrl+N to `modes[N - 1].id`, so a keystroke sent during
 * the window before the swap dispatches a mode id from the WRONG list —
 * "baseplate" for Cmd+2 — which does not exist in the loaded manifest. The app
 * then stays on its current mode, and no amount of polling recovers, because
 * the keystroke has already been spent. That is the whole 09-keyboard
 * Cmd/Ctrl+2 flake: it is a race on manifest arrival, not on rendering speed,
 * which is why raising the poll timeout would not have fixed it and why it
 * moved between the chromium and webkit shards run to run.
 *
 * Note this race is invisible to Cmd/Ctrl+1, since fallback modes[0] ("bin")
 * and loaded modes[0] ("cup", label "Start") both satisfy that test's
 * assertion — it passes whether or not the manifest had landed. Callers should
 * use this helper before ANY numeric mode shortcut, not just the ones observed
 * failing.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string[]} expectedModeIds - mode ids of the loaded manifest, in order
 * @param {number} [timeout]
 * @returns {Promise<string[]>}
 */
export async function waitForModesReady(page, expectedModeIds, timeout = 15_000) {
  // Assert against the app's own rendered tablist — the same source of truth
  // getActiveMode() reads — rather than a proxy like the header title, which
  // updates from a different piece of state and can land first.
  const tablist = page.locator('[role="tablist"][aria-label="Mode selection"]:visible').first()
  await tablist.waitFor({ state: 'visible', timeout })
  await expect
    .poll(
      async () => {
        const tabs = tablist.locator('[role="tab"]')
        const count = await tabs.count()
        const ids = []
        for (let i = 0; i < count; i++) {
          ids.push(
            (await tabs.nth(i).getAttribute('data-value')) ??
            ((await tabs.nth(i).textContent()) || '').trim().toLowerCase(),
          )
        }
        return ids
      },
      {
        timeout,
        message:
          'Mode tabs never matched the loaded manifest — the app is probably still ' +
          'showing the fallback manifest, so Cmd/Ctrl+N would dispatch a mode id ' +
          'from the wrong list.',
      },
    )
    .toHaveLength(expectedModeIds.length)
  return expectedModeIds
}

/**
 * Press Cmd/Ctrl+N to switch mode, only once the loaded manifest's modes are
 * the ones the shortcut handler will index into.
 *
 * @param {import('@playwright/test').Page} page
 * @param {number} n - 1-based mode index, as the shortcut treats it
 * @param {string[]} expectedModeIds - mode ids of the loaded manifest, in order
 */
export async function pressModeShortcut(page, n, expectedModeIds) {
  await waitForModesReady(page, expectedModeIds)
  const mac = await isMac(page)
  await page.keyboard.press(mac ? `Meta+${n}` : `Control+${n}`)
}

/**
 * Navigate to projects view.
 * @param {import('@playwright/test').Page} page
 */
export async function goToProjects(page) {
  await page.goto('/projects')
  await waitForAppReady(page)
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
    localStorage.setItem('gridfinity-lang', l)
    localStorage.setItem('tablaco-lang', l)
    localStorage.setItem('custom-msh-lang', l)
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
 * Get the current URL pathname.
 * @param {import('@playwright/test').Page} page
 */
export async function getPathname(page) {
  return page.evaluate(() => window.location.pathname)
}

/**
 * Get the current URL search params.
 * @param {import('@playwright/test').Page} page
 */
export async function getSearchParams(page) {
  return page.evaluate(() => window.location.search)
}

/**
 * Get the current URL hash.
 * @param {import('@playwright/test').Page} page
 */
export async function getHash(page) {
  return page.evaluate(() => window.location.hash)
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

/**
 * Enable clipboard access cross-browser.
 * Chromium: uses grantPermissions (native, reliable).
 * Firefox/WebKit: mocks clipboard API via page.evaluate.
 * Call after page has navigated (needs a live page context).
 * @param {import('@playwright/test').Page} page
 */
export async function enableClipboard(page) {
  const browserName = page.context().browser()?.browserType()?.name() || 'chromium'
  if (browserName === 'chromium') {
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
  } else {
    await page.evaluate(() => {
      window.__clipboardText = ''
      if (!navigator.clipboard) {
        Object.defineProperty(navigator, 'clipboard', {
          value: {}, writable: true, configurable: true
        })
      }
      navigator.clipboard.writeText = async (text) => { window.__clipboardText = text }
      navigator.clipboard.readText = async () => window.__clipboardText
    })
  }
}

/**
 * Read text from clipboard (works with both grantPermissions and mock).
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<string>}
 */
export async function readClipboard(page) {
  return page.evaluate(async () => {
    if (window.__clipboardText !== undefined) return window.__clipboardText
    return navigator.clipboard.readText()
  })
}
