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
    // Find the row container by filtering for the label ID
    return this.sidebar.locator('.flex.justify-between.items-center')
      .filter({ has: this.page.locator(`#param-label-${paramId}`) })
      .locator('[role="button"], input[type="number"]')
      .first()
  }

  /** Click the slider value to enter edit mode, type a value, and blur. */
  async editSliderValue(paramId, value) {
    const valSpan = this.sliderValue(paramId)
    if (await valSpan.isVisible({ timeout: 3000 }).catch(() => false)) {
      await valSpan.click()
    } else {
      // Fallback: find slider by aria-labelledby and click the value span nearby
      const slider = this.sidebar.locator(`[aria-labelledby="param-label-${paramId}"]`)
      const container = slider.locator('xpath=../../..')
      await container.locator('[role="button"]').click()
    }
    const input = this.sidebar.locator(`input[type="number"]`)
    await input.fill(String(value))
    await input.blur()
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
