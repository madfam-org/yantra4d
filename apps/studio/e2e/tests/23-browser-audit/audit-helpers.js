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
 * The backend's own view of the render worker: "heartbeat age Ns; queue depth N;
 * active jobs N" (apps/api/routes/core/health.py::_check_render_worker).
 *
 * `ctx` is any APIRequestContext — the `request` fixture in a hook, or
 * `page.request` where only a page is in scope.
 */
export async function renderWorkerDetail(ctx) {
  try {
    const res = await ctx.get(`${BACKEND_URL}/api/health`, { timeout: 5000 })
    if (!res.ok()) return `/api/health answered ${res.status()}`
    const body = await res.json()
    const worker = body?.checks?.render_worker
    if (!worker) return 'no render_worker check in /api/health'
    return `${worker.ok ? 'ok' : 'NOT ok'} — ${worker.detail}`
  } catch (err) {
    return `unreadable (${err.message})`
  }
}

/** Last resort when the API refuses the blanket cancel: talk to the harness's own Redis. */
async function drainViaRedisCli() {
  const { execFile } = await import('node:child_process')
  const { promisify } = await import('node:util')
  const run = promisify(execFile)
  // The two keys render_orchestrator.py names: the queue itself, and the global
  // cancel flag the worker checks for work already in flight.
  const commands = [
    ['DEL', 'yantra_render_queue'],
    ['SET', 'yantra_render_cancel_all', String(Math.floor(Date.now() / 1000)), 'EX', '300'],
  ]
  const results = []
  for (const args of commands) {
    try {
      const { stdout } = await run('redis-cli', args, { timeout: 5000 })
      results.push(`${args[0]} ${args[1]} -> ${stdout.trim()}`)
    } catch (err) {
      results.push(`${args[0]} ${args[1]} -> ${err.message.split('\n')[0]}`)
    }
  }
  return results.join('; ')
}

/**
 * Cancel every queued and in-flight render, and say what was drained.
 *
 * One harness worker serves the whole suite, and nothing else ever empties its
 * queue: the Studio does not cancel its in-flight render when the page is
 * navigated away or closed, so every test that leaves mid-render abandons work
 * that the worker still has to chew through. Run #171 had ZERO cancel calls in
 * 40 minutes, and custom-msh's failing assembly test — which renders every part,
 * re-run three times by serial-mode retries — left enough behind that
 * gridfinity's "renders bin with default params" timed out at 180 s four render
 * requests deep without ever reaching the front of the queue. It is a queueing
 * failure that reads as a render failure.
 *
 * Called per spec file in afterAll, and in afterEach after a test that failed,
 * so one bad group cannot starve the next.
 *
 * Since #83 `POST /api/render-cancel` cancels only what it is handed: a body
 * of `{ all: true }` is the one form that still reaches `cancel_all_renders()`,
 * behind `require_role("admin")` — which passes every caller through while
 * AUTH_ENABLED is off, the state this harness runs in. An empty body is a 400
 * (`cancel_target_required`) and drains nothing, which is how run #96's drain
 * silently stopped working. Should the harness ever run with auth on, the
 * 401/403 falls through to redis-cli rather than leaving the queue full; any
 * other status is logged as-is so a wrong body shape is visible in the run log.
 */
