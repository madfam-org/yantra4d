import { expect } from '@playwright/test'
import { BasePage } from './base.page.js'

export class StudioSidebarPage extends BasePage {
  constructor(page) {
    super(page)
    this.sidebar = page.locator('[data-testid="studio-sidebar"]')
    this.generateButton = this.sidebar.locator('button', { hasText: /Generate|Generar/ }).first()
    this.cancelButton = this.sidebar.locator('button', { hasText: /Cancel|Cancelar/ }).first()
    this.verifyButton = this.sidebar.locator('button', { hasText: /Verification|Verificación/ }).first()
    // Reset is an icon button — <Button size="icon" title={t("btn.reset")}>
    // with no text node — so a hasText match could never find it and every
    // click on it waited out the full 60s timeout. Match the title, which is
    // also what a screen reader announces.
    this.resetButton = this.sidebar.getByTitle(/Reset to Defaults|Restablecer/i).first()
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
   *
   * Matched on Radix's generated id rather than the tab's text. Radix builds it
   * as `${baseId}-trigger-${value}` from the TabsTrigger `value` prop, which is
   * the same "export" in every locale — matching the label instead broke the
   * moment a test ran in Spanish and looked for "Export" against "Exportar".
   */
  async selectSection(value) {
    const tab = this.sidebar.locator(`[role="tab"][id$="-trigger-${value}"]`).first()
    await tab.click()
    // Wait for the tab to actually report itself selected and for its panel to
    // be on screen, rather than sleeping 150ms and hoping. Radix mounts
    // TabsContent only for the active value, so callers that immediately take a
    // non-retrying reading (locator.count()) were racing the mount — which is
    // how 05-export:95 and 17-auth:90 both counted zero controls on WebKit
    // under ARC load while their retrying siblings passed (run 32565668502).
    await tab.and(this.page.locator('[data-state="active"]')).waitFor({ timeout: 10_000 }).catch(() => { })
    await this.sidebar
      .locator(`[role="tabpanel"][id$="-content-${value}"]`)
      .first()
      .waitFor({ state: 'visible', timeout: 10_000 })
      .catch(() => { })
  }

  /** Locator for the mode tablist (distinguished from section tabs by aria-label). */
  get modeTablist() {
    // The sidebar renders a mode tablist in both its desktop and mobile layout
    // trees, so this matched two elements and `.first()` was a guess about DOM
    // order. The mobile one does not track the desktop one's selection, so
    // getActiveMode() read aria-selected off a stale hidden tab and returned
    // "start" after a click that had correctly switched the mode to "grid" —
    // which is why the sibling test asserting the URL passed at the same time.
    // Scope to the tablist the user can actually see. The two previous branches
    // of the .or() were the same selector written twice: `this.sidebar` IS
    // [data-testid="studio-sidebar"].
    return this.sidebar.locator('[role="tablist"][aria-label="Mode selection"]:visible').first()
  }

  /**
   * Click a mode tab by index (0-based) or data-value/aria-selected.
   *
   * Each branch waits for the clicked tab to actually become selected before
   * returning. Without that, `await selectMode('grid')` resolved as soon as the
   * click dispatched and callers read the pre-render DOM — getActiveMode()
   * returned "start" for a click that had correctly switched to grid, while the
   * sibling test asserting the URL passed because the router had already moved.
   */
  async selectMode(modeId) {
    const tablist = this.modeTablist

    // 1. Try to find by data-value (Radix UI) or text content
    const tabByValue = tablist.locator(`[role="tab"][data-value="${modeId}"]`)
    if (await tabByValue.count() > 0) {
      await tabByValue.click()
      await this._waitForSelected(tabByValue)
      return
    }

    // 2. Try to find by text content (plain button mode tabs)
    const tabByText = tablist.locator(`[role="tab"]`).filter({ hasText: new RegExp(modeId, 'i') }).first()
    if (await tabByText.count() > 0) {
      await tabByText.click()
      await this._waitForSelected(tabByText)
      return
    }

    // 3. Fall back to index-based selection
    const tabs = tablist.locator('[role="tab"]')
    const count = await tabs.count()
    const modeIndex = { cup: 0, single: 1, grid: 2, assembly: 2 }
    const idx = modeIndex[modeId] ?? 0
    if (idx < count) {
      await tabs.nth(idx).click()
      await this._waitForSelected(tabs.nth(idx))
    }
  }

  /**
   * Wait for a mode tab to report itself selected.
   *
   * The desktop ModeTabs are plain buttons carrying aria-selected; the mobile
   * Radix list uses data-state="active". Accept either, and don't fail the
   * caller if neither ever appears — some callers only want the side effect
   * (the route change), and a strict wait here would turn those into timeouts.
   */
  async _waitForSelected(tab) {
    await tab
      .and(this.page.locator('[aria-selected="true"], [data-state="active"]'))
      .waitFor({ timeout: 5000 })
      .catch(() => { })
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

  /**
   * Click the slider value to enter edit mode, set a value, and commit.
   *
   * Convergent, not single-shot. SliderControl renders `editing ? <input> : <span>`
   * and flips `editing` from a plain React onClick, so a click that lands before
   * the handler is attached (WebKit on the contended ARC pods) is silently lost
   * and no input ever appears. The previous body clicked once and then waited an
   * unretried 3 s for `input[type="number"]` — that is the failure PR #56 called
   * out in this page object and worked around locally as
   * helpers/test-utils.js#setSliderValue; this is the same discipline applied
   * where all 29 callers actually go through.
   *
   * @param {string} paramId
   * @param {number|string} value
   * @param {number} [timeout] budget per phase (edit-mode, fill, commit)
   */
  async editSliderValue(paramId, value, timeout = 15_000) {
    const row = this.sidebar.locator(`.flex.justify-between:has(#param-label-${paramId})`)
    // `span[role="button"]`, not the index-based sliderValue() pick: the row's
    // contents swap with `editing`, so `.last()` is a guess about a DOM mid-swap.
    const valSpan = row.locator('span[role="button"]').first()
    const input = row.locator('input[type="number"]')

    // The row itself must be rendered first (param rows re-render when the
    // preset applied by goToStudio's URL-settle step lands; on a contended
    // runner that arrives after the old 5 s budget).
    await expect(valSpan.or(input).first()).toBeVisible({ timeout })

    // Click until the row reports itself in edit mode. Guarded by an up-front
    // isVisible on the SPAN: once a click lands the span unmounts, and a click
    // issued against an unmounted locator does not fail fast — it waits out its
    // whole actionability budget while the locator re-resolves.
    await expect
      .poll(
        async () => {
          if (await input.isVisible().catch(() => false)) return true
          if (!(await valSpan.isVisible().catch(() => false))) return input.isVisible().catch(() => false)
          await valSpan.click({ timeout: 5_000 }).catch(() => { })
          return input.isVisible().catch(() => false)
        },
        {
          timeout,
          message:
            `Slider row "${paramId}" never entered edit mode — the click on its ` +
            "value span was lost before React attached SliderControl's onClick.",
        },
      )
      .toBe(true)

    // Fill until the controlled input actually holds the value. `fill()` dispatches
    // an input event, but the input's value comes from React state, so a fill that
    // lands during a re-render can be discarded and commitEdit would then write
    // the OLD value back.
    await expect
      .poll(
        async () => {
          if ((await input.inputValue().catch(() => null)) === String(value)) return true
          await input.fill(String(value))
          return (await input.inputValue().catch(() => null)) === String(value)
        },
        { timeout, message: `Slider input for "${paramId}" never held ${value} — React discarded the fill.` },
      )
      .toBe(true)

    await input.press('Enter')
    // The input unmounting is `editing === false`, i.e. commitEdit ran.
    await expect(input).toBeHidden({ timeout })
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
