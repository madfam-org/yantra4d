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
 * Navigate to a real project and wait for manifest + UI to load.
 */
export async function goToRealProject(page, slug, expectedName) {
  await page.goto(`/project/${slug}`)
  await page.waitForSelector('header', { timeout: 15_000 })
  await page.locator('header h1', { hasText: expectedName })
    .waitFor({ timeout: 15_000 })
    .catch(() => {})

  // Wait for URL to settle to /project/{slug}/{preset}/{mode}
  await page.waitForURL(/\/project\/[^/]+\/[^/]+\/[^/]+/, { timeout: 10_000 })
    .catch(() => {})

  // Wait for first mode tab to be visible
  await page.locator('[role="tab"]').first()
    .waitFor({ state: 'visible', timeout: 10_000 })
    .catch(() => {})

  // Let React state settle with real (larger) manifests
  await page.waitForTimeout(1000)
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
  const dialog = page.locator('[role="alertdialog"]')
  const renderAnywayBtn = page.locator('[role="alertdialog"] button', { hasText: /Render Anyway/i })

  // If dialog is already showing (from mode switch), click Render Anyway
  if (await dialog.isVisible({ timeout: 10000 }).catch(() => false)) {
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
 *
 * Call after an explicit Generate that may estimate over the project's
 * threshold. A mode switch or a slider edit will not put this dialog up any
 * more — those render automatically, and an automatic render over the threshold
 * is skipped with a non-blocking toast rather than confirmed — so after one of
 * those this is a no-op that costs the 5s wait below.
 */
export async function dismissRenderWarning(page, action = 'cancel') {
  const dialog = page.locator('[role="alertdialog"]')
  const appeared = await dialog.waitFor({ state: 'visible', timeout: 5000 })
    .then(() => true).catch(() => false)
  if (!appeared) return
  const btnText = action === 'render'
    ? /Render Anyway/i
    : /Cancel|Cancelar/
  await page.locator('[role="alertdialog"] button', { hasText: btnText }).click()
  await dialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
}

/**
 * Change a slider value and wait for the subsequent render to complete.
 */
export async function triggerAndWaitRender(sidebar, page, paramId, value, timeout = 120_000) {
  await sidebar.editSliderValue(paramId, value)
  await waitForRenderDone(page, timeout)
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
