import { BasePage } from './base.page.js'

export class StudioSidebarPage extends BasePage {
  constructor(page) {
    super(page)
    this.sidebar = page.locator('[data-testid="studio-sidebar"]')
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

  /**
   * Select one of the sidebar's section tabs: config | view | analysis | export.
   *
   * StudioSidebar wraps its panels in <Tabs defaultValue="config">, so
   * ExportPanel, PrintPanel and the BOM only exist in the DOM once their tab is
   * selected. Tests that assume a panel is present on load find nothing at all.
   */
  async selectSection(value) {
    const labels = { config: 'Design', view: 'View', analysis: 'BOM', export: 'Export' }
    const tab = this.sidebar
      .locator('[role="tablist"]:not([aria-label="Mode selection"]) [role="tab"]')
      .filter({ hasText: new RegExp(labels[value] || value, 'i') })
      .first()
    await tab.click()
    await this.page.waitForTimeout(150)
  }

  /** Locator for the mode tablist (distinguished from section tabs by aria-label). */
  get modeTablist() {
    // Desktop: custom ModeTabs with aria-label="Mode selection"
    // Mobile: Radix TabsList inside the mobile bar
    return this.sidebar.locator('[role="tablist"][aria-label="Mode selection"]').or(
      this.page.locator('[data-testid="studio-sidebar"] [role="tablist"][aria-label="Mode selection"]')
    ).first()
  }

  /** Click a mode tab by index (0-based) or data-value/aria-selected. */
  async selectMode(modeId) {
    const tablist = this.modeTablist

    // 1. Try to find by data-value (Radix UI) or text content
    const tabByValue = tablist.locator(`[role="tab"][data-value="${modeId}"]`)
    if (await tabByValue.count() > 0) {
      await tabByValue.click()
      return
    }

    // 2. Try to find by text content (plain button mode tabs)
    const tabByText = tablist.locator(`[role="tab"]`).filter({ hasText: new RegExp(modeId, 'i') }).first()
    if (await tabByText.count() > 0) {
      await tabByText.click()
      return
    }

    // 3. Fall back to index-based selection
    const tabs = tablist.locator('[role="tab"]')
    const count = await tabs.count()
    const modeIndex = { cup: 0, single: 1, grid: 2, assembly: 2 }
    const idx = modeIndex[modeId] ?? 0
    if (idx < count) {
      await tabs.nth(idx).click()
    }
  }

  /** Get the active mode tab's data-value or text. */
  async getActiveMode() {
    const tablist = this.modeTablist
    // Mode tabs use aria-selected="true" (plain buttons) or data-state="active" (Radix)
    const active = tablist.locator('[role="tab"][aria-selected="true"], [role="tab"][data-state="active"]').first()
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
    // Scope to the flex row that contains this param's label — avoids matching sibling sliders
    const row = this.sidebar.locator(`.flex.justify-between:has(#param-label-${paramId})`)
    return row.locator('[role="button"], input[type="number"]').last()
  }

  /** Click the slider value to enter edit mode, type a value, and commit. */
  async editSliderValue(paramId, value) {
    const row = this.sidebar.locator(`.flex.justify-between:has(#param-label-${paramId})`)
    const valSpan = this.sliderValue(paramId)
    await valSpan.waitFor({ state: 'visible', timeout: 5000 })
    await valSpan.click()
    // Scope input to the parameter's row to avoid matching other inputs
    const input = row.locator(`input[type="number"]`)
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
