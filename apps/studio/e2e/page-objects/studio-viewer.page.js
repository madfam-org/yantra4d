import { BasePage } from './base.page.js'

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

  /** Click a camera view. */
  async setCameraView(viewId) {
    await this.cameraViewButton(viewId).click()
  }

  /** Toggle axes visibility. */
  async toggleAxes() {
    await this.axesToggle.click()
  }

  /** Toggle grid animation. */
  async toggleAnimation() {
    await this.animationToggle.click()
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
