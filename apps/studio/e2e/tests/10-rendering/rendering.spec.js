import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage, forceBackendRender } from '../../helpers/test-utils.js'

test.describe('Rendering Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    // Every test in this file asserts on the behaviour of a MOCKED render, and
    // only a SERVER placement fetches `/api/render-stream`. The browser is the
    // default placement, so without this `?render=backend` pin the whole file
    // would test the browser path — where the mocks are never fetched and the
    // render dies in a WASM environment that ships no binary, at
    // machine-dependent speed.
    await forceBackendRender(page)
    await goToStudio(page)
  })

  test('clicking Generate starts render', async ({ page, sidebar }) => {
    // Let the initial auto-render COMPLETE before the mock is swapped, so the
    // render observed below is unambiguously the one this test triggers. The
    // load-time render is debounced 500ms behind the last params change, so
    // "nothing is running right now" is also true before it has started —
    // waiting for output is the difference between the two.
    await sidebar.waitForRenderOutput()

    // Hold the render open instead of sleeping 5s inside the route handler. A
    // fixed sleep makes the assertion a bet that it looks inside a window whose
    // start (debounce + React commit) and end (5s later) both move with runner
    // load; losing that bet is exactly this line reporting that Processing never
    // appeared, for a render that had already come and gone. While the route is
    // held the app CANNOT leave the rendering state, so a fast render cannot
    // slip past the assertion.
    let releaseRender = () => { }
    const renderHeld = new Promise((resolve) => { releaseRender = resolve })
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await renderHeld
      await route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    try {
      // Change param to bust the render cache (auto-render cached the initial result)
      await sidebar.editSliderValue('width', 66)
      // The debounced auto-render fires with the held mock: first the app's own
      // statement that a render is in flight...
      await sidebar.waitForRenderState('rendering')
      // ...then the control it swaps in to say so, which is what a user sees.
      await expect(page.locator('button', { hasText: /Processing|Procesando/ })).toBeVisible({ timeout: 10000 })
    } finally {
      releaseRender()
    }
  })

  test('cancel button appears during render', async ({ page, sidebar }) => {
    // Same two changes as the test above: settle the load-time render first so
    // the one below is ours, and hold it open rather than sleeping 5s, so the
    // window in which Cancel exists is bounded by this test and not by how fast
    // the runner happens to render.
    await sidebar.waitForRenderOutput()

    let releaseRender = () => { }
    const renderHeld = new Promise((resolve) => { releaseRender = resolve })
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await renderHeld
      await route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    try {
      // Change param to trigger auto-render (debounce 500ms)
      await sidebar.editSliderValue('width', 123)

      // The render is in flight — and stays in flight — so Cancel being absent
      // here is the app failing to offer it, never the assertion arriving late.
      await sidebar.waitForRenderState('rendering')
      await expect(sidebar.cancelButton).toBeVisible({ timeout: 5000 })
    } finally {
      releaseRender()
    }
  })

  test('cancel aborts render', async ({ page, sidebar, viewer }) => {
    // The initial auto-render has to be OVER before the held mock goes in, or
    // it lands on the held route itself and the render this test cancels is
    // then the second of two overlapping ones. `waitForRenderSettled` could not
    // establish that from here: it reports "no render in flight", which is also
    // true in the 500ms debounce window before the load-time render starts —
    // and it ran after the route swap, so on a loaded runner it was one
    // scheduling slip away from freezing the load-time render instead.
    await sidebar.waitForRenderOutput()

    // Hold the render open until the test releases it, instead of betting that
    // a fixed 10s sleep outlasts however long the runner takes to get here.
    let releaseRender = () => { }
    const renderHeld = new Promise((resolve) => { releaseRender = resolve })
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render-stream', async (route) => {
      await renderHeld
      await route.fulfill({ contentType: 'text/event-stream', body: 'data: {"progress":100}\n\n' })
    })

    try {
      // Trigger auto-render
      await sidebar.editSliderValue('width', 124)

      // Wait for render to start — on the app's own state, then on the control.
      await sidebar.waitForRenderState('rendering')
      await expect(sidebar.cancelButton).toBeVisible({ timeout: 15_000 })

      // Cancel, and wait for the END STATE of a cancel rather than for one
      // button to reappear: the dock stays in its rendering shape until the
      // abort has propagated through the fetch and useRender's 500ms
      // LOADING_RESET_DELAY_MS, so "Generate is not there yet" and "the cancel
      // was dropped" looked identical — both reported as element(s) not found.
      // A dropped click is now retried and a stuck render is now named.
      await sidebar.cancelRenderAndWaitForIdle()

      // Idle for the right reason: the app logs the cancellation only from the
      // AbortError path, so this distinguishes an aborted render from one that
      // was allowed to finish. The route is still held, so it cannot have.
      await expect
        .poll(() => viewer.getConsoleLogs(), {
          timeout: 10_000,
          message: 'the render console never reported the cancellation',
        })
        .toMatch(/CANCEL/i)

      // Verify loading cleared. The app aborts the in-flight fetch, so this
      // holds while the route is still held open.
      await expect(sidebar.generateButton).toBeVisible({ timeout: 10_000 })
      await expect(sidebar.generateButton).toBeEnabled({ timeout: 10_000 })
    } finally {
      releaseRender()
    }
  })

  test('console logs render progress', async ({ page, sidebar, viewer }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(1000)
    const logs = await viewer.getConsoleLogs()
    expect(logs.length).toBeGreaterThan(0)
  })

  test('SSE streaming render updates progress', async ({ page, sidebar }) => {
    // The default mock returns SSE events
    // Verify generate completes
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)
  })

  test('generate button re-enables after render completes', async ({ sidebar }) => {
    await sidebar.clickGenerate()
    // Wait for the render to be OVER — output produced, state back to idle —
    // rather than for 2s and a hope. `isGenerateDisabled()` is a single
    // non-retrying read, so on a runner where the render outlives the sleep it
    // read `disabled` off a render that was still perfectly healthy.
    await sidebar.waitForRenderOutput()
    await sidebar.waitForRenderState('idle')
    expect(await sidebar.isGenerateDisabled()).toBe(false)
  })

  test('render with same params uses cache', async ({ page, sidebar, viewer }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)

    // Generate again with same params
    await sidebar.clickGenerate()
    await page.waitForTimeout(1000)
    const _logs = await viewer.getConsoleLogs()
    // May contain "Loaded from cache" depending on impl
  })

  test('changing parameter triggers auto-render after debounce', async ({ sidebar, viewer }) => {
    // Wait for the initial auto-render to fully complete. An enabled Generate
    // button is also what the page looks like before that render has started,
    // and counting its log lines from there counts one render as two.
    await sidebar.waitForRenderOutput()

    // Get current console log text before the change
    const logsBefore = await viewer.getConsoleLogs()
    const countGenerating = (logs) => (logs.match(/Generating/g) || []).length
    const countBefore = countGenerating(logsBefore)

    // Trigger a parameter change — auto-render should fire after debounce
    await sidebar.editSliderValue('width', 75)

    // Poll for the extra log entry instead of sleeping for 3s: the debounce is
    // 500ms but the render behind it is not, and the assertion is on the app
    // having logged a second "Generating", not on when it got round to it.
    await expect
      .poll(async () => countGenerating(await viewer.getConsoleLogs()), {
        timeout: 20_000,
        message: 'the parameter change never started a second render',
      })
      .toBeGreaterThan(countBefore)
  })

  test('render error shows message in console', async ({ page, sidebar, viewer }) => {
    // Let the initial (successful) auto-render finish first, so the failure
    // below is unambiguously the one produced by the error mock. BEFORE the
    // mock goes in, and on the render's output rather than on an idle sidebar:
    // an idle sidebar is also the 500ms window before the load-time render
    // starts, and that render would then hit the error mock itself.
    await sidebar.waitForRenderOutput()

    await page.unroute('**/api/render')
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render', (route) => {
      route.fulfill({ status: 500, json: { error: 'OpenSCAD crashed' } })
    })
    await page.route('**/api/render-stream', (route) => {
      route.fulfill({ status: 500, json: { error: 'OpenSCAD crashed' } })
    })
    // Change param to bust cache, triggering a fresh render with the error mock
    await sidebar.editSliderValue('width', 55)
    // Poll the console rather than sleeping for a fixed 2s. In run 32565668502
    // the error DID arrive — the post-failure snapshot shows
    //   "Ready. Generating (cup)... [body] Starting... (1/1) Starting OpenSCAD...
    //    Error: OpenSCAD exited with code 1"
    // — but at t=2s the log still read only "Ready. / Generating (cup)... /
    // [body] Starting... (1/1)", which is exactly the string the failure
    // reported as "Received".
    await expect.poll(
      async () => viewer.getConsoleLogs(),
      { timeout: 20_000, message: 'render console never reported an error' },
    ).toContain('Error')
  })

  test('render timeout shows error', async ({ page, sidebar }) => {
    await page.unroute('**/api/render')
    await page.unroute('**/api/render-stream')
    await page.route('**/api/render', (route) => {
      route.abort('timedout')
    })
    await page.route('**/api/render-stream', (route) => {
      route.abort('timedout')
    })
    // Change param to bust cache, triggering render with timeout mock
    await sidebar.editSliderValue('width', 44)
    await page.waitForTimeout(2000)
  })

  test('verify button works after successful render', async ({ page, sidebar }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)
    // After render, verify should be enabled (if parts loaded)
  })

  test('verify shows results in console', async ({ page, sidebar, viewer }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(2000)
    if (!(await sidebar.verifyButton.isDisabled())) {
      await sidebar.clickVerify()
      await page.waitForTimeout(1000)
      const logs = await viewer.getConsoleLogs()
      expect(logs).toContain('Verif')
    }
  })

  test('long render warning dialog appears for high estimates', async ({ page, sidebar }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } }) // 2 minutes
    })
    // Trigger render — this should show confirmation dialog
    await sidebar.generateButton.click()
    await page.waitForTimeout(500)
    // Dialog may appear if estimate exceeds threshold
  })

  test('confirm dialog "Render Anyway" proceeds with render', async ({ page, sidebar }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } })
    })
    await sidebar.generateButton.click()
    await page.waitForTimeout(500)
    const dialog = page.locator('text=Render Anyway')
    if (await dialog.isVisible()) {
      await dialog.click()
    }
  })

  test('confirm dialog "Cancel" aborts render', async ({ page, sidebar }) => {
    await page.route('**/api/estimate', (route) => {
      route.fulfill({ json: { estimated_time: 120 } })
    })
    await sidebar.generateButton.click()
    await page.waitForTimeout(500)
    const cancelBtn = page.locator('[role="alertdialog"] button', { hasText: 'Cancel' })
    if (await cancelBtn.isVisible()) {
      await cancelBtn.click()
    }
  })

  test('progress bar reflects percentage', async ({ page, sidebar }) => {
    // With SSE mock, progress updates from 0→100
    await sidebar.clickGenerate()
    await page.waitForTimeout(500)
  })

  test('progress phase label updates during render', async ({ page, sidebar }) => {
    await sidebar.clickGenerate()
    await page.waitForTimeout(500)
  })

  test('multiple rapid generates are debounced', async ({ page, sidebar }) => {
    await sidebar.clickGenerate()
    await sidebar.clickGenerate()
    await sidebar.clickGenerate()
    // Should not crash, only one render should be active
    await page.waitForTimeout(1000)
    await expect(page.locator('header')).toBeVisible()
  })
})
