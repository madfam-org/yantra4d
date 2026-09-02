/**
 * Shared helpers for the browser audit E2E suite.
 * Designed for real Docker backend (not mocked APIs).
 */

const BACKEND_URL = 'http://localhost:5000'

// Public commons cartridges — present in every checkout of this repo.
export const PUBLIC_AUDIT_SLUGS = ['gridfinity', 'custom-msh']
// Client-private cartridges: `update = none` submodules (#48, #52). Absent from a
// default checkout; present only when the nightly is dispatched with
// `include_private_projects`, or locally with the submodule initialised.
export const PRIVATE_AUDIT_SLUGS = ['tablaco']

// Populated by skipIfNoBackend from the backend's live project list.
let availableSlugs = null

/** True when the running backend serves this project. */
export function hasProject(slug) {
  return availableSlugs?.has(slug) ?? false
}

function missingReason(slug) {
  return PRIVATE_AUDIT_SLUGS.includes(slug)
    ? `Project "${slug}" is a client-private cartridge (update = none) and is not in this checkout — dispatch the nightly with include_private_projects to audit it`
    : `Project "${slug}" not found in backend`
}

/**
 * Skip a single test unless the backend serves `slug`. Use inside a test body
 * for the private cartridges, so a public-only checkout reports them as
 * SKIPPED with the reason instead of failing on a 404.
 */
export function skipUnlessProject(test, slug) {
  test.skip(!hasProject(slug), missingReason(slug))
}

/**
 * Skip the whole group if the real backend is not running, OpenSCAD is
 * unavailable, or any of `requiredSlugs` is not served. Records the served
 * project list for hasProject()/skipUnlessProject(). Groups that only need the
 * public cartridges take the default, so the private ones being absent no
 * longer skips the entire audit.
 */
export async function skipIfNoBackend(request, test, requiredSlugs = PUBLIC_AUDIT_SLUGS) {
  try {
    const health = await request.get(`${BACKEND_URL}/api/health`, { timeout: 5000 })
    if (!health.ok()) {
      test.skip('Real backend not reachable on :5000')
      return
    }
    const body = await health.json()
    if (!body.checks?.openscad?.ok) {
      test.skip('OpenSCAD not available in the real backend')
      return
    }

    const projects = await request.get(`${BACKEND_URL}/api/projects`, { timeout: 5000 })
    if (!projects.ok()) {
      test.skip('Cannot fetch project list from backend')
      return
    }
    const projectList = await projects.json()
    const slugs = (projectList.projects || projectList).map(p => p.slug || p.project?.slug)
    availableSlugs = new Set(slugs)
    for (const slug of requiredSlugs) {
      if (!availableSlugs.has(slug)) {
        test.skip(missingReason(slug))
        return
      }
    }
  } catch {
    test.skip('Real backend not running on :5000')
  }
}

/**
 * Fetch a real project's manifest from the backend.
 *
 * Lets a test ask the cartridge what it actually declares instead of assuming.
 * Returns null when the project or the endpoint is not available.
 */
export async function fetchManifest(request, slug) {
  try {
    const res = await request.get(`${BACKEND_URL}/api/projects/${slug}/manifest`, { timeout: 10_000 })
    if (!res.ok()) return null
    return await res.json()
  } catch {
    return null
  }
}

/**
 * Pages currently carrying the auto-cancel handler below, mapped to the exact
 * locator it was registered with — page.removeLocatorHandler() wants that same
 * locator back. A WeakMap so it is dropped with the page; the `page` fixture is
 * per-test, so no registration ever outlives the test that made it.
 */
const renderWarningHandled = new WeakMap()

/**
 * Cancel the Long Render Warning automatically, before every later action.
 *
 * One-shot dismissals were whack-a-mole. The studio re-arms its debounced
 * auto-generate on every param/preset settle and every mode switch, so the
 * modal comes BACK after a single cancel: run #167 still lost four tests to a
 * 180 s `locator.click` timeout with the dialog present in all twelve failure
 * snapshots — the post-load settle in cross-cutting, `selectMode()` in
 * gridfinity and custom-msh, the sheet trigger in responsive. Radix renders the
 * dialog over a pointer-event-blocking overlay, so any click issued while it is
 * up waits out its entire actionability budget.
 *
 * page.addLocatorHandler() moves this from "remember to dismiss" to "cannot be
 * hit": Playwright re-checks the locator before every action on the page and
 * runs this first. Registered once per page, uncapped (no `times`), and
 * `noWaitAfter` because the handler already waits for the dialog to go.
 *
 * Only AUTOMATIC renders are swallowed here. A test that wants the modal —
 * anything user-initiated — calls expectRenderWarning() to take the handler off
 * first.
 */
