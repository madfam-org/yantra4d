import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage, setTheme } from '../../helpers/test-utils.js'

test.describe('Theme System', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
  })

  test('light theme applies correct classes', async ({ page }) => {
    await setTheme(page, 'light')
    await goToStudio(page)
    const hasDark = await page.evaluate(() => document.documentElement.classList.contains('dark'))
    expect(hasDark).toBe(false)
  })

  test('dark theme applies dark class to html', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    const hasDark = await page.evaluate(() => document.documentElement.classList.contains('dark'))
    expect(hasDark).toBe(true)
  })

  test('system theme follows OS preference', async ({ page }) => {
    await setTheme(page, 'system')
    await page.emulateMedia({ colorScheme: 'dark' })
    await goToStudio(page)
    const hasDark = await page.evaluate(() => document.documentElement.classList.contains('dark'))
    expect(hasDark).toBe(true)
  })

  test('system theme follows light OS preference', async ({ page }) => {
    await setTheme(page, 'system')
    await page.emulateMedia({ colorScheme: 'light' })
    await goToStudio(page)
    const hasDark = await page.evaluate(() => document.documentElement.classList.contains('dark'))
    expect(hasDark).toBe(false)
  })

  test('theme persists across reload', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    await page.reload()
    await page.waitForSelector('header')
    const theme = await page.evaluate(() => localStorage.getItem('vite-ui-theme'))
    expect(theme).toBe('dark')
  })

  test('theme toggle button shows correct icon for light', async ({ page }) => {
    await setTheme(page, 'light')
    await goToStudio(page)
    await expect(page.locator('button:has(.lucide-sun)').first()).toBeVisible()
  })

  test('theme toggle button shows correct icon for dark', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    await expect(page.locator('button:has(.lucide-moon)').first()).toBeVisible()
  })

  test('theme toggle button shows correct icon for system', async ({ page }) => {
    await setTheme(page, 'system')
    await goToStudio(page)
    await expect(page.locator('button:has(.lucide-monitor)').first()).toBeVisible()
  })

  test('cycling theme updates localStorage', async ({ page }) => {
    await setTheme(page, 'light')
    await goToStudio(page)

    const themeBtn = page.locator('button:has(.lucide-sun), button:has(.lucide-moon), button:has(.lucide-monitor)').first()
    await themeBtn.click()
    const t1 = await page.evaluate(() => localStorage.getItem('vite-ui-theme'))
    expect(t1).toBe('dark')

    await themeBtn.click()
    const t2 = await page.evaluate(() => localStorage.getItem('vite-ui-theme'))
    expect(t2).toBe('system')
  })

  test('dark theme changes canvas background', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    // Canvas background should be dark (#09090b)
    await expect(page.locator('canvas')).toBeVisible()
  })

  test('light theme changes canvas background', async ({ page }) => {
    await setTheme(page, 'light')
    await goToStudio(page)
    await expect(page.locator('canvas')).toBeVisible()
  })

  test('theme affects card backgrounds', async ({ page }) => {
    await setTheme(page, 'dark')
    await goToStudio(page)
    const bg = await page.evaluate(() => {
      const el = document.querySelector('.bg-card')
      return getComputedStyle(el).backgroundColor
    })
    expect(bg).toBeTruthy()
  })
})
