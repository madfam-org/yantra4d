/* global process */
import { expect } from '@playwright/test'
import { BasePage } from './base.page.js'

// CI budgets. The shared ARC pool runs the commons' nightly sweep (three render
// groups at 1.5 CPU each) alongside PR matrices, so a viewer that goes idle in
// under a second unloaded can take tens of seconds there. 20s was not a budget,
// it was a coin flip; scale it under CI instead of tightening the assertions.
const CI = !!process.env.CI
// Every budget here must fit INSIDE playwright.config.js's 60s per-test timeout,
// or it can never expire: the test dies on the outer timeout first and the
// assertion's own message — the one naming what never settled — is never
// printed. That is what made firefox shard 1/3 read as a mystery on run
// 34028413876: a 90s inner budget under a 60s test could only ever surface as
// "Test timeout of 60000ms exceeded".
//
// So these are sized as a BUDGET THAT SUMS, against the per-test ceiling the
// caller sets (the toggle spec raises its own to 150s in CI precisely because it
// runs this chain twice). toggleAnimation() is the longest chain —
// canvas-stable, then render-idle, then the click, then the settle.
//
// The click budget is the one that must NOT be squeezed. Measured locally on a
// machine at load ~24 (other lanes rendering), 10s was not enough for firefox to
// actuate a click on a control floating over the repainting canvas: 7 of 8
// failures in a 10× run were `locator.click: Timeout 10000ms exceeded`, and the
// same test passes comfortably unloaded. The ARC pool is contended the same way.
const VIEWER_READY_TIMEOUT = CI ? 20_000 : 20_000
const CONTROL_CLICK_TIMEOUT = CI ? 30_000 : 15_000
// How long the animated grid gets to leave `preparing`. See toggleAnimation.
const ANIM_SETTLE_TIMEOUT = CI ? 20_000 : 15_000

export class StudioViewerPage extends BasePage {
  constructor(page) {
    super(page)
    this.viewerContainer = page.locator('.flex-1.relative.flex.flex-col')
    this.canvas = page.locator('canvas').first()
    // StudioMainView renders two render consoles — one in the desktop layout,
    // one in the mobile layout behind consoleExpanded — and both carry
    // role="log". Matching bare [role="log"] resolved to both and failed strict
    // mode on every console assertion. Scope to whichever the user can actually
    // see; if both were ever visible at once that is an app bug, and strict mode
    // will still say so rather than quietly picking one.
    this.console = page.locator('[role="log"]:visible')
    this.loadingOverlay = page.locator('text=Rendering..., text=Renderizando...')
    this.progressBar = page.locator('.bg-primary.transition-all')
    this.progressText = page.locator('.text-muted-foreground', { hasText: '%' })
    // Also duplicated across the desktop and mobile layout trees: 4 in the
    // DOM, 1 visible. Same reason as the console above.
    this.axesToggle = page.locator('button:visible', { hasText: /⊞|⊟/ })
    // 4 in the DOM, same double-mount as the console and the axes toggle above.
    this.animationToggle = page.locator('[data-testid="animation-toggle"]:visible').first()
  }

  /** Get camera view button by view id. */
  cameraViewButton(viewId) {
    // Camera view buttons are in the top-right button group, present in both
    // layout trees — the unscoped selector resolved to 4 elements.
    // Both layout trees also carry the button group itself, so :visible alone
    // still left two candidates in some layouts and the click waited out its
    // timeout. Take the first visible match.
    const viewLabels = { iso: 'Isometric', top: 'Top', front: 'Front', right: 'Right' }
    return this.page.locator('.absolute.top-2.right-2 button:visible', { hasText: new RegExp(viewLabels[viewId] || viewId, 'i') }).first()
  }

  /**
   * Wait for the viewer to actually be render-idle.
   *
   * While a render is in flight the viewer covers itself with
   * `absolute inset-0 z-50 bg-background/80 backdrop-blur-sm`, which intercepts
   * pointer events. Clicks on viewer controls then retry until the test times
   * out — Playwright reports "element is visible, enabled and stable" followed
   * by "<div …> intercepts pointer events", which reads like a flaky selector
   * but is the app correctly blocking input mid-render.
   *
   * The viewer root publishes exactly that condition as
   * `data-render-state="rendering" | "idle"` — the same `loading` prop that
   * decides whether LoadingOverlay mounts — so we wait on the app's own signal
   * rather than on a visibility predicate that has to agree with Playwright's.
   *
   * This THROWS on timeout. The previous version ended in `.catch(() => {})`,
   * so a viewer that never went idle inside the budget resolved anyway and the
   * caller clicked straight into the overlay; the failure then surfaced far
   * downstream as an attribute that never changed. A readiness helper that
   * cannot fail is not a readiness helper.
   */
  async waitForRenderIdle(timeout = VIEWER_READY_TIMEOUT) {
    // One assertion, one budget. `toHaveAttribute` already waits for the
    // element to exist, so there is no separate attach wait to cap — and
    // capping it was a real bug: StudioMainView mounts the viewer tree from
    // `isDesktop`, a responsive hook, so a layout settle under load unmounts
    // and remounts the whole <Viewer>. A 15s attach cap inside a 90s budget
    // could not ride that out, and the helper failed on a viewer that was
    // merely remounting (2/10 locally before this line was fixed).
    await expect(
      this.page.locator('[data-testid="viewer-root"]').first(),
    ).toHaveAttribute('data-render-state', 'idle', { timeout })
  }

