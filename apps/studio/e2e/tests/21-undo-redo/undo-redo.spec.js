import { test, expect } from '../../fixtures/app.fixture.js'
import {
    goToStudio,
    setLanguage,
    undoButton,
    redoButton,
    waitForUndoBaseline,
    waitForEditRecorded,
} from '../../helpers/test-utils.js'

/**
 * This whole file was inert. Every test located its buttons as
 * `button[aria-label*="ndo"]` — a selector that matches nothing, because
 * StudioHeader labels undo/redo with `title` and an sr-only span and sets no
 * aria-label anywhere in the app — and then guarded its assertions behind
 *
 *     if (await btn.isVisible().catch(() => false)) { ...assert... }
 *
 * With a locator that can never resolve, that condition is always false, so
 * six of the seven tests ran to completion having asserted nothing at all.
 *
 * The single assertion that sat outside such a guard is the redo value check
 * in the last test — and that is exactly the assertion reported failing on the
 * webkit shard of run 32792016684. So this file was not "green with one flaky
 * test": it was one live assertion, which flaked, plus six false greens.
 *
 * The guards were also never expressing real optionality — the product renders
 * both buttons unconditionally on desktop, `disabled` rather than absent when
 * there is nothing to undo. Fixing the locator and dropping the guards is both
 * correct and strictly stronger.
 */

test.describe('Undo/Redo State Management', () => {
    test.beforeEach(async ({ page }) => {
        await setLanguage(page, 'en')
        await goToStudio(page)
        // The undo history must be at a known-empty baseline before any test
        // edits anything — see waitForUndoBaseline for why the auto-redirect
        // can otherwise push a preset entry onto the stack and invert the
        // meaning of Ctrl+Z / Ctrl+Shift+Z.
        await waitForUndoBaseline(page)
    })

    test('undo button is disabled on fresh load', async ({ page }) => {
        await expect(undoButton(page)).toBeDisabled({ timeout: 15_000 })
    })

    test('redo button is disabled on fresh load', async ({ page }) => {
        await expect(redoButton(page)).toBeDisabled({ timeout: 15_000 })
    })

    test('editing a slider value enables undo', async ({ page, sidebar }) => {
        // Make a discrete parameter change
        await sidebar.editSliderValue('width', 100)
        // Was `waitForTimeout(600) // Wait for debounce`. canUndo flipping IS
        // the app's statement that the edit reached the history; the 600ms was
        // a guess calibrated against RENDER_DEBOUNCE_MS on one machine.
        await expect(undoButton(page)).toBeEnabled({ timeout: 15_000 })
    })

    test('undo restores previous parameter value', async ({ page, sidebar }) => {
        // Get initial value
        const initialValue = await sidebar.sliderValue('width').textContent()

        // Change the value
        await sidebar.editSliderValue('width', 150)
        await waitForEditRecorded(page)
        await expect(sidebar.sliderValue('width')).toHaveText(/150/, { timeout: 15_000 })

        // Click undo — unconditionally. waitForEditRecorded already established
        // it is enabled, so the old `if (visible && enabled)` guard could only
        // ever have skipped the assertion, never protected it.
        await undoButton(page).click()

        // Value should be restored
        await expect
            .poll(() => sidebar.sliderValue('width').textContent(), { timeout: 15_000 })
            .toBe(initialValue)
    })

    test('redo re-applies change after undo', async ({ page, sidebar }) => {
        // Change value
        await sidebar.editSliderValue('width', 200)
        await waitForEditRecorded(page)
        await expect(sidebar.sliderValue('width')).toHaveText(/200/, { timeout: 15_000 })

        // Undo
        await undoButton(page).click()
        // Redo only becomes enabled once the undo has committed — that flip is
        // the app's own signal that it is safe to redo, and replaces the
        // `waitForTimeout(300)` that used to stand in for it.
        await expect(redoButton(page)).toBeEnabled({ timeout: 15_000 })

        // Redo
        await redoButton(page).click()
        await expect
            .poll(() => sidebar.sliderValue('width').textContent(), { timeout: 15_000 })
            .toBe('200')
    })

    test('keyboard shortcut Ctrl+Z triggers undo', async ({ page, sidebar }) => {
        await sidebar.editSliderValue('width', 175)
        await waitForEditRecorded(page)

        // editSliderValue commits with Enter and the input then unmounts, but
        // focus can land back on the numeric input's row. useKeyboardShortcuts
        // ignores keydown whose target is INPUT/TEXTAREA/SELECT, so a Ctrl+Z
        // sent while focus is still inside the param input is dropped on the
        // floor — silently, since the old test's `if (visible)` guard then
        // asserted "still disabled" against a button that had never been
        // enabled. Move focus somewhere the handler will act on first.
        await page.locator('#main-content:visible').first().click()

        // Press Ctrl+Z
        await page.keyboard.press('Control+z')

        // Undo button should now be disabled (back to initial state)
        await expect(undoButton(page)).toBeDisabled({ timeout: 15_000 })
        // Strengthened: assert the value actually reverted, not merely that the
        // button went disabled. A shortcut that did nothing at all would also
        // leave the button disabled if the edit had never been recorded — which
        // is precisely what the old guarded version could not distinguish.
        await expect(sidebar.sliderValue('width')).not.toHaveText(/^175$/, { timeout: 15_000 })
    })

    test('keyboard shortcut Ctrl+Shift+Z triggers redo', async ({ page, sidebar }) => {
        await sidebar.editSliderValue('width', 175)
        await waitForEditRecorded(page)
        await expect(sidebar.sliderValue('width')).toHaveText(/175/, { timeout: 15_000 })

        // Same focus concern as the Ctrl+Z sibling: the shortcut handler
        // early-returns for INPUT targets.
        await page.locator('#main-content:visible').first().click()

        await page.keyboard.press('Control+z')
        // Wait for the undo to commit via the app's own signal rather than
        // sleeping 300ms — the redo button becoming enabled is exactly "there
        // is now something to redo", which is the precondition for the next
        // keystroke to mean anything.
        await expect(redoButton(page)).toBeEnabled({ timeout: 15_000 })

        await page.keyboard.press('Control+Shift+z')

        await expect
            .poll(() => sidebar.sliderValue('width').textContent(), { timeout: 15_000 })
            .toBe('175')
    })
})