export async function autoCancelRenderWarning(page) {
  if (renderWarningHandled.has(page)) return
  const dialog = page.locator('[role="alertdialog"]')
  renderWarningHandled.set(page, dialog)
  await page.addLocatorHandler(
    dialog,
    async (warning) => {
      await warning
        .getByRole('button', { name: /^(Cancel|Cancelar)$/ })
        .click({ timeout: 5000 })
        .catch(() => {})
      await dialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
    },
    { noWaitAfter: true },
  )
}

/**
 * Stop auto-cancelling the Long Render Warning and hand back its locator, for a
 * test that needs to SEE the dialog — a user-initiated Generate still raises it
 * (that stays true after the quiet-autogenerate change, which only silences the
 * automatic path). Without this the handler would cancel the very dialog the
 * caller is about to confirm, and the "Render Anyway" click would land on a
 * detached button.
 *
 * The handler stays off for the rest of the test — simpler than re-arming
 * around each Generate, and safe because the `page` fixture is per-test. A
 * later goToRealProject() in the same test re-registers it, since this also
 * clears the registry entry.
 */
export async function expectRenderWarning(page) {
  const registered = renderWarningHandled.get(page)
  if (registered) {
    await page.removeLocatorHandler(registered)
    renderWarningHandled.delete(page)
  }
  return page.locator('[role="alertdialog"]')
}

/**
 * Navigate to a real project and wait for manifest + UI to load.
 */
export async function goToRealProject(page, slug, expectedName) {
  await page.goto(`/project/${slug}`)
  await page.waitForSelector('header', { timeout: 15_000 })
  await page.locator('header h1', { hasText: expectedName })
    .waitFor({ timeout: 15_000 })
    .catch(() => {})

  // Wait for the URL to settle on the canonical path. buildHash()
  // (hooks/system/useHashNavigation.ts) writes /project/{slug}/{mode}/{preset}
  // — MODE first, and the preset segment only once one is active — so the old
  // three-segment pattern here was both in the wrong order and unsatisfiable on
  // a cartridge with no preset. Match the mode segment and stop there.
  await page.waitForURL(/\/project\/[^/]+\/[^/]+/, { timeout: 10_000 })
    .catch(() => {})

  // Wait for the first VISIBLE mode tab. App.tsx renders its desktop and mobile
  // trees at the same time (`hidden lg:flex` / `lg:hidden`), so `[role="tab"]`
  // .first() is a tab in whichever tree is display:none at this viewport and
  // never becomes visible — 10 s burned on every mobile navigation.
  await page.locator('[role="tab"]').filter({ visible: true }).first()
    .waitFor({ state: 'visible', timeout: 10_000 })
    .catch(() => {})

  // Let React state settle with real (larger) manifests
  await page.waitForTimeout(1000)

  // The studio auto-generates on load (debounced effect in
  // hooks/project/useProjectParams.ts) and pops the modal Long Render Warning
  // whenever the estimate exceeds the cartridge's warning threshold. That is
  // now the normal path for gridfinity, whose cadquery `bin` default estimates
  // ~2 minutes. Radix renders the alert dialog over a pointer-event-blocking
  // overlay, so every later click waits out its full actionability budget
  // instead of landing — in run #166 header.toggleLanguage() timed out at 180 s
  // on all three attempts with the dialog sitting in the page snapshot. Cancel
  // the one already up, so the page is clean immediately — including for the
  // axe audits, which reach the page through page.evaluate: neither an action
  // nor an assertion, so nothing there ever triggers a locator handler...
  await dismissRenderWarning(page, 'cancel', 2500)

  // ...and arm the handler for every one that comes after: the settle, a mode
  // switch and a preset each re-arm the auto-generate, so a single cancel here
  // is not enough (run #167). Registered AFTER the one-shot above, never
  // before — with the handler live, dismissRenderWarning's own click on Cancel
  // would race the handler for the same button.
  await autoCancelRenderWarning(page)
}

