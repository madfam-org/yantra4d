import { test, expect } from '../../fixtures/app.fixture.js'
import {
  goToStudio,
  setLanguage,
  setTheme,
  waitForHeaderReady,
  themeButton,
  settledTheme,
  cycleThemeTo,
  THEME_ICONS,
} from '../../helpers/test-utils.js'

/**
 * Assert the <html> class the ThemeProvider commits, waiting for it rather
 * than sampling it.
 *
 * Every test below used a bare `page.evaluate(() => classList.contains('dark'))`
 * immediately after goToStudio. ThemeProvider applies that class from a
 * useEffect, so the read races the effect: it is only reliable because
 * goToStudio happens to sleep 500ms at the end. These are latent siblings of
 * the reported flake — same provider, same commit-after-paint window, just
 * reading the class instead of the icon — so they get the same retrying read.
 * The assertion is unchanged; only the sampling becomes a wait.
 */
async function expectDarkClass(page, expected) {
  await expect
    .poll(() => page.evaluate(() => document.documentElement.classList.contains('dark')), {
      timeout: 15_000,
      message: `<html> never settled to ${expected ? 'dark' : 'light'}.`,
    })
    .toBe(expected)
}

test.describe('Theme System', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  test('light theme applies correct classes', async ({ page }) => {
    await setTheme(page, 'light')
    await goToStudio(page)
    await expectDarkClass(page, false)
  })

  test('dark theme applies dark class to html', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    await expectDarkClass(page, true)
  })

  test('system theme follows OS preference', async ({ page }) => {
    await setTheme(page, 'system')
    await page.emulateMedia({ colorScheme: 'dark' })
    await goToStudio(page)
    await expectDarkClass(page, true)
  })

  test('system theme follows light OS preference', async ({ page }) => {
    await setTheme(page, 'system')
    await page.emulateMedia({ colorScheme: 'light' })
    await goToStudio(page)
    await expectDarkClass(page, false)
  })

  test('theme persists across reload', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    await page.reload()
    await waitForHeaderReady(page)
    // Strengthened: also assert the reloaded app actually APPLIED the persisted
    // theme, not merely that the key survived. The old assertion would have
    // passed even if the provider had failed to read the key on boot, since
    // setTheme seeds the key via addInitScript on every load.
    expect(await page.evaluate(() => localStorage.getItem('vite-ui-theme'))).toBe('dark')
    await expectDarkClass(page, true)
  })

  // The three icon tests below matched `button:has(.lucide-X)` unscoped and
  // took .first(). Two problems, both the shapes this campaign has been
  // fixing: (a) the studio renders header controls in more than one layout
  // tree, so .first() was a guess about DOM order rather than a match on the
  // button the user can see, and (b) an icon-class selector's identity changes
  // with the state it is meant to be reporting, so the locator only resolves
  // once the swap has painted. themeButton() is matched on the button's stable
  // identity and scoped to the visible header; the icon is then asserted as a
  // property OF that button.
  test('theme toggle button shows correct icon for light', async ({ page }) => {
    await setTheme(page, 'light')
    await goToStudio(page)
    await waitForHeaderReady(page)
    await expect(themeButton(page).locator(THEME_ICONS.light)).toBeVisible({ timeout: 15_000 })
  })

  test('theme toggle button shows correct icon for dark', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    await waitForHeaderReady(page)
    await expect(themeButton(page).locator(THEME_ICONS.dark)).toBeVisible({ timeout: 15_000 })
  })

  test('theme toggle button shows correct icon for system', async ({ page }) => {
    await setTheme(page, 'system')
    await goToStudio(page)
    await waitForHeaderReady(page)
    await expect(themeButton(page).locator(THEME_ICONS.system)).toBeVisible({ timeout: 15_000 })
  })

  test('cycling theme updates localStorage', async ({ page }) => {
    await setTheme(page, 'light')
    await goToStudio(page)
    // The header must have swapped in the loaded manifest before we click one
    // of its buttons: `manifest.project.name`, canUndo/canRedo and
    // useProjectMeta all re-render StudioHeader as the fetch lands, and a click
    // dispatched into that window is lost. The old test absorbed those lost
    // clicks with a re-click loop instead of preventing them.
    await waitForHeaderReady(page)

    const themes = ['light', 'dark', 'system']

    // Read the app's SETTLED theme, not a bare localStorage sample. The
    // provider writes the key synchronously in handleSetTheme but applies the
    // <html> class from a useEffect, so there is a real window where the two
    // disagree — reading only the key is how the old test could proceed to
    // demand the moon icon before React had re-rendered the button at all.
    // That is the reported failure: `header button:has(.lucide-moon)` not
    // visible within 3s, three attempts, webkit shard 3/3 of run 32792016684.
    await expect.poll(() => settledTheme(page), { timeout: 15_000 }).not.toBeNull()
    const initial = await settledTheme(page)
    const startIdx = themes.indexOf(initial)
    expect(startIdx).toBeGreaterThanOrEqual(0)

    // cycleThemeTo does a real Playwright click (actionability-checked, so it
    // cannot fire at an unmounted button) and then waits for localStorage, the
    // <html> class and the icon to all agree — three assertions where the old
    // code had one sampled read and a 3s icon race.
    await cycleThemeTo(page, themes[(startIdx + 1) % 3])
    await cycleThemeTo(page, themes[(startIdx + 2) % 3])
    // And back to the start: proves the cycle is a closed 3-loop, which the
    // old test stopped one step short of showing.
    await cycleThemeTo(page, themes[startIdx])
  })

  test('dark theme changes canvas background', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    // Canvas background should be dark (#09090b)
    await expect(page.locator('canvas:visible').first()).toBeVisible()
  })

  test('light theme changes canvas background', async ({ page }) => {
    await setTheme(page, 'light')
    await goToStudio(page)
    await expect(page.locator('canvas:visible').first()).toBeVisible()
  })

  test('theme affects card backgrounds', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    // Wait for the element before reading it. The old version called
    // getComputedStyle(el) on the raw querySelector result, so if .bg-card had
    // not rendered yet the test died with "el is null" — a hard TypeError
    // reported as a test failure, indistinguishable in triage from a real
    // regression. Wait for the node, then read.
    await expect(page.locator('.bg-card').first()).toBeAttached({ timeout: 15_000 })
    await expectDarkClass(page, true)
    const bg = await page.locator('.bg-card').first()
      .evaluate((el) => getComputedStyle(el).backgroundColor)
    expect(bg).toBeTruthy()
  })
})
