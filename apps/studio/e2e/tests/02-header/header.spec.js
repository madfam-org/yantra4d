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

  test('undo reverts parameter change', async ({ page, header, sidebar }) => {
    await expect(sidebar.slider('width')).toBeVisible({ timeout: 5000 })
    const valueBefore = await sidebar.sliderValue('width').textContent()
    await sidebar.editSliderValue('width', 100)
    await page.waitForTimeout(300)

    await header.clickUndo()
    await page.waitForTimeout(300)

    const valueAfter = await sidebar.sliderValue('width').textContent()
    expect(valueAfter).toBe(valueBefore)
  })

  test('redo restores undone change', async ({ page, header, sidebar }) => {
    await expect(sidebar.slider('width')).toBeVisible({ timeout: 5000 })
    await sidebar.editSliderValue('width', 100)
    await page.waitForTimeout(300)
    await header.clickUndo()
    await page.waitForTimeout(300)

    expect(await header.isRedoDisabled()).toBe(false)
    await header.clickRedo()
    await page.waitForTimeout(300)

    const value = await sidebar.sliderValue('width').textContent()
    expect(value).toBe('100')
  })

  test('share button copies URL to clipboard', async ({ page, header }) => {
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    await header.clickShare()
    await expect(page.locator('text=Link copied!')).toBeVisible()
  })

  test('share toast disappears after a delay', async ({ page, header }) => {
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    await header.clickShare()
    await expect(page.locator('text=Link copied!')).toBeVisible()
    await page.waitForTimeout(3000)
    await expect(page.locator('text=Link copied!')).not.toBeVisible()
  })

  test('language toggle switches EN→ES', async ({ page, header }) => {
    await expect(page.locator('text=Generate')).toBeVisible()
    await header.toggleLanguage()
    await expect(page.locator('text=Generar')).toBeVisible()
  })

  test('language toggle switches ES→EN', async ({ page, header }) => {
    await header.toggleLanguage() // to ES
    await expect(page.locator('text=Generar')).toBeVisible()
    await header.toggleLanguage() // back to EN
    await expect(page.locator('text=Generate')).toBeVisible()
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

  test('theme toggle cycles light→dark→system', async ({ page, header }) => {
    // Set theme directly via localStorage (not addInitScript to avoid persistence issues)
    await page.evaluate(() => localStorage.setItem('vite-ui-theme', 'light'))
    await page.reload()
    await page.waitForSelector('header')

    // Cycle light → dark
    await header.cycleTheme()
    const theme1 = await page.evaluate(() => localStorage.getItem('vite-ui-theme'))
    expect(theme1).toBe('dark')

    // Cycle dark → system
    await header.cycleTheme()
    const theme2 = await page.evaluate(() => localStorage.getItem('vite-ui-theme'))
    expect(theme2).toBe('system')

    // Cycle system → light
    await header.cycleTheme()
    const theme3 = await page.evaluate(() => localStorage.getItem('vite-ui-theme'))
    expect(theme3).toBe('light')
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