/**
 * Wait for a render to complete (Generate button disables then re-enables).
 */
export async function waitForRenderComplete(page, timeout = 120_000) {
  const generateBtn = page.locator('button', { hasText: /Generate|Generar/ }).first()

  // Wait for render to start (button becomes disabled)
  await generateBtn.waitFor({ state: 'visible', timeout: 10_000 })
  await page.waitForFunction(
    btn => btn?.disabled === true,
    await generateBtn.elementHandle().catch(() => null),
    { timeout: 5000 }
  ).catch(() => {})

  // Wait for render to finish (button re-enables)
  await expect_poll(() => generateBtn.isDisabled(), { timeout })
    .toBe(false)
}

/**
 * Poll-based expect helper (avoids importing expect at module level).
 * Use waitForRenderDone instead for simpler API.
 */
async function expect_poll(fn, { timeout = 120_000 } = {}) {
  const start = Date.now()
  let last
  while (Date.now() - start < timeout) {
    last = await fn()
    if (last === false) return { toBe: (v) => { if (last !== v) throw new Error(`Expected ${v}, got ${last}`) } }
    await new Promise(r => setTimeout(r, 500))
  }
  return { toBe: (v) => { if (last !== v) throw new Error(`Render did not complete within ${timeout}ms`) } }
}

/**
 * Simpler render wait: just poll until Generate button is enabled.
 */
export async function waitForRenderDone(page, timeout = 120_000) {
  const generateBtn = page.locator('button', { hasText: /Generate|Generar/ }).first()

  // Wait for Generate button to appear — may take the full render duration
  // if a render was already started (e.g. via "Render Anyway" dialog)
  await generateBtn.waitFor({ state: 'visible', timeout }).catch(() => {})

  // Wait briefly for render to start (in case button was visible but render hasn't begun)
  await page.waitForTimeout(2000)

  // Poll until button is visible and enabled (render complete)
  const start = Date.now()
  while (Date.now() - start < timeout) {
    const visible = await generateBtn.isVisible().catch(() => false)
    if (visible) {
      const disabled = await generateBtn.isDisabled().catch(() => true)
      if (!disabled) return
    }
    await page.waitForTimeout(500)
  }
  throw new Error(`Render did not complete within ${timeout}ms`)
}

/**
 * Dismiss the "Long Render Warning" dialog if present, then click Generate.
 * Handles cases where switching modes auto-triggers the warning.
 */
export async function clickGenerateWithWarning(sidebar, page) {
  // User-initiated Generate: the modal is expected here, so take the
  // auto-cancel handler off before anything is clicked. It stays off for the
  // rest of the test (a later goToRealProject re-arms it).
  const dialog = await expectRenderWarning(page)
  const renderAnywayBtn = page.locator('[role="alertdialog"] button', { hasText: /Render Anyway/i })

  // If dialog is already showing (from a mode switch, or from the load-time
  // auto-generate goToRealProject did not get to), click Render Anyway. Short
  // budget: on the common path there is no dialog yet and every second here is
  // spent once per render test.
  if (await dialog.isVisible({ timeout: 2000 }).catch(() => false)) {
    await renderAnywayBtn.click()
    await dialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
    return
  }

  // Try clicking Generate — if the dialog overlay appears mid-click, catch and handle
  try {
    await sidebar.generateButton.click({ timeout: 5000 })
  } catch {
    // Dialog likely appeared during click attempt — dismiss it
    if (await dialog.isVisible({ timeout: 10000 }).catch(() => false)) {
      await renderAnywayBtn.click()
      await dialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
      return
    }
  }

  await page.waitForTimeout(500)

  // Handle dialog if Generate triggered it
  if (await dialog.isVisible({ timeout: 2000 }).catch(() => false)) {
    await renderAnywayBtn.click()
    await dialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
  }
}

/**
 * Dismiss the Long Render Warning dialog if it appears.
 * Call after mode switches or parameter edits that may trigger a render
 * estimate — the dialog is modal, so anything clicked while it is up blocks.
 */