export async function drainRenderQueue(ctx, reason = '') {
  const before = await renderWorkerDetail(ctx)
  let how = 'POST /api/render-cancel'
  let outcome
  try {
    const res = await ctx.post(`${BACKEND_URL}/api/render-cancel`, { data: { all: true }, timeout: 10_000 })
    if (res.ok()) {
      outcome = JSON.stringify(await res.json().catch(() => ({})))
    } else if (res.status() === 401 || res.status() === 403) {
      how = `POST /api/render-cancel refused ${res.status()}, redis-cli`
      outcome = await drainViaRedisCli()
    } else {
      outcome = `HTTP ${res.status()}`
    }
  } catch (err) {
    outcome = `failed (${err.message})`
  }
  const after = await renderWorkerDetail(ctx)
   
  console.log(
    `[audit] render queue drained${reason ? ` after ${reason}` : ''} via ${how}: ${outcome}\n` +
    `        worker before: ${before}\n` +
    `        worker after:  ${after}`,
  )
  return { before, after }
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
 * Fail immediately, and by name, if the studio has opened its upgrade prompt.
 *
 * The upsell is a second [role="alertdialog"], raised by
 * hooks/render/useRender.ts when a render comes back tier-refused. It is NOT
 * auto-cancelled: its Cancel button reads "Maybe Later", which
 * autoCancelRenderWarning() deliberately does not match, because clicking it
 * away would hide a real entitlement gate and let render tests pass having
 * rendered nothing.
 *
 * What it costs when unhandled is the problem: run #168 spent 180 s per attempt
 * waiting for a "Render Anyway" button inside the wrong dialog, and reported a
 * bare timeout. This turns that into one line naming the cause.
 *
 * Matched on the checkout/pricing links rather than on any string, so it holds
 * in either locale and survives copy changes.
 */
export async function assertNoUpgradePrompt(page, context = 'render') {
  const upsell = page
    .locator('[role="alertdialog"]')
    .filter({ has: page.locator('a[href*="pricing"], a[href*="checkout"]') })
  if (!(await upsell.isVisible().catch(() => false))) return
  const shown = ((await upsell.textContent().catch(() => '')) || '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 240)
  throw new Error(
    `Tier gate hit during ${context}: the studio opened its upgrade prompt instead of rendering. ` +
    'The audit backend must run as a tier allowed to use this project\'s engine — the nightly ' +
    'sets HARNESS_TIER (docs/AUTH.md, "Harness tier"); gridfinity\'s default `bin` mode is ' +
    `CadQuery, which the guest tier may not use. Dialog said: "${shown}"`,
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
 * Fail immediately, and by name, if the studio is showing its manifest error
 * screen instead of the project.
 *
 * App.tsx replaces the ENTIRE app with that screen when the manifest fetch
 * fails — no header, no sidebar, no tabs — so every later assertion fails on an
 * absence and reports a count of zero rather than the reason. Run #170 lost an
 * attempt of "loads gridfinity and shows manifest data" to exactly that: the
 * page was "📡 Can't Reach the Server", and the test said only that it wanted
 * five mode tabs and found none.
 *
 * Detected by the absence of the studio's <header>, which the error screen does
 * not render — locale-free, and true for all three variants (unreachable, not
 * found, locked).
 */
export async function assertStudioLoaded(page, slug = '') {
  // The studio always has a <header>; the error screen replaces the whole app
  // and has none. Checked that way round rather than by matching its copy, so
  // it holds in every locale and for all three variants (unreachable, not
  // found, locked). goToRealProject has already waited for the header once by
  // the time this runs, so its absence now means the app tore it down.
  if (await page.locator('header').first().isVisible().catch(() => false)) return
  const heading = (await page.locator('h1').first().textContent().catch(() => '')) || ''
  if (!heading.trim()) return
  const body = (await page.locator('p').first().textContent().catch(() => '')) || ''
  throw new Error(
    `The studio never loaded${slug ? ` "${slug}"` : ''}: it replaced the app with its ` +
    `manifest error screen — "${heading.trim()}" / "${body.trim().slice(0, 200)}". ` +
    'This is the app, not the harness: check the backend log for the manifest ' +
    'request it made. A slug-less GET /api/manifest is a 400 on any multi-project ' +
    'backend, and ManifestProvider falls back to it whenever the projects-list ' +
    'fetch is aborted by its 2 s timeout.',
  )
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

  // Wait for the first VISIBLE mode tab. #81 made App.tsx mount only the tree
  // that is on screen, so this is usually the only tab there is; the filter
  // stays because it is what makes the wait honest — an unfiltered .first()
  // waited out its whole 10 s on any tab that is present but not shown.
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
  // nor an assertion, so nothing there ever triggers a locator handler.
  //
  // Since #82 a load-time automatic render is skipped with a toast and opens no
  // dialog at all, so this finds nothing and is purely a safety net for a build
  // or cartridge where one still appears — hence the short budget: it is paid
  // in full on every navigation in the suite...
  await dismissRenderWarning(page, 'cancel', 1000)

  // By now the manifest request has resolved one way or the other, so a failure
  // is reportable as itself rather than as whatever is missing downstream.
  await assertStudioLoaded(page, slug)

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
    // A tier-refused render never re-enables Generate on its own terms; say so
    // now rather than after the full timeout.
    await assertNoUpgradePrompt(page, 'waitForRenderDone')
    const visible = await generateBtn.isVisible().catch(() => false)
    if (visible) {
      const disabled = await generateBtn.isDisabled().catch(() => true)
      if (!disabled) return
    }
    await page.waitForTimeout(500)
  }
  // Say WHICH kind of not-finishing this was. One worker serves the whole suite
  // and abandoned renders are never cancelled, so the likeliest reason a render
  // does not finish is that it never started — it is still behind someone else's
  // work. Run #171 reported this as "Render did not complete", which reads as a
  // broken renderer; the queue depth says starvation.
  const worker = await renderWorkerDetail(page.request)
  throw new Error(
    `Render did not complete within ${timeout}ms. Render worker at timeout: ${worker}. ` +
    'A non-zero queue depth here means this render was still waiting its turn — ' +
    'check whether an earlier group left work behind (drainRenderQueue runs in ' +
    'afterAll and after a failed test) rather than assuming the renderer is broken.',
  )
}

/**
 * Dismiss the "Long Render Warning" dialog if present, then click Generate.
 *
 * A mode switch no longer raises the dialog: the render it schedules is the
 * debounced automatic one, which is now skipped with a toast instead of
 * confirmed with a modal. Only a render the user asked for opens the dialog, so
 * the "already showing" branch below covers a dialog left up by an earlier
 * explicit Generate in the same test, and the later branch covers the one this
 * function's own click raises. Both stay conditional — a project under the
 * threshold raises neither.
 */
export async function clickGenerateWithWarning(sidebar, page) {
  // User-initiated Generate: the modal is expected here, so take the
  // auto-cancel handler off before anything is clicked. It stays off for the
  // rest of the test (a later goToRealProject re-arms it).
  const dialog = await expectRenderWarning(page)
  const renderAnywayBtn = page.locator('[role="alertdialog"] button', { hasText: /Render Anyway/i })

  // The upsell is an alertdialog too, so check before treating one as the
  // render warning — otherwise this waits out its whole budget looking for a
  // "Render Anyway" button that is not in that dialog (run #168).
  await assertNoUpgradePrompt(page, 'clickGenerateWithWarning')

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
  await assertNoUpgradePrompt(page, 'clickGenerateWithWarning')

  // Handle dialog if Generate triggered it
  if (await dialog.isVisible({ timeout: 2000 }).catch(() => false)) {
    await renderAnywayBtn.click()
    await dialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
  }
}

/**
 * Dismiss the Long Render Warning dialog if it appears.
 *
 * Call after an explicit Generate that may estimate over the project's
 * threshold. A mode switch or a slider edit will not put this dialog up any
 * more — those render automatically, and an automatic render over the threshold
 * is skipped with a non-blocking toast rather than confirmed (#82) — so after
 * one of those this is a no-op that costs the wait below.
 *
 * It is still worth calling where an older cartridge or an unmerged build could
 * raise one: the dialog is modal, so anything clicked while it is up blocks for
 * its whole actionability budget. That is also why autoCancelRenderWarning()
 * exists, and why the click below tolerates failure.
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
  // The console on screen. Absent (or collapsed) it reads null, and the
  // Generate-disabled evidence stands alone.
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
