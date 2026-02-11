import { BasePage } from './base.page.js'

export class StudioViewerPage extends BasePage {
  constructor(page) {
    super(page)
    this.viewerContainer = page.locator('.flex-1.relative.flex.flex-col')
    this.canvas = page.locator('canvas').first()
    this.console = page.locator('[role="log"]')
    this.loadingOverlay = page.locator('text=Rendering..., text=Renderizando...')
    this.progressBar = page.locator('.bg-primary.transition-all')
    this.progressText = page.locator('.text-muted-foreground', { hasText: '%' })
    this.axesToggle = page.locator('button', { hasText: /⊞|⊟/ })
    this.animationToggle = page.locator('[data-testid="animation-toggle"]')
  }

  /** Get camera view button by view id. */
  cameraViewButton(viewId) {
    // Camera view buttons are in the top-right button group
    const viewLabels = { iso: 'Isometric', top: 'Top', front: 'Front', right: 'Right' }
    return this.page.locator('.absolute.top-2.right-2 button', { hasText: new RegExp(viewLabels[viewId] || viewId, 'i') })
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