  /**
   * Click a viewer control once the viewer is render-idle.
   *
   * Every viewer control sits under the same overlay, so every one of them can
   * lose a click the same way the animation toggle did. Route them all through
   * one helper so the fix is structural rather than a patch on the one test
   * that happened to fail.
   *
   * These controls float over the R3F <canvas>, which repaints every frame, and
   * headless firefox cannot reliably drive a real mouse click onto them: the log
   * reaches "element is visible, enabled and stable", prints "performing click
   * action", and then hangs until the budget expires. Measured over a 10× run on
   * an otherwise idle machine, 5 of 8 failures were `locator.click: Timeout
   * 30000ms exceeded` on a button that was clickable throughout — and `force:
   * true` does not help, because the part that stalls is the actuation itself,
   * not the actionability checks it skips.
   *
   * So dispatch the activation directly instead of asking the browser's input
   * pipeline to synthesise it. `element.click()` runs the same click handler
   * React bound (it dispatches a real, bubbling, cancelable PointerEvent-backed
   * click through the DOM), which is exactly what these tests are about: does
   * the control's handler run and drive the app's state.
   *
   * What this trades away is hit-testing — a control covered by something else
   * would still be "clicked". That coverage is not lost, it is made explicit and
   * checked BEFORE the dispatch: waitForRenderIdle() throws unless the app
   * reports itself idle, which is precisely when the LoadingOverlay's
   * `inset-0 z-50` pointer-blocking sheet is unmounted; the specs assert
   * visibility with `expect(...).toBeVisible()`; and `evaluate` throws on its
   * own if the locator resolves to nothing. A test that mattered on hit-testing
   * would be one asserting the overlay blocks input — and that is not this one.
   */
  async clickViewerControl(locator) {
    await this.waitForRenderIdle()
    await locator.waitFor({ state: 'visible', timeout: CONTROL_CLICK_TIMEOUT })
    await locator.evaluate((el) => el.click())
  }

  /**
   * Wait until the viewer's canvas has stopped being torn down and re-created.
   *
   * Headless firefox brings the canvas up on a software GL stack that loses its
   * drawing surface under load — the page logs `WebGL warning: <Present>: Swap
   * chain surface creation failed`, then `WebGL context was lost` /
   * `THREE.WebGLRenderer: Context Restored.`, repeatedly. R3F re-creates the
   * <Canvas> subtree on every restore, which UNMOUNTS whatever is inside it.
   *
   * That is the firefox failure this page object kept mis-reading as a lost
   * click. AnimatedGrid lives inside the Canvas and fetches its STLs in a mount
   * effect whose cleanup sets `cancelled = true`; that flag suppresses BOTH
   * `onReady` and `onError` (AnimatedGrid.tsx). So a teardown mid-fetch drops
   * the settle callback on the floor while the PARENT keeps `animating` true —
   * and `data-anim-state` is `animating && !animReady` → `preparing`, forever.
   * `fetchAssemblyGeometries` caches successes only, so each remount re-runs the
   * fetch and re-loses the race. No budget can outwait that, which is why
   * widening the assertion to accept `preparing` would not have been a fix: it
   * would have made a permanent app-side hang report green.
   *
   * What we need before clicking is not a pristine context — firefox never
   * offers one, it churns for the life of the page — but a canvas that has held
   * the SAME element for a beat, so the mount we start can survive its own
   * fetch. Identity is the signal: R3F swaps the <canvas> element itself on a
   * restore, so a node that stays `===` across consecutive polls is a subtree
   * that is not being torn down right now.
   *
   * Deliberately NOT `canvas.getContext(...)`: on a canvas that already owns a
   * Three.js context, asking firefox for a different context type returns null,
   * so a `getContext`-based gate can never pass there — it timed out on every
   * run before this was rewritten.
   */
  async waitForCanvasStable(timeout = VIEWER_READY_TIMEOUT) {
    await this.page.waitForFunction(
      () => {
        const canvas = document.querySelector('canvas')
        if (!canvas) {
          globalThis.__y4dCanvasSeen = null
          globalThis.__y4dCanvasRuns = 0
          return false
        }
        if (globalThis.__y4dCanvasSeen !== canvas) {
          globalThis.__y4dCanvasSeen = canvas
          globalThis.__y4dCanvasRuns = 1
          return false
        }
        globalThis.__y4dCanvasRuns = (globalThis.__y4dCanvasRuns || 0) + 1
        // Two consecutive identical reads (~250 ms of the same element), not
        // more: firefox's canvas keeps churning for the life of the page, so a
        // longer run of stability is a condition it may simply never offer, and
        // demanding it turns this guard into its own flake. This only has to
        // catch the case where we are mid-teardown right now; the settle
        // assertion in toggleAnimation() is what actually holds the line.
        return globalThis.__y4dCanvasRuns >= 2
      },
      null,
      { timeout, polling: 250 },
    )
  }

