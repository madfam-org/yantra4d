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
   * Click a visible mode tab by its rendered label.
   *
   * ModeTabs (src/components/studio/StudioSidebar.tsx) renders plain buttons
   * carrying nothing but the translated label — no data-value — so selectMode()
   * can only reach a mode whose id appears in its own label. gridfinity's
   * `baseplate_scad` ("Baseplate (OpenSCAD Extended)") and custom-msh's
   * `multi_rack` ("Multi-Rack") are not reachable that way: selectMode() finds
   * no text match and falls through to its index branch, silently clicking the
   * FIRST tab instead of the one asked for. Match the accessible name instead.
   */
  async selectModeByLabel(label) {
    const tab = this.modeTablist.getByRole('tab', { name: label, exact: true }).first()
    await tab.click()
    await this._waitForSelected(tab)
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
    // `.first()` on the row, not just on what hangs off it. `:has()` matches
    // EVERY ancestor that contains the label, so a second `.flex.justify-between`
    // higher up makes this a multi-element locator — and then `input` below is
    // multi-element too, `isVisible()` raises strict mode, and the `.catch()`
    // swallowing it turns "the input is right there" into a silent `false` that
    // no amount of clicking can fix. That is a candidate for run #170's
    // custom-msh flake, where the poll clicked for its whole 15 s against an
    // idle page with the value span plainly present in the snapshot.
    const row = this.sidebar.locator(`.flex.justify-between:has(#param-label-${paramId})`).first()
    // `span[role="button"]`, not the index-based sliderValue() pick: the row's
    // contents swap with `editing`, so `.last()` is a guess about a DOM mid-swap.
    const valSpan = row.locator('span[role="button"]').first()
    const input = row.locator('input[type="number"]').first()

    // The row itself must be rendered first (param rows re-render when the
    // preset applied by goToStudio's URL-settle step lands; on a contended
    // runner that arrives after the old 5 s budget).
    await expect(valSpan.or(input).first()).toBeVisible({ timeout })

    // Click until the row reports itself in edit mode. Guarded by an up-front
    // isVisible on the SPAN: once a click lands the span unmounts, and a click
    // issued against an unmounted locator does not fail fast — it waits out its
    // whole actionability budget while the locator re-resolves.
    //
    // Every failure here used to be swallowed, so a poll that ran out reported
    // only that it had run out. Keep the swallowing — one lost click is not a
    // test failure — but remember WHY each attempt failed and put the last
    // reason in the message, so the next run says whether the click was
    // intercepted, the element detached, or the locator was never unique.
    let lastReason = 'no click was ever attempted'
    const why = (err) => {
      lastReason = String(err && err.message ? err.message : err).split('\n')[0].slice(0, 300)
      return false
    }
    // The rethrow below is what makes that work: expect.poll's `message` is a
    // string built when the poll STARTS, so interpolating lastReason into it
    // would always report the placeholder.
    try {
      await expect
        .poll(
          async () => {
            if (await input.isVisible().catch(why)) return true
            if (!(await valSpan.isVisible().catch(why))) return input.isVisible().catch(why)
            await valSpan.click({ timeout: 5_000 }).catch(why)
            return input.isVisible().catch(why)
          },
          { timeout },
        )
        .toBe(true)
    } catch {
      throw new Error(
        `Slider row "${paramId}" never entered edit mode within ${timeout}ms — the ` +
        "click on its value span was lost before React attached SliderControl's " +
        `onClick. Last failure seen while polling: ${lastReason}`,
      )
    }

    // Fill until the controlled input actually holds the value. `fill()` dispatches
    // an input event, but the input's value comes from React state, so a fill that
    // lands during a re-render can be discarded and commitEdit would then write
    // the OLD value back.
    //
    // The row can also leave edit mode UNDER the poll: the input carries
    // `onBlur={commitEdit}`, and a re-render triggered by something else on the
    // page — the auto-render this very edit is about to start, a manifest or
    // preset update landing late on a contended runner — can take the focus and
    // unmount it. Polling `inputValue()` against an input that is no longer there
    // can then never succeed, which is precisely the "React discarded the fill"
    // failure 10-rendering:131 reports. Re-open the row and fill again instead of
    // spending the whole budget on a locator that has nothing behind it.
    let fillReason = 'no fill was ever attempted'
    const whyFill = (err) => {
      fillReason = String(err && err.message ? err.message : err).split('\n')[0].slice(0, 300)
      return null
    }
    try {
      await expect
        .poll(
          async () => {
            if ((await input.inputValue().catch(whyFill)) === String(value)) return true
            if (!(await input.isVisible().catch(whyFill))) {
              // Back in display mode — the fill has nowhere to land until the
              // row is reopened. Same convergent click as the phase above.
              if (await valSpan.isVisible().catch(whyFill)) {
                await valSpan.click({ timeout: 5_000 }).catch(whyFill)
              }
              return false
            }
            await input.fill(String(value)).catch(whyFill)
            return (await input.inputValue().catch(whyFill)) === String(value)
          },
          { timeout },
        )
        .toBe(true)
    } catch {
      throw new Error(
        `Slider input for "${paramId}" never held ${value} — React discarded the ` +
        `fill. Last failure seen while polling: ${fillReason}`,
      )
    }

    // Commit, and converge on the app DISPLAYING the committed value.
    //
    // `press('Enter')` is a one-shot into commitEdit, and the input is unmounted
    // by the same handler that reads it: a keypress lost the way the opening
    // click can be lost leaves the row in edit mode, and a commit that ran
    // against a discarded editValue leaves it showing the OLD number. Both used
    // to be reported one layer away from where they happened — as an unhidden
    // input, or as the caller waiting out its own budget on a value the app
    // never took. The span carrying `value` proves both halves at once: the span
    // only renders while `editing === false`, so its text IS the committed state.
    let commitReason = 'no commit was ever attempted'
    const whyCommit = (err) => {
      commitReason = String(err && err.message ? err.message : err).split('\n')[0].slice(0, 300)
      return null
    }
    const shownValue = () => valSpan.textContent().then((txt) => txt?.trim()).catch(whyCommit)
    await input.press('Enter').catch(whyCommit)
    try {
      await expect
        .poll(
          async () => {
            if ((await shownValue()) === String(value)) return String(value)
            if (await input.isVisible().catch(whyCommit)) {
              // Still editing: either Enter never arrived, or the fill was
              // discarded before it did. Restore the value, then re-commit.
              if ((await input.inputValue().catch(whyCommit)) !== String(value)) {
                await input.fill(String(value)).catch(whyCommit)
              }
              await input.press('Enter').catch(whyCommit)
            } else if (await valSpan.isVisible().catch(whyCommit)) {
              // Committed the wrong number — reopen and let the branch above
              // put the asked-for one in.
              await valSpan.click({ timeout: 5_000 }).catch(whyCommit)
            }
            return shownValue()
          },
          { timeout },
        )
        .toBe(String(value))
    } catch {
      throw new Error(
        `Slider "${paramId}" never committed ${value} — the row is showing ` +
        `${JSON.stringify(await shownValue())} and Enter did not take. ` +
        `Last failure seen while polling: ${commitReason}`,
      )
    }
    // The input unmounting is `editing === false`, i.e. commitEdit ran.
    await expect(input).toBeHidden({ timeout })
  }

  /** Get text input by param id. */
  textInput(paramId) {
    return this.sidebar.locator(`#text-${paramId}`)
  }

  /**
   * Type a value into a text param and wait until the input actually holds it.
   *
   * The same convergence editSliderValue's fill phase needs, for the same
   * reason: Controls renders these as `value={params[id]}` + onChange, so a
   * fill whose change event is lost — the handler not yet attached, or a
   * re-render landing on top of it — is silently reverted to the value in React
   * state on the next commit. `fill()` replaces the whole value, so repeating
   * it cannot append or double up.
   *
   * @param {string} paramId
   * @param {string} value
   * @param {number} [timeout]
   */
  async fillTextInput(paramId, value, timeout = 15_000) {
    const input = this.textInput(paramId)
    let lastReason = 'no fill was ever attempted'
    const why = (err) => {
      lastReason = String(err && err.message ? err.message : err).split('\n')[0].slice(0, 300)
      return null
    }
    try {
      await expect
        .poll(
          async () => {
            if ((await input.inputValue().catch(why)) === value) return true
            await input.fill(value).catch(why)
            return (await input.inputValue().catch(why)) === value
          },
          { timeout },
        )
        .toBe(true)
    } catch {
      throw new Error(
        `Text input "${paramId}" never held ${JSON.stringify(value)} — React ` +
        `discarded the fill. Last failure seen while polling: ${lastReason}`,
      )
    }
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

  /**
   * Wait until a render has actually FINISHED and produced parts.
   *
   * Not the same as "no render is in flight": the load-time auto-render is
   * debounced 500ms behind the last params change, so an idle sidebar is also
   * what a page looks like in the window BEFORE that render starts. Tests that
   * settle on idle and then install a mock can hand that mock the load-time
   * render and end up cancelling, or asserting on, the second of two
   * overlapping renders.
   *
   * Verify is `disabled={loading || parts.length === 0}` — the one control that
   * is enabled only once a render has come back with output — so waiting for it
   * says a render happened AND is over, without reading any log text.
   *
   * @param {number} [timeout]
   */
  async waitForRenderOutput(timeout = 30_000) {
    await expect(this.verifyButton).toBeEnabled({ timeout })
  }

  /**
   * The app's own render state, as StudioSidebar publishes it:
   * `"rendering"` while a render is in flight, `"idle"` otherwise.
   *
   * Read this rather than inferring the state from the buttons. The dock swaps
   * Generate ⇄ Processing... and Force Regenerate ⇄ Cancel off one `loading`
   * flag, so "Generate is visible" and "the render is over" are the same fact —
   * but the button is ABSENT for the whole of a render, and an absent element
   * can only ever report "element(s) not found". The attribute is present
   * throughout and says which of the two states the app believes it is in.
   *
   * @returns {Promise<string|null>} null if the sidebar is not mounted.
   */
  async renderState() {
    return this.sidebar.getAttribute('data-render-state', { timeout: 5_000 }).catch(() => null)
  }

  /**
   * Wait until the sidebar reports `state`.
   *
   * @param {'idle'|'rendering'} state
   * @param {number} [timeout]
   */
  async waitForRenderState(state, timeout = 20_000) {
    await expect
      .poll(() => this.renderState(), {
        timeout,
        message:
          `the sidebar never reported data-render-state="${state}" within ${timeout}ms. ` +
          'A null reading means the sidebar is not mounted at all; the other state ' +
          'means the app is still where it was, not that a control went missing.',
      })
      .toBe(state)
  }

  /**
   * Cancel the render in flight and wait for the app to report itself idle.
   *
   * Convergent, for the same reason editSliderValue's opening click is: a click
   * on a control React has only just mounted can be lost, and a lost cancel is
   * indistinguishable from a slow one — the render simply stays in flight and
   * every later assertion waits out its budget on a Generate button that is
   * never coming back. Re-clicking is safe and cannot overshoot: Cancel is
   * rendered only while `loading` is true, so once the app is idle there is
   * nothing left to click, and handleCancelGenerate aborts an already-aborted
   * controller as a no-op.
   *
   * It does NOT make a render finish: the abort has to propagate through the
   * fetch and the 500ms LOADING_RESET_DELAY_MS in useRender before the dock
   * comes back. The budget covers that on a contended runner; what it buys over
   * a flat wait is that a timeout here reports the state the app is stuck in.
   *
   * @param {number} [timeout]
   */
  async cancelRenderAndWaitForIdle(timeout = 20_000) {
    let lastReason = 'cancel was never clicked'
    const why = (err) => {
      lastReason = String(err && err.message ? err.message : err).split('\n')[0].slice(0, 300)
      return false
    }
    try {
      await expect
        .poll(
          async () => {
            const state = await this.renderState()
            if (state === 'idle') return 'idle'
            if (await this.cancelButton.isVisible().catch(why)) {
              await this.cancelButton.click({ timeout: 5_000 }).catch(why)
            }
            return this.renderState()
          },
          { timeout },
        )
        .toBe('idle')
    } catch {
      throw new Error(
        `The render never returned to idle within ${timeout}ms of cancelling — the ` +
        `sidebar still reports data-render-state="${await this.renderState()}", so the ` +
        'abort has not settled (or the cancel click is being dropped). Last failure ' +
        `seen while polling: ${lastReason}`,
      )
    }
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
