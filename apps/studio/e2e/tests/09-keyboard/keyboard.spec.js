import { test, expect } from '../../fixtures/app.fixture.js'
import {
  goToStudio,
  setLanguage,
  isMac,
  forceBackendRender,
  waitForModesReady,
  pressModeShortcut,
  pressUntilSettled,
} from '../../helpers/test-utils.js'

/**
 * Mode ids of the MOCKED manifest (e2e/helpers/api-mocker.js), in the order the
 * Cmd/Ctrl+N shortcut indexes them. Deliberately different from the gridfinity
 * fallback manifest the app boots with, which is what makes the wait necessary.
 */
const MOCK_MODE_IDS = ['cup', 'single', 'grid']

test.describe('Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    // Pin the render path to the mocked server. Without this the browser is the
    // default placement, so the per-test render mocks below are never fetched.
    await forceBackendRender(page)
    await goToStudio(page)
  })

  test('Cmd/Ctrl+Z triggers undo', async ({ page, sidebar }) => {
    const valueBefore = await sidebar.sliderValue('width').textContent()
    await sidebar.editSliderValue('width', 100)
    await expect(sidebar.sliderValue('width')).toHaveText('100', { timeout: 10000 })

    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText(valueBefore, { timeout: 10000 })
  })

  test('Cmd/Ctrl+Shift+Z triggers redo', async ({ page, sidebar }) => {
    // Wait for initial auto-render to settle so it doesn't clear redo stack
    await page.waitForTimeout(1500)

    const valueBefore = await sidebar.sliderValue('width').textContent()
    await sidebar.editSliderValue('width', 100)
    await expect(sidebar.sliderValue('width')).toHaveText('100', { timeout: 10000 })

    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText(valueBefore, { timeout: 10000 })

    // Small delay to avoid keyboard event collision with undo handler
    await page.waitForTimeout(200)
    await page.keyboard.press(mac ? 'Meta+Shift+z' : 'Control+Shift+z')
    await expect(sidebar.sliderValue('width')).toHaveText('100', { timeout: 10000 })
  })

  test('Cmd/Ctrl+Enter triggers render', async ({ page, sidebar }) => {
    // Settle the load-time render before the mock goes in, so the state
    // observed below belongs to the param change this test makes.
    await sidebar.waitForRenderOutput()

    // Hold the render open rather than sleeping 5s in the route handler: the
    // window a fixed sleep leaves open moves with runner load at both ends, and
    // this assertion missing it is how a healthy render reported that
    // Processing never appeared. Held, the app cannot leave the rendering state.
    let releaseRender = () => { }
    const renderHeld = new Promise((resolve) => { releaseRender = resolve })
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await renderHeld
      await route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100,"phase":"Done"}\n\n' })
    })
    await page.unroute('**/api/render')
    await page.route('**/api/render', async (route) => {
      await renderHeld
      await route.abort()
    })

    try {
      // Change a param to bust the render cache, then wait for debounce to clear
      await sidebar.editSliderValue('width', 77)
      // The debounced auto-render fires with the held mock: the app's own state
      // first, then the control it swaps in to say so.
      await sidebar.waitForRenderState('rendering')
      await expect(page.locator('button', { hasText: /Processing|Procesando/ })).toBeVisible({ timeout: 10000 })
    } finally {
      releaseRender()
    }
  })

  test('Escape cancels active render', async ({ page, sidebar }) => {
    // The initial auto-render must be OVER before the held mock goes in, or it
    // lands on the held route itself and Escape then cancels the load-time
    // render rather than this test's. The settle used to run AFTER the swap and
    // could only report "nothing in flight" — equally true in the 500ms
    // debounce window before the load-time render has started. Waiting for that
    // render's output says it both happened and finished.
    await sidebar.waitForRenderOutput()

    // Hold the render open until this test releases it, so the window in which
    // Escape has something to cancel is set by the test rather than by how fast
    // the runner happens to render. The previous version raced twice over: the
    // initial auto-render might still be running when it pressed Escape (so the
    // Cancel it saw belonged to the *un*mocked render), and on a browser
    // placement — the default — the 10s mock below was never consulted at all.
    let releaseRender = () => { }
    const renderHeld = new Promise((resolve) => { releaseRender = resolve })
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await renderHeld
      await route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    try {
      // Change a param to bust render cache — debounced auto-render uses the held mock
      await sidebar.editSliderValue('width', 63)
      // Wait for render to actually start — the app's own state, then the
      // Cancel button, which is what Escape is the keyboard equivalent of.
      await sidebar.waitForRenderState('rendering')
      await expect(sidebar.cancelButton).toBeVisible({ timeout: 15_000 })

      // Press until the app reports itself idle rather than once and hope. The
      // handler is `Escape && loading` on a window listener, so a keystroke
      // that lands a frame before React re-runs the effect with loading=true is
      // dropped silently — indistinguishable, from the outside, from a cancel
      // that is merely slow. Re-pressing cannot overshoot: with nothing
      // loading, Escape does nothing here at all.
      await pressUntilSettled(
        page,
        'Escape',
        async () => (await sidebar.renderState()) === 'idle',
        20_000,
      )
      // Generate button should re-appear — the app aborts the in-flight fetch,
      // so this must not depend on the route ever being released.
      await expect(sidebar.generateButton).toBeVisible({ timeout: 10_000 })
      await expect(sidebar.generateButton).toBeEnabled({ timeout: 10_000 })
    } finally {
      releaseRender()
    }
  })

  // The mode tabs are plain buttons carrying aria-selected; the only tabs with
  // data-state="active" are the Radix section tabs (Design/View/BOM/Export) and
  // the hidden mobile mode list. So [role="tab"][data-state="active"] resolved
  // first to the Design section tab and these assertions compared a mode name
  // against "Design". sidebar.getActiveMode() reads the visible mode tablist.
  test('Cmd/Ctrl+1 switches to first mode', async ({ page, sidebar }) => {
    // waitForModesReady, not a bare keypress: the shortcut handler indexes into
    // whichever manifest is loaded when the key lands, and until the mock
    // manifest arrives that is the gridfinity fallback. This test would pass
    // either way — fallback modes[0] is "bin" and loaded modes[0] is "cup"
    // (label "Start"), so /start|inicio/ matches the loaded one regardless —
    // which made it a false green hiding the same race that fails Cmd/Ctrl+2.
    await pressModeShortcut(page, 1, MOCK_MODE_IDS)
    await expect.poll(() => sidebar.getActiveMode(), { timeout: 15_000 }).toMatch(/start|inicio/i)
  })

  test('Cmd/Ctrl+2 switches to second mode', async ({ page, sidebar }) => {
    // The flake this file was red for. Sending Meta+2 before the mock manifest
    // replaced the fallback dispatched fallback modes[1] = "baseplate", a mode
    // absent from the loaded manifest, so the app stayed on "cup" and
    // getActiveMode() returned "start" until the poll expired. Waiting for the
    // loaded modes to be the ones on screen removes the race at its source.
    await pressModeShortcut(page, 2, MOCK_MODE_IDS)
    await expect.poll(() => sidebar.getActiveMode(), { timeout: 15_000 }).toMatch(/single|individual/i)
  })

  test('Cmd/Ctrl+number beyond mode count does nothing', async ({ page, sidebar }) => {
    // Guard the count too: the fallback manifest has FIVE modes, so a Meta+9
    // here is only genuinely "beyond the mode count" once the 3-mode loaded
    // manifest is in place. Without the wait this asserts nothing on a slow
    // manifest — and would also have stayed green if Meta+9 had switched mode
    // while both reads still resolved to the same tab.
    await waitForModesReady(page, MOCK_MODE_IDS)
    const modeBefore = await sidebar.getActiveMode()
    const mac = await isMac(page)
    await page.keyboard.press(mac ? 'Meta+9' : 'Control+9')
    await page.waitForTimeout(300)
    expect(await sidebar.getActiveMode()).toBe(modeBefore)
  })

  test('keyboard shortcuts work when sidebar is focused', async ({ page, sidebar }) => {
    // Focus the sidebar by clicking the param label (non-interactive, won't change values)
    await page.locator('#param-label-width').click()
    const mac = await isMac(page)
    // Capture value AFTER focus — clicking the slider track could change it
    const valueBefore = await sidebar.sliderValue('width').textContent()
    await sidebar.editSliderValue('width', 100)
    await expect(sidebar.sliderValue('width')).toHaveText('100', { timeout: 10000 })
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText(valueBefore, { timeout: 10000 })
  })

  test('keyboard shortcuts work when viewer is focused', async ({ page, sidebar }) => {
    // Click the viewer area (not canvas directly — it may remount during manifest load).
    // App.tsx renders StudioMainView in both the desktop and the mobile layout
    // tree, so #main-content is in the DOM twice — a duplicate id, and enough to
    // fail strict mode here before any key was pressed. Scope to the visible one.
    await page.locator('#main-content:visible').first().click()
    await page.waitForTimeout(200)
    // Ctrl+3 selects the 3rd mode (Grid) — modes are 1-indexed in shortcuts.
    // Same manifest race as Cmd/Ctrl+2: fallback modes[2] is "cup", so an early
    // keystroke here switches to Start and this asserts /grid/ against "start".
    await pressModeShortcut(page, 3, MOCK_MODE_IDS)
    await expect.poll(() => sidebar.getActiveMode(), { timeout: 15_000 }).toMatch(/grid|cuadr/i)
  })

  test('keyboard shortcuts do not interfere with text inputs', async ({ sidebar }) => {
    // Settle the load-time render first: its completion re-renders the sidebar,
    // and a controlled input re-rendered on top of a change event React never
    // received snaps straight back to the value in state. That is the whole
    // failure — "Received: A" for a successful-looking fill of Z — and it is
    // about a lost change event, not about a shortcut interfering.
    await sidebar.waitForRenderOutput()

    const letterInput = sidebar.textInput('letter')
    if (await letterInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      // fill() atomically focuses, clears, types and dispatches change events —
      // repeated until React acknowledges it, for the reason above.
      // This validates the core concern: keyboard shortcut handler returns early for INPUT elements
      await sidebar.fillTextInput('letter', 'Z')
      await expect(letterInput).toHaveValue('Z', { timeout: 10000 })
    }
  })

  test('multiple undos walk back through history', async ({ page, sidebar }) => {
    const initialVal = await sidebar.sliderValue('width').textContent()
    await sidebar.editSliderValue('width', 80)
    await expect(sidebar.sliderValue('width')).toHaveText('80', { timeout: 10000 })
    await sidebar.editSliderValue('width', 120)
    await expect(sidebar.sliderValue('width')).toHaveText('120', { timeout: 10000 })

    const mac = await isMac(page)
    // Undo to 80
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText('80', { timeout: 10000 })

    // Undo to initial
    await page.keyboard.press(mac ? 'Meta+z' : 'Control+z')
    await expect(sidebar.sliderValue('width')).toHaveText(initialVal, { timeout: 10000 })
  })
})
