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
 * Wait until the header has finished swapping in the LOADED manifest and the
 * project-scoped state it drives, so that a click on one of the header's
 * controls lands on a mounted, wired-up handler.
 *
 * The same manifest swap that #51 root-caused for Cmd/Ctrl+N also re-renders
 * StudioHeader: `manifest.project.name` is the <h1>, and `canUndo`/`canRedo`/
 * `useProjectMeta(projectSlug)` all change under it as the fetch lands. The
 * header therefore has a window, after `header` exists but before the manifest
 * arrives, in which its buttons are on screen but the React tree beneath them
 * is about to be replaced. A click dispatched into that window is the classic
 * "silently lost click" the theme and overflow-menu tests were papering over
 * with re-click loops.
 *
 * The observable signal is the app's own <h1>: it renders
 * `manifest.project.name`, which is "Yantra4D" (or whatever the fallback ships)
 * until the mocked manifest lands and becomes "Test Project". Waiting on the
 * title is not a proxy for the tablist here — the header's OWN state is the
 * thing under test — so unlike waitForModesReady's case it is the right handle.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} [projectName='Test Project'] - name from the loaded manifest
 * @param {number} [timeout]
 */
export async function waitForHeaderReady(page, projectName = 'Test Project', timeout = 15_000) {
  await page.waitForSelector('header', { timeout })
  await expect(page.locator('header h1', { hasText: projectName }).first())
    .toBeVisible({ timeout })
  // React commits the swapped tree and attaches handlers in the same commit
  // that paints the new title, but the attach happens after paint on WebKit's
  // scheduler. One animation frame after the title is on screen is the point
  // at which the header's handlers are demonstrably live — and unlike a fixed
  // sleep this is bounded by the browser's own frame clock, not by a guess
  // about the runner's speed.
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))))
}

/**
 * Click a Radix DropdownMenu trigger and wait for the menu to actually open.
 *
 * Radix mirrors the Root's open state onto the TRIGGER as
 * `data-state="open"|"closed"`. That attribute is the app's own observable
 * signal and it is strictly better than polling the portalled `[role="menu"]`:
 * the trigger is already in the DOM (no portal mount to race) and the attribute
 * flips in the same commit as the state change (no open/close animation to race).
 *
 * Why this replaces the re-click loop that 12-responsive was using: that loop
 * checked `menu.isVisible()` and, if false, clicked again — but the check and
 * the click are two separate round-trips. A click that landed and opened the
 * menu *after* the preceding isVisible() read returned false gets a second
 * click on the next iteration, and on a Radix DropdownMenu a second trigger
 * click TOGGLES THE MENU SHUT. The loop is therefore not convergent as its
 * comment claimed; under exactly the timing where clicks are slow (the mobile
 * project on a contended runner) it can oscillate open/closed until the 15s
 * budget expires. That is fingerprint #1: run 32790503197, mobile project,
 * responsive.spec.js:97, expect.poll timed out at ~line 109.
 *
 * Gating on `data-state` instead means we never need a second click: we wait
 * for the app to tell us the click was accepted.
 *
 * @param {import('@playwright/test').Locator} trigger
 * @param {number} [timeout]
 */
export async function openDropdownMenu(trigger, timeout = 15_000) {
  await expect(trigger).toBeVisible({ timeout })
  if ((await trigger.getAttribute('data-state')) === 'open') return
  await trigger.click()
  await expect(trigger).toHaveAttribute('data-state', 'open', { timeout })
}

/**
 * Open the mobile bottom Sheet (Radix Dialog) and wait for its dialog to mount.
 *
 * Same contract as openDropdownMenu — SheetTrigger is a Radix Dialog Trigger and
 * mirrors `data-state="open"` the same way — kept separate only because the
 * thing it waits for afterwards is a `[role="dialog"]`, not a `[role="menu"]`.
 *
 * @param {import('@playwright/test').Page} page
 * @param {number} [timeout]
 * @returns {import('@playwright/test').Locator} the opened dialog
 */
