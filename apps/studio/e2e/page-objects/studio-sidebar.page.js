import { BasePage } from './base.page.js'

export class StudioSidebarPage extends BasePage {
  constructor(page) {
    super(page)
    this.sidebar = page.locator('.w-80').first()
    this.generateButton = this.sidebar.locator('button', { hasText: /Generate|Generar/ }).first()
    this.cancelButton = this.sidebar.locator('button', { hasText: /Cancel|Cancelar/ }).first()
    this.verifyButton = this.sidebar.locator('button', { hasText: /Verification|Verificación/ }).first()
    this.resetButton = this.sidebar.locator('button', { hasText: /Reset to Defaults|Restablecer/ }).first()
  }

  /** Get mode tab trigger by mode id or label. */
  modeTab(modeIdOrLabel) {
    // Radix TabsTrigger uses data-value attribute for the value prop
    return this.sidebar.locator(`[role="tablist"] button`).filter({
      has: this.page.locator(`text="${modeIdOrLabel}"`)
    }).first().or(
      this.sidebar.locator(`[role="tab"]`).nth(
        modeIdOrLabel === 'single' ? 0 : modeIdOrLabel === 'grid' ? 1 : 0
      )
    )
  }

  /** Click a mode tab by index (0-based) or data-value. */
  async selectMode(modeId) {
    // 1. Try to find by data-value (Radix UI)
    const tabByValue = this.sidebar.locator(`[role="tablist"] [role="tab"][data-value="${modeId}"]`)
    if (await tabByValue.count() > 0) {
      await tabByValue.click()
      return
    }

    const tabs = this.sidebar.locator('[role="tablist"] [role="tab"]')
    const count = await tabs.count()
    // Map mock mode IDs to indices based on MOCK_MANIFEST (cup, single, grid)
    const modeIndex = { cup: 0, single: 1, grid: 2, assembly: 2 }
    const idx = modeIndex[modeId] ?? 0
    if (idx < count) {
      await tabs.nth(idx).click()
    }
  }

  /** Get the active mode tab's data-value or text. */
  async getActiveMode() {
    const active = this.sidebar.locator('[role="tablist"] [role="tab"][data-state="active"]')
    // Try data-value first, fall back to text content
    const dataValue = await active.getAttribute('data-value').catch(() => null)
    if (dataValue) return dataValue
    const text = await active.textContent()
    return text.trim().toLowerCase()
  }

  /** Get a preset button by label text. */
  presetButton(label) {
    return this.sidebar.locator('button', { hasText: label })
  }

  /** Click a size preset. */
  async applyPreset(label) {
    await this.presetButton(label).click()
  }

  /** Get slider by param id. */
  slider(paramId) {
    return this.sidebar.locator(`[aria-labelledby="param-label-${paramId}"]`)
  }

  /** Get the displayed value span for a slider (the clickable value next to the label). */
  sliderValue(paramId) {
    // Find the SliderControl container that has the matching label, then get the value display.
    // Uses the label id to scope to the correct control without fragile xpath traversal.
    const container = this.sidebar.locator(`.space-y-2:has(#param-label-${paramId})`)
    return container.locator('.flex.justify-between').first()
      .locator('[role="button"], input[type="number"]').last()
  }

  /** Click the slider value to enter edit mode, type a value, and commit. */
  async editSliderValue(paramId, value) {
    const container = this.sidebar.locator(`.space-y-2:has(#param-label-${paramId})`)
    const valSpan = this.sliderValue(paramId)
    await valSpan.waitFor({ state: 'visible', timeout: 5000 })
    await valSpan.click()
    // Scope input to the parameter's container to avoid matching other inputs
    const input = container.locator(`input[type="number"]`)
    await input.waitFor({ state: 'visible', timeout: 3000 })
    // Use fill() to atomically clear and set the value. Previous approaches
    // (selectText, triple-click, Ctrl+A) all raced with React's autoFocus
    // under parallel test load, especially in Chromium where the Selection API
    // is restricted for <input type="number">.
    await input.fill(String(value))
    await input.press('Enter')
    // Wait for the input to disappear (confirming commit back to display mode)
    await input.waitFor({ state: 'hidden', timeout: 3000 })
  }

  /** Get text input by param id. */
  textInput(paramId) {
    return this.sidebar.locator(`#text-${paramId}`)
  }

  /** Get checkbox by param id. */
  checkbox(paramId) {
    return this.sidebar.locator(`#${paramId}`)
  }

  /** Toggle wireframe switch. */
  async toggleWireframe() {
    await this.sidebar.locator('#wireframe-toggle').click()
  }

  /** Get color input for a part. */
  colorInput(partId) {
    return this.sidebar.locator(`#color-${partId}`)
  }

  /** Get the Basic/Advanced visibility toggle. */
  visibilityToggle() {
    return this.sidebar.locator('button', { hasText: /Advanced|Basic|Avanzado|Básico/ })
  }

  /** Click generate. */
  async clickGenerate() {
    await this.generateButton.click()
  }

  /** Click cancel. */
  async clickCancel() {
    await this.cancelButton.click()
  }

  /** Click verify. */
  async clickVerify() {
    await this.verifyButton.click()
  }

  /** Click reset. */
  async clickReset() {
    await this.resetButton.click()
  }

  /** Check if generate button is disabled. */
  async isGenerateDisabled() {
    return this.generateButton.isDisabled()
  }
}
