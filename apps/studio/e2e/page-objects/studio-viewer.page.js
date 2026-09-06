/* global process */
import { expect } from '@playwright/test'
import { BasePage } from './base.page.js'

// CI budgets. The shared ARC pool runs the commons' nightly sweep (three render
// groups at 1.5 CPU each) alongside PR matrices, so a viewer that goes idle in
// under a second unloaded can take tens of seconds there. 20s was not a budget,
// it was a coin flip; scale it under CI instead of tightening the assertions.
const CI = !!process.env.CI
const VIEWER_READY_TIMEOUT = CI ? 90_000 : 20_000
const CONTROL_CLICK_TIMEOUT = CI ? 30_000 : 10_000

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
   */
  async clickViewerControl(locator) {
    await this.waitForRenderIdle()
    await locator.click({ timeout: CONTROL_CLICK_TIMEOUT })
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
   */
  async toggleAnimation() {
    await this.clickViewerControl(this.animationToggle)
    await expect(this.animationToggle).not.toHaveAttribute(
      'data-anim-state',
      'preparing',
      { timeout: VIEWER_READY_TIMEOUT },
    )
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
