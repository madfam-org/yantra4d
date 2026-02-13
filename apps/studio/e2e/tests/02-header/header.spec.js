import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage } from '../../helpers/test-utils.js'

test.describe('Studio Header', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
  })

  test('displays project name from manifest', async ({ header }) => {
    await expect(header.projectName).toBeVisible()
    const name = await header.getProjectName()
    expect(name).toContain('Test Project')
  })

  test('shows "powered by Yantra4D" tagline', async ({ page }) => {
    await expect(page.locator('text=powered by Yantra4D')).toBeVisible()
  })

  test('ProjectSelector is visible when multiple projects exist', async ({ header }) => {
    await expect(header.projectSelector).toBeVisible()
  })

  test('ProjectSelector switches project', async ({ page, header }) => {
    await header.selectProject('demo')
    await page.waitForTimeout(1000)
    await expect(page.locator('header')).toBeVisible()
  })

  test('Projects link navigates to projects view', async ({ page, header }) => {
    await header.projectsLink.click()
    await page.waitForTimeout(500)
    const hash = await page.evaluate(() => window.location.hash)
    expect(hash).toBe('#/projects')
  })

  test('undo reverts parameter change', async ({ header, sidebar }) => {
    await expect(sidebar.slider('width')).toBeVisible({ timeout: 5000 })
    const valueBefore = await sidebar.sliderValue('width').textContent()
    const targetValue = Number(valueBefore) === 100 ? 150 : 100
    await sidebar.editSliderValue('width', targetValue)
    await expect(sidebar.sliderValue('width')).toHaveText(String(targetValue), { timeout: 2000 })

    // Check/Wait for undo button to be active
    const undoBtn = header.undoButton || header.header.locator('button[title="Undo"], button[title="Deshacer"]')
    await expect(undoBtn).toBeEnabled({ timeout: 5000 })

    await header.clickUndo()
    await expect(sidebar.sliderValue('width')).toHaveText(valueBefore, { timeout: 3000 })
  })

  test('redo restores undone change', async ({ header, sidebar }) => {
    await expect(sidebar.slider('width')).toBeVisible({ timeout: 5000 })
    const valueBefore = await sidebar.sliderValue('width').textContent()
    const targetValue = Number(valueBefore) === 100 ? 150 : 100
    await sidebar.editSliderValue('width', targetValue)
    await expect(sidebar.sliderValue('width')).toHaveText(String(targetValue), { timeout: 3000 })

    await header.clickUndo()
    await expect(sidebar.sliderValue('width')).toHaveText(valueBefore, { timeout: 3000 })

    expect(await header.isRedoDisabled()).toBe(false)
    await header.clickRedo()
    await expect(sidebar.sliderValue('width')).toHaveText(String(targetValue), { timeout: 3000 })
  })

  test('share button copies URL to clipboard', async ({ page, header }) => {
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    await header.clickShare()
    // Toast may appear as inline tooltip or via sonner
    const toast = page.getByText('Link copied!').or(page.getByText('¡Enlace copiado!'))
    await expect(toast.first()).toBeVisible({ timeout: 5000 })
  })

  test('share toast disappears after a delay', async ({ page, header }) => {
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    await header.clickShare()
    // Wait for any toast to appear (inline tooltip or sonner)
    const toast = page.getByText('Link copied!').or(page.getByText('¡Enlace copiado!'))
    await expect(toast.first()).toBeVisible({ timeout: 5000 })
    // Both inline tooltip (2s) and sonner toast (2s) auto-hide
    // Wait for ALL instances to disappear
    await expect(toast.first()).not.toBeVisible({ timeout: 8000 })
  })

  test('language toggle switches EN→ES', async ({ page, header }) => {
    await expect(page.locator('text=Generate')).toBeVisible({ timeout: 5000 })
    await header.toggleLanguage()
    await page.waitForTimeout(500)
    await expect(page.locator('text=Generar')).toBeVisible({ timeout: 5000 })
  })

  test('language toggle switches ES→EN', async ({ page, header }) => {
    await header.toggleLanguage() // to ES
    await page.waitForTimeout(500)
    await expect(page.getByRole('button', { name: 'Generar' })).toBeVisible({ timeout: 5000 })
    await header.toggleLanguage() // back to EN
    await page.waitForTimeout(500)
    await expect(page.getByRole('button', { name: 'Generate' })).toBeVisible({ timeout: 5000 })
  })

  test('language persists to localStorage', async ({ page, header }) => {
    await header.toggleLanguage()
    const lang = await page.evaluate(() =>
      localStorage.getItem('yantra4d-lang') ||
      localStorage.getItem('test-lang') ||
      localStorage.getItem('gridfinity-lang')
    )
    expect(['en', 'es']).toContain(lang)
  })

  test('theme toggle cycles light→dark→system', async ({ page }) => {
    // Set theme directly via localStorage and reload
    await page.evaluate(() => localStorage.setItem('vite-ui-theme', 'light'))
    await page.reload()
    // Wait for app to fully hydrate
    await expect(page.locator('[role="tab"]').first()).toBeVisible({ timeout: 8000 })

    // Dispatch click via JS to avoid Playwright click intermittency after reload
    const clickThemeButton = async () => {
      await page.evaluate(() => {
        const btn = document.querySelector('header button[title^="Theme:"]')
          || document.querySelector('header button[title^="Tema:"]')
        if (btn) btn.click()
      })
    }

    const getTheme = () => page.evaluate(() => localStorage.getItem('vite-ui-theme'))

    // Cycle light → dark
    await clickThemeButton()
    await expect(async () => expect(await getTheme()).toBe('dark')).toPass({ timeout: 3000 })

    // Cycle dark → system
    await clickThemeButton()
    await expect(async () => expect(await getTheme()).toBe('system')).toPass({ timeout: 3000 })

    // Cycle system → light
    await clickThemeButton()
    await expect(async () => expect(await getTheme()).toBe('light')).toPass({ timeout: 3000 })
  })

  test('theme persists across reload', async ({ page }) => {
    // Set dark theme via UI
    await page.evaluate(() => localStorage.setItem('vite-ui-theme', 'dark'))
    await page.reload()
    await page.waitForSelector('header')
    const theme = await page.evaluate(() => localStorage.getItem('vite-ui-theme'))
    expect(theme).toBe('dark')
  })

  test('dark theme applies dark class to html', async ({ page }) => {
    await page.evaluate(() => localStorage.setItem('vite-ui-theme', 'dark'))
    await page.reload()
    await page.waitForSelector('header')
    const hasDark = await page.evaluate(() => document.documentElement.classList.contains('dark'))
    expect(hasDark).toBe(true)
  })
})