export async function dismissRenderWarning(page, action = 'cancel', timeout = 5000) {
  const dialog = page.locator('[role="alertdialog"]')
  const appeared = await dialog.waitFor({ state: 'visible', timeout })
    .then(() => true).catch(() => false)
  if (!appeared) return
  const btnText = action === 'render'
    ? /Render Anyway/i
    : /Cancel|Cancelar/
  // Tolerated failure: with autoCancelRenderWarning() armed, the handler can
  // cancel the dialog between the wait above and this click, leaving the button
  // detached. The state that matters is asserted on the next line.
  await page.locator('[role="alertdialog"] button', { hasText: btnText })
    .click({ timeout: 5000 })
    .catch(() => {})
  await dialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
}

/**
 * Change a slider value and wait for the subsequent render to complete.
 *
 * Has to prove a render in two different worlds, because the app's answer to a
 * param change that estimates over `warning_threshold_seconds` is changing:
 *
 *   - today: the debounced auto-generate raises the modal Long Render Warning
 *     and renders nothing until it is answered;
 *   - after the quiet-autogenerate change: an AUTOMATIC render over the
 *     threshold is skipped altogether behind a non-blocking toast, and only a
 *     user-initiated Generate still carries the modal.
 *
 * Either way a short estimate still auto-renders with no dialog at all. So this
 * cannot just dismiss a dialog and wait: answering a dialog that no longer
 * appears, then "waiting" on a Generate button that was never disabled, passes
 * without a render ever happening. Wait for real evidence instead — the dialog,
 * or Generate reporting itself disabled — ask for the render explicitly when
 * the app declined to start one, and fail if no render was ever observed.
 */
export async function triggerAndWaitRender(sidebar, page, paramId, value, timeout = 120_000) {
  // This helper's whole job is to observe the render, so it must be able to see
  // the warning rather than have it cancelled underneath it. Take the handler
  // off first, then clear anything the load left up — in that order, so the
  // cancel below cannot race the handler for the same button — and only then
  // touch the slider.
  const dialog = await expectRenderWarning(page)
  await dismissRenderWarning(page, 'cancel', 500)
  const generateBtn = page.locator('button', { hasText: /Generate|Generar/ }).first()
  // Both layout trees render the console; take the one on screen. Absent (or
  // collapsed) it reads null, and the Generate-disabled evidence stands alone.
  const renderLog = page.locator('[role="log"]').filter({ visible: true }).first()
  const logBefore = await renderLog.textContent().catch(() => null)

  // Poll for a render being in flight — the Generate button disables for the
  // duration. Gives up early if the modal comes up instead, since that means
  // the app is waiting on an answer rather than rendering.
  const renderStarted = async (budgetMs) => {
    const deadline = Date.now() + budgetMs
    while (Date.now() < deadline) {
      if (await generateBtn.isDisabled().catch(() => false)) return true
      if (await dialog.isVisible().catch(() => false)) return false
      await page.waitForTimeout(100)
    }
    return false
  }

  await sidebar.editSliderValue(paramId, value)

  // RENDER_DEBOUNCE_MS is 500 ms (hooks/project/useProjectParams.ts); leave room
  // for the estimate and a React commit on a contended runner.
  let rendering = await renderStarted(2500)

  if (!rendering && await dialog.isVisible().catch(() => false)) {
    // Automatic render, long estimate, current behaviour: confirm it.
    await dismissRenderWarning(page, 'render', 1000)
    rendering = await renderStarted(5000)
  }

  if (!rendering) {
    // Nothing started on its own — the quiet-autogenerate path, or a value the
    // app already had cached. Ask for the render the way a user would; that is
    // still the modal path, which clickGenerateWithWarning confirms.
    await clickGenerateWithWarning(sidebar, page)
    rendering = await renderStarted(5000)
  }

  await waitForRenderDone(page, timeout)

  const logAfter = await renderLog.textContent().catch(() => null)
  if (!rendering && logAfter === logBefore) {
    throw new Error(
      `Setting "${paramId}" to ${value} produced no render: the Generate button was ` +
      'never observed disabled and the render console never changed.',
    )
  }
}

/**
 * Trigger an action and wait for a download event.
 * Returns { download, suggestedFilename, path }.
 */
export async function waitForDownload(page, triggerAction, timeout = 60_000) {
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout }),
    triggerAction(),
  ])
  const path = await download.path()
  const suggestedFilename = download.suggestedFilename()
  return { download, suggestedFilename, path }
}