  /** Click a camera view. */
  async setCameraView(viewId) {
    await this.clickViewerControl(this.cameraViewButton(viewId))
  }

  /** Toggle axes visibility. */
  async toggleAxes() {
    await this.clickViewerControl(this.axesToggle)
  }

  /**
   * Toggle grid animation and wait for the app to settle on a real state.
   *
   * Resolves to the settled `data-anim-state`. Callers must look at it: the
   * animated grid fetches and worker-parses assembly STLs, and on a starved
   * runner that fetch/parse fails, at which point AnimatedGrid's `onError`
   * calls `setAnimating(false)` — the app turns the toggle back off by itself.
   * A test that only watches `aria-pressed` sees that revert as a click that
   * never landed and re-clicks into a loop it cannot win, because every
   * successful click is undone by the next failed fetch. That is precisely how
   * this test failed on run 34023576549: `aria-pressed` was polled 18 times and
   * was `false` every time, while the click had in fact landed each round.
   *
   * There is no blind re-click here. One click, then wait for `data-anim-state`
   * to leave `preparing` — the only transient value — and report what it landed
   * on. `error` is a legitimate outcome under CPU starvation and is the caller's
   * to interpret, not something to retry away.
   *
   * `preparing` stays a FAILURE. It is reachable only two ways: the fetch is
   * still in flight (that is what the budget is for), or AnimatedGrid was
   * unmounted mid-fetch by a canvas teardown and no settle callback will ever
   * fire (see waitForCanvasStable). The second is a real hang, and a helper that
   * returned it as an admissible value would hand the caller a green test for a
   * viewer stuck behind a "Preparing…" overlay. Waiting for the canvas to hold
   * still BEFORE starting the grid is what makes the strict assertion honest.
   *
   * That wait applies only to the toggle that STARTS the animation. Once the
   * grid is running the canvas legitimately churns — that is the feature — and
   * demanding a settled canvas before the toggle-off would time out on a viewer
   * doing exactly what it was asked to do. Turning it off starts no fetch, so
   * there is no mount to protect.
   */
  async toggleAnimation() {
    const startingUp =
      (await this.animationToggle.getAttribute('data-anim-state')) !== 'playing'
    if (startingUp) await this.waitForCanvasStable()
    await this.clickViewerControl(this.animationToggle)
    await expect(
      this.animationToggle,
      'animation toggle never left `preparing`: AnimatedGrid resolved neither ' +
        'onReady nor onError. Usually its mount was torn down mid-fetch by a ' +
        'WebGL context loss (check the page console for "WebGL context was lost").',
    ).not.toHaveAttribute('data-anim-state', 'preparing', {
      timeout: ANIM_SETTLE_TIMEOUT,
    })
    return this.animationToggle.getAttribute('data-anim-state')
  }

  /** Get console log text. */
  async getConsoleLogs() {
    return this.console.textContent()
  }

  /** Wait for console to contain text. */
  async waitForConsoleText(text, timeout = 10_000) {
    await this.console.locator(`text=${text}`).waitFor({ timeout })
  }

  /** Check if loading overlay is visible. */
  async isLoading() {
    return this.loadingOverlay.isVisible()
  }

  /** Get print estimate overlay. */
  printEstimate() {
    return this.page.locator('text=Print Estimate, text=Estimación de Impresión').locator('..')
  }

  /** Get material select in print estimate. */
  materialSelect() {
    return this.page.locator('#pe-material')
  }

  /** Get infill select in print estimate. */
  infillSelect() {
    return this.page.locator('#pe-infill')
  }
}
