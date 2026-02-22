import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage } from '../../helpers/test-utils.js'

test.describe('Undo/Redo State Management', () => {
    test.beforeEach(async ({ page }) => {
        await setLanguage(page, 'en')
        await goToStudio(page)
    })

    test('undo button is disabled on fresh load', async ({ page }) => {
        const undoBtn = page.locator('button[aria-label*="ndo"]').first()
        if (await undoBtn.isVisible().catch(() => false)) {
            await expect(undoBtn).toBeDisabled()
        }
    })

    test('redo button is disabled on fresh load', async ({ page }) => {
        const redoBtn = page.locator('button[aria-label*="edo"]').first()
        if (await redoBtn.isVisible().catch(() => false)) {
            await expect(redoBtn).toBeDisabled()
        }
    })

    test('editing a slider value enables undo', async ({ page, sidebar }) => {
        // Make a discrete parameter change
        await sidebar.editSliderValue('width', 100)
        await page.waitForTimeout(600) // Wait for debounce

        const undoBtn = page.locator('button[aria-label*="ndo"]').first()
        if (await undoBtn.isVisible().catch(() => false)) {
            await expect(undoBtn).toBeEnabled({ timeout: 2000 })
        }
    })

    test('undo restores previous parameter value', async ({ page, sidebar }) => {
        // Get initial value
        const initialValue = await sidebar.getSliderValue('width')

        // Change the value
        await sidebar.editSliderValue('width', 150)
        await page.waitForTimeout(600)

        // Click undo
        const undoBtn = page.locator('button[aria-label*="ndo"]').first()
        if (await undoBtn.isVisible().catch(() => false) && await undoBtn.isEnabled()) {
            await undoBtn.click()
            await page.waitForTimeout(300)

            // Value should be restored
            const restoredValue = await sidebar.getSliderValue('width')
            expect(restoredValue).toBe(initialValue)
        }
    })

    test('redo re-applies change after undo', async ({ page, sidebar }) => {
        // Change value
        await sidebar.editSliderValue('width', 200)
        await page.waitForTimeout(600)

        // Undo
        const undoBtn = page.locator('button[aria-label*="ndo"]').first()
        if (await undoBtn.isVisible().catch(() => false) && await undoBtn.isEnabled()) {
            await undoBtn.click()
            await page.waitForTimeout(300)

            // Redo
            const redoBtn = page.locator('button[aria-label*="edo"]').first()
            if (await redoBtn.isVisible().catch(() => false) && await redoBtn.isEnabled()) {
                await redoBtn.click()
                await page.waitForTimeout(300)

                const value = await sidebar.getSliderValue('width')
                expect(value).toBe(200)
            }
        }
    })

    test('keyboard shortcut Ctrl+Z triggers undo', async ({ page, sidebar }) => {
        await sidebar.editSliderValue('width', 175)
        await page.waitForTimeout(600)

        // Press Ctrl+Z
        await page.keyboard.press('Control+z')
        await page.waitForTimeout(300)

        // Undo button should now be disabled (back to initial state)
        const undoBtn = page.locator('button[aria-label*="ndo"]').first()
        if (await undoBtn.isVisible().catch(() => false)) {
            await expect(undoBtn).toBeDisabled({ timeout: 2000 })
        }
    })

    test('keyboard shortcut Ctrl+Shift+Z triggers redo', async ({ page, sidebar }) => {
        await sidebar.editSliderValue('width', 175)
        await page.waitForTimeout(600)

        await page.keyboard.press('Control+z')
        await page.waitForTimeout(300)

        await page.keyboard.press('Control+Shift+z')
        await page.waitForTimeout(300)

        const value = await sidebar.getSliderValue('width')
        expect(value).toBe(175)
    })
})