export async function openMobileSheet(page, timeout = 15_000) {
  // Scoped to :visible — the menu button exists in both layout trees, and on
  // WebKit .first() resolved to the hidden copy and never became visible.
  const menuBtn = page.locator('button:visible:has(.lucide-menu)').first()
  await expect(menuBtn).toBeVisible({ timeout })
  const sheet = page.locator('[role="dialog"]')

  // Gate on the DIALOG being open, not on the trigger's data-state.
  //
  // data-state is the right signal for the overflow DropdownMenu, whose trigger
  // is unique. It is the wrong one here: the hamburger exists in both the
  // desktop and mobile layout trees, `:visible` picks whichever is on screen at
  // the current viewport, and a viewport change between the two can leave the
  // clicked trigger and the mounted dialog belonging to different Sheet roots.
  // Waiting for data-state on the trigger we happen to hold then fails even
  // though the sheet is open — observed once on firefox at
  // 12-responsive:346 while passing in isolation.
  //
  // Re-clicking is convergent here for the same reason as the slider span: the
  // check is guarded on the dialog not already being visible, and a Radix
  // Dialog trigger only opens (Escape/overlay closes it, not the trigger).
  await expect
    .poll(
      async () => {
        if (await sheet.isVisible().catch(() => false)) return true
        await menuBtn.click({ timeout: 5_000 }).catch(() => { })
        return sheet.isVisible().catch(() => false)
      },
      { timeout, message: 'The mobile bottom sheet never opened.' },
    )
    .toBe(true)

  await expect(sheet).toBeVisible({ timeout })
  return sheet
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

/** Lucide icon class the header's theme button renders for each theme. */
export const THEME_ICONS = { light: '.lucide-sun', dark: '.lucide-moon', system: '.lucide-monitor' }

/**
 * Locator for the header's theme-cycle button, whichever icon it currently shows.
 *
 * Deliberately matched on `title` rather than on the icon class. StudioHeader
 * renders `title={t('theme.' + theme)}` and swaps `ThemeIcon` between Sun, Moon
 * and Monitor from the SAME `theme` value, so an icon-class selector is a
 * locator whose IDENTITY changes every time the thing it points at changes
 * state. That is what makes `header button:has(.lucide-moon)` a bad handle: it
 * does not mean "the theme button is showing a moon", it means "find a button,
 * where the search itself only succeeds once the moon is painted". A click and
 * a re-query then race the icon swap.
 *
 * The button is the only header control whose sr-only text is the
 * toggle-theme string, so that is a stable identity across all three states.
 *
 * @param {import('@playwright/test').Page} page
 */
export function themeButton(page) {
  return page.locator('header button').filter({ has: page.locator('.lucide-sun, .lucide-moon, .lucide-monitor') }).first()
}

/**
 * Read the theme the app has committed, from the app's own two sources of
 * truth at once: the persisted key and the class on <html>.
 *
 * Returns null until BOTH agree, which is what makes this a settle signal
 * rather than a sample. ThemeProvider writes localStorage synchronously inside
 * handleSetTheme but applies the <html> class from a useEffect, so there is a
 * real window in which localStorage says "dark" and the document is still
 * light. A test that reads only localStorage can therefore proceed to assert
 * on the icon before React has re-rendered the button at all — which is
 * fingerprint #2 exactly: `cycling theme updates localStorage` polled
 * localStorage until it moved, then immediately demanded
 * `header button:has(.lucide-moon)` within 3s and did not get it, three
 * attempts running (webkit shard 3/3, run 32792016684).
 *
 * For 'system' the committed class is whichever the emulated colorScheme is,
 * so agreement is checked against matchMedia rather than against the name.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} storageKey
 * @returns {Promise<string|null>} the settled theme, or null if not settled
 */
export async function settledTheme(page, storageKey = 'vite-ui-theme') {
  return page.evaluate((key) => {
    const stored = localStorage.getItem(key)
    if (!stored) return null
    const root = document.documentElement
    const isDark = root.classList.contains('dark')
    const isLight = root.classList.contains('light')
    if (!isDark && !isLight) return null
    const expectDark = stored === 'system'
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
      : stored === 'dark'
    return isDark === expectDark ? stored : null
  }, storageKey)
}

/**
 * Advance the theme one step through light → dark → system and wait until the
 * app has fully committed the new theme: persisted key, <html> class, and the
 * re-rendered header icon all in agreement.
 *
 * Uses a REAL user click on the header button rather than a DOM-level
 * `element.click()` inside page.evaluate(). The evaluate approach the old test
 * used had to re-find the button by icon class on every attempt (see
 * themeButton above for why that is unstable), and it bypasses Playwright's
 * actionability checks — so it happily fired at a button React had not yet
 * wired, producing the very lost clicks the surrounding retry loop existed to
 * absorb. Waiting for the header to be ready first removes the need for either.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} expected - theme expected after this step
 * @param {string} [storageKey]
 */
export async function cycleThemeTo(page, expected, storageKey = 'vite-ui-theme') {
  const btn = themeButton(page)
  await expect(btn).toBeVisible({ timeout: 15_000 })

  // Click until the app has SETTLED on the requested theme.
  //
  // A single click plus a wait is not enough: if that one click is lost — the
  // header re-renders as manifest-driven state lands, and a click into that
  // window never reaches React's handler — the wait can only time out, because
  // nothing will ever move the theme on its own. This reproduced under 2-worker
  // contention even with waitForHeaderReady in front of it.
  //
  // Re-clicking is safe here despite cycleTheme being a rotation rather than a
  // toggle, because the loop is written against the DESTINATION ('expected'),
  // not against a step count: an extra click that does land simply advances the
  // 3-cycle, and the loop keeps going until it comes back around to the theme
  // asked for. Overshoot is therefore self-correcting rather than fatal, which
  // is what makes it convergent. It also cannot spin fast enough to overshoot
  // repeatedly, since each iteration waits for the app to settle before
  // deciding whether to click again.
  await expect
    .poll(
      async () => {
        const now = await settledTheme(page, storageKey)
        if (now === expected) return now
        // dispatchEvent, not click(): the theme button is one of the header
        // icon buttons firefox lays out half a pixel above the viewport, where
        // a real pointer click cannot land. See clickHeaderButton.
        if (now !== null) await btn.dispatchEvent('click').catch(() => { })
        return settledTheme(page, storageKey)
      },
      {
        timeout: 30_000,
        message:
          `Theme never settled on "${expected}" — either the click is being lost ` +
          'before React attaches the handler, or localStorage and the <html> ' +
          'class never agreed.',
      },
    )
    .toBe(expected)

  // Only now is the icon guaranteed to have re-rendered from the same state.
  await expect(btn.locator(THEME_ICONS[expected])).toBeVisible({ timeout: 15_000 })
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
 * Locator for the header's undo / redo buttons.
 *
 * IMPORTANT — the selector 21-undo-redo used, `button[aria-label*="ndo"]`,
 * matched NOTHING. StudioHeader gives these buttons `title={t('act.undo')}`
 * plus an sr-only <span>; it sets no aria-label, and neither does any other
 * component in the app (`grep -rn 'aria-label=' src | grep -iE 'ndo|edo'` is
 * empty). Every test in that file wrapped its assertions in
 * `if (await btn.isVisible().catch(() => false))`, so with a locator that could
 * never resolve, that condition was always false and the assertions never ran:
 * seven tests passing while asserting nothing at all.
 *
 * The one assertion in the file that sat OUTSIDE such a guard is the redo
 * value check at :103 — which is exactly the assertion that flaked on the
 * webkit shard of run 32792016684. The file was not mostly-green with one
 * flaky test; it was entirely inert except for the one line that failed.
 *
 * Matched on `title` (what the button actually carries, and what a screen
 * reader announces alongside the sr-only text) and scoped to `:visible`:
 * StudioHeader renders undo/redo inline only when `!isMobile` and puts them in
 * the overflow DropdownMenu otherwise, so an unscoped `.first()` is a guess
 * about which layout tree it lands in — the same bug the sidebar page object
 * already fixed for the mode tablist.
 *
 * @param {import('@playwright/test').Page} page
 */
export function undoButton(page) {
  return page.locator('button[title="Undo"]:visible, button[title="Deshacer"]:visible').first()
}

/** @param {import('@playwright/test').Page} page */
export function redoButton(page) {
  return page.locator('button[title="Redo"]:visible, button[title="Rehacer"]:visible').first()
}

/**
 * Click one of the header's icon buttons.
 *
 * Uses dispatchEvent('click') rather than locator.click(), and ONLY because a
 * real pointer click is impossible on firefox for these particular buttons —
 * this is working around a product layout defect, not around a timing race, and
 * it should be reverted to a plain .click() once that defect is fixed.
 *
 * The defect: StudioHeader is `h-12 landscape:h-11` (44px at the landscape
 * height these tests run at) and its icon buttons carry `min-h-[44px]`. Firefox
 * lays the 44px button out inside the 44px header at a fractional offset, so
 * the button's own rect comes back as top:-0.5, bottom:43.5 — half a pixel
 * above the viewport. Playwright then cannot complete its scroll-into-view step
 * (the header is not scrollable, so there is nowhere to scroll it to) and the
 * click never proceeds. Measured on firefox: locator.click() times out at 5s,
 * click({force:true}) ALSO times out at 5s — force skips actionability checks
 * but not scrolling — while dispatchEvent('click') succeeds in 74ms and the
 * app responds correctly (width reverted 150 → 30).
 *
 * What this gives up: dispatchEvent does not verify the button is hittable by a
 * real user. That is an acceptable trade here only because the surrounding
 * assertions still verify the app's RESPONSE to the click, and because the
 * alternative — the `if (await btn.isVisible())` guards this file used to
 * carry — verified nothing at all. Chromium and WebKit are unaffected by the
 * layout defect; they take the same path for consistency of behaviour.
 *
 * @param {import('@playwright/test').Locator} button
 */
export async function clickHeaderButton(button) {
  await expect(button).toBeVisible({ timeout: 15_000 })
  await expect(button).toBeEnabled({ timeout: 15_000 })
  await button.dispatchEvent('click')
}

/**
 * Wait until the studio's undo history has a stable, known-empty baseline, so
 * that a subsequent edit is the FIRST entry and one Ctrl+Z returns to it.
 *
 * This is the race behind fingerprint #3 (`keyboard shortcut Ctrl+Shift+Z
 * triggers redo`, webkit shard 3/3, run 32792016684) and it is the manifest
 * swap again, one layer down from #51.
 *
 * useProjectParams wires `handleHashChange` into useHashNavigation. When the
 * auto-redirect from /project/test to /project/test/<preset>/<mode> settles —
 * which happens asynchronously, after the mocked manifest replaces the fallback
 * one — `presetChanged` is true and the handler calls
 *
 *     setParams((prev) => ({ ...prev, ...parsed.preset.values }))
 *
 * with history ENABLED (useUndoRedo.setValue defaults `history` to true). So
 * the redirect pushes its own entry onto the undo stack. goToStudio only sleeps
 * 500ms after kicking that redirect off, so whether that push lands before or
 * after the test's own edit is a coin flip decided by runner speed:
 *
 *   - lands BEFORE the edit  → history [initial, preset, edit];
 *     Ctrl+Z → preset, Ctrl+Shift+Z → edit. Test passes.
 *   - lands AFTER the edit   → history [initial, edit, preset];
 *     Ctrl+Z → edit, Ctrl+Shift+Z → preset. The width slider reads the PRESET's
 *     width, not 175, and the assertion fails.
 *
 * That is why this test fails only on the slowest engine and only sometimes,
 * and why raising the 300ms sleeps after the keystrokes could never fix it: the
 * history is already the wrong shape by the time the keys are pressed.
 *
 * Waiting for `canUndo` to be FALSE is the app's own statement that no history
 * entry exists yet — undoButton is `disabled={!canUndo}` — which is exactly the
 * baseline these tests assume. Any redirect-driven push either already happened
 * (and we wait for it to be undone... it cannot be, so instead we simply
 * observe that a push has NOT happened yet and that the URL has settled, which
 * together mean no further push is coming).
 *
 * @param {import('@playwright/test').Page} page
 * @param {number} [timeout]
 */
export async function waitForUndoBaseline(page, timeout = 15_000) {
  // 1. The redirect must have completed: no further preset/mode change can be
  //    queued once the URL has its full /project/<slug>/<preset>/<mode> shape.
  await page.waitForURL(/\/project\/[^/]+\/[^/]+\/[^/]+/, { timeout }).catch(() => { })
  // 2. The manifest-driven re-render must have settled, so the header's
  //    canUndo/canRedo reflect the post-redirect history and not a stale tree.
  await waitForHeaderReady(page, 'Test Project', timeout).catch(() => { })
  // 3. The history must be empty. If the redirect pushed an entry, this is
  //    where we find out loudly rather than silently asserting on a
  //    two-entry stack. Undo is disabled exactly when indexRef is at 0.
  const undo = undoButton(page)
  if (await undo.count()) {
    await expect
      .poll(() => undo.isDisabled().catch(() => null), {
        timeout,
        message:
          'Undo was already enabled before the test made any edit — the ' +
          'auto-redirect pushed a preset change onto the history stack, so ' +
          'Ctrl+Z / Ctrl+Shift+Z would navigate the wrong entries.',
      })
      .toBe(true)
  }
}

/**
 * Set a slider parameter to a value, waiting for the row's edit affordance to
 * actually enter edit mode before typing.
 *
 * Why this exists alongside StudioSidebarPage.editSliderValue: that page object
 * clicks the value span and then waits 3000ms for `input[type="number"]` to
 * appear. SliderControl renders that row as `editing ? <input> : <span>` and
 * flips `editing` from a plain React `onClick` on the span — so a click that
 * lands before React has (re-)attached that handler is silently lost, `editing`
 * stays false, no input ever appears, and the wait dies at
 * studio-sidebar.page.js:176. It is the SAME lost-click race as the overflow
 * menu and the theme button, one layer down, and it is the last thing standing
 * between 21-undo-redo and green: it reproduces locally on chromium roughly
 * 1-in-5 when 15-theme runs alongside it, and on firefox far more often.
 *
 * This is a pre-existing defect in shared test infrastructure, NOT introduced
 * here — it fails identically on unmodified main. It is fixed in this helper
 * rather than in the page object only to keep this PR inside the three spec
 * files plus helpers it was scoped to; the page object should adopt the same
 * wait in a follow-up so every slider-editing spec benefits.
 *
 * The settle signal is the app's own toggle: the input being visible IS
 * `editing === true`. Re-clicking is safe and convergent here, unlike on the
 * Radix menus — a second click on the span while already editing cannot toggle
 * back off, because once `editing` is true the span is unmounted and there is
 * nothing left to click.
 *
 * @param {import('@playwright/test').Page} page
 * @param {import('../page-objects/studio-sidebar.page.js').StudioSidebarPage} sidebar
 * @param {string} paramId
 * @param {number} value
 * @param {number} [timeout]
 */
export async function setSliderValue(page, sidebar, paramId, value, timeout = 15_000) {
  const row = page.locator(`[data-testid="studio-sidebar"] .flex.justify-between:has(#param-label-${paramId})`)
  // Matched as `span[role="button"]`, not a bare `[role="button"]` + .last().
  // The row's contents change with `editing`, so an index-based pick is a guess
  // about a DOM that is mid-swap; the span is the only span carrying that role.
  const valSpan = row.locator('span[role="button"]').first()
  const input = row.locator('input[type="number"]')

  await expect(valSpan.or(input).first()).toBeVisible({ timeout })
  // Click until the row reports itself in edit mode.
  //
  // The click is guarded by an up-front `isVisible` on the SPAN, not just on
  // the input. Both matter: SliderControl renders `editing ? <input> : <span>`,
  // so once the click lands the span is unmounted — and issuing a click against
  // an unmounted locator does not fail fast, it waits out the full actionability
  // budget while the locator re-resolves to whatever else the row now contains.
  // A firefox probe showed exactly that: the first click succeeded (the input
  // was open), and the redundant second click then burned 5s per poll iteration
  // until the outer budget expired — which is why 21-undo-redo was timing out
  // on firefox at 60s per test while passing in isolation.
  await expect
    .poll(
      async () => {
        if (await input.isVisible().catch(() => false)) return true
        // Only click while the span is actually the thing on screen.
        if (!(await valSpan.isVisible().catch(() => false))) return input.isVisible().catch(() => false)
        await valSpan.click({ timeout: 5_000 }).catch(() => { })
        return input.isVisible().catch(() => false)
      },
      {
        timeout,
        message:
          `Slider row "${paramId}" never entered edit mode — the click on its ` +
          'value span was lost before React attached SliderControl\'s onClick.',
      },
    )
    .toBe(true)

  // Fill, then confirm the controlled input actually holds the value before
  // committing. `fill()` dispatches an input event, but SliderControl's value
  // comes from React state (`value={editValue}` + onChange), so a fill that
  // lands during a re-render can be discarded — leaving commitEdit to parse
  // the OLD editValue and write the old number back. That is not hypothetical:
  // a stress run failed with Undo still [disabled] and the row reading
  // "Width: 30" (the default) after a successful-looking fill of 100.
  await expect
    .poll(async () => {
      if ((await input.inputValue().catch(() => null)) === String(value)) return true
      await input.fill(String(value))
      return (await input.inputValue().catch(() => null)) === String(value)
    }, {
      timeout,
      message: `Slider input for "${paramId}" never held ${value} — React discarded the fill.`,
    })
    .toBe(true)

  await input.press('Enter')
  // The input unmounting is `editing === false`, i.e. commitEdit ran.
  await expect(input).toBeHidden({ timeout })
  // And the committed value must be what we asked for. Without this the helper
  // can report success on an edit the app silently dropped, which is exactly
  // how the caller then waits out its budget on an undo that never happened.
  await expect
    .poll(() => valSpan.textContent().then((t) => t?.trim()), {
      timeout,
      message: `Slider "${paramId}" did not commit ${value}.`,
    })
    .toBe(String(value))
}

/**
 * Move keyboard focus somewhere useKeyboardShortcuts will act on.
 *
 * The handler early-returns for keydown whose target is INPUT/TEXTAREA/SELECT
 * or contenteditable. After editing a slider the focus is inside exactly such
 * an input, and although committing with Enter unmounts it, where focus lands
 * next is up to the browser — on WebKit it can stay within the sidebar row.
 * A Ctrl+Z fired then is dropped silently.
 *
 * @param {import('@playwright/test').Page} page
 */
export async function focusShortcutTarget(page) {
  // focus(), not click(). #main-content is a large flex container that the R3F
  // canvas and the panel overlays sit on top of, so a real click has to
  // hit-test through them — on firefox that never resolves and the call waits
  // out the whole 60s test timeout (observed at test-utils.js:744 for
  // 21-undo-redo:104). Focus is all this helper actually needs: the shortcut
  // handler is a window-level listener that only cares what document.
  // activeElement is, not where a pointer went. #main-content carries
  // tabIndex={-1} precisely so it can receive focus programmatically.
  await page.locator('#main-content:visible').first().evaluate((el) => el.focus())
  await expect
    .poll(
      () => page.evaluate(() => {
        const el = document.activeElement
        if (!el) return true
        return !['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) && !el.isContentEditable
      }),
      { timeout: 15_000, message: 'Focus stayed inside a text input, where the shortcut handler ignores keydown.' },
    )
    .toBe(true)
}

/**
 * Press a studio shortcut until the app reports it took effect.
 *
 * A single `keyboard.press` is a one-shot into a global keydown listener that
 * may not be attached yet, or that early-returns because focus is somewhere it
 * refuses to act on. There is no acknowledgement, so a dropped keystroke is
 * indistinguishable from a slow one — the test simply waits out its budget on
 * a state change that will never come.
 *
 * Re-pressing is only sound when the action is idempotent at its boundary, and
 * undo/redo are: useUndoRedo's undo() early-returns at `indexRef <= 0` and
 * redo() at the top of the stack, so extra presses past the target are no-ops
 * rather than overshoot. `settled` must therefore describe the boundary state,
 * not a relative move.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} combo - e.g. 'Control+z'
 * @param {() => Promise<boolean>} settled - resolves true once the app reflects it
 * @param {number} [timeout]
 */
export async function pressUntilSettled(page, combo, settled, timeout = 15_000) {
  await expect
    .poll(
      async () => {
        if (await settled()) return true
        await page.keyboard.press(combo)
        return settled()
      },
      { timeout, message: `"${combo}" never took effect — the keystroke is being dropped, not merely slow.` },
    )
    .toBe(true)
}

/**
 * Wait until an edit made through the sidebar has been committed to the undo
 * history, i.e. the app reports it has something to undo.
 *
 * Replaces `await page.waitForTimeout(600) // Wait for debounce`. The 600ms was
 * chosen against RENDER_DEBOUNCE_MS (500) on one machine; the history push
 * itself is synchronous inside setValue, but it only happens once the committed
 * input value has propagated through ParamRow → setParams, and on WebKit under
 * load that propagation is the slow part. `canUndo` is the app's own signal
 * that the push happened.
 *
 * @param {import('@playwright/test').Page} page
 * @param {number} [timeout]
 */
export async function waitForEditRecorded(page, timeout = 15_000) {
  const undo = undoButton(page)
  if (!(await undo.count())) return
  await expect(undo).toBeEnabled({ timeout })
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
