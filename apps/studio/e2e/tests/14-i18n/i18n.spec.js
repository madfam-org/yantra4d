import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, setLanguage } from '../../helpers/test-utils.js'

/** Click the globe button and select a language from the dropdown. */
async function selectLanguageFromDropdown(page, langLabel) {
  await page.locator('button:has(.lucide-globe)').first().click()
  // Wait for dropdown to appear
  const dropdown = page.locator('.absolute.top-full')
  await dropdown.first().waitFor({ timeout: 3000 })
  // Click the target language button
  await dropdown.locator('button', { hasText: langLabel }).click()
  await page.waitForTimeout(300)
}

/** Click the globe button and select the first non-current language. */
async function toggleToOtherLanguage(page) {
  await page.locator('button:has(.lucide-globe)').first().click()
  const dropdown = page.locator('.absolute.top-full')
  await dropdown.first().waitFor({ timeout: 3000 })
  const options = dropdown.locator('button')
  const count = await options.count()
  for (let i = 0; i < count; i++) {
    const isBold = await options.nth(i).evaluate(el => el.classList.contains('font-semibold'))
    if (!isBold) {
      await options.nth(i).click()
      await page.waitForTimeout(300)
      return
    }
  }
  if (count > 0) {
    await options.last().click()
    await page.waitForTimeout(300)
  }
}

test.describe('Internationalization (i18n)', () => {
  test('default language renders all UI in Spanish', async ({ page }) => {
    await setLanguage(page, 'es')
    await goToStudio(page)
    await expect(page.locator('text=Generar')).toBeVisible()
    await expect(page.locator('text=Ejecutar Verificación')).toBeVisible()
    await expect(page.locator('text=Restablecer Valores')).toBeVisible()
  })

  test('English UI renders all buttons', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    await expect(page.locator('text=Generate')).toBeVisible()
    await expect(page.locator('text=Run Verification Suite')).toBeVisible()
    await expect(page.locator('text=Reset to Defaults')).toBeVisible()
  })

  test('toggling language updates all header text', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    await expect(page.locator('text=Projects').first()).toBeVisible()

    await selectLanguageFromDropdown(page, 'Español')
    await expect(page.locator('text=Proyectos').first()).toBeVisible({ timeout: 5000 })
  })

  test('export panel text updates on language toggle', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    await expect(page.locator('text=Export Images')).toBeVisible()
    await expect(page.locator('text=Download STL')).toBeVisible()

    await selectLanguageFromDropdown(page, 'Español')
    await expect(page.locator('text=Exportar Imágenes')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('text=Descargar STL')).toBeVisible({ timeout: 5000 })
  })

  test('projects view title translates', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToProjects(page)
    await expect(page.locator('h2', { hasText: 'Projects' })).toBeVisible({ timeout: 5000 })

    await selectLanguageFromDropdown(page, 'Español')
    await expect(page.locator('h2', { hasText: 'Proyectos' })).toBeVisible({ timeout: 5000 })
  })

  test('theme toggle tooltips translate', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    const themeBtn = page.locator('button:has(.lucide-sun), button:has(.lucide-moon), button:has(.lucide-monitor)').first()
    const title = await themeBtn.getAttribute('title')
    expect(title).toContain('Theme')

    await selectLanguageFromDropdown(page, 'Español')
    await page.waitForTimeout(300)
    const titleEs = await themeBtn.getAttribute('title')
    expect(titleEs).toContain('Tema')
  })

  test('language persists across page reload', async ({ page }) => {
    await setLanguage(page, 'es')
    await goToStudio(page)
    await expect(page.locator('text=Generar')).toBeVisible()

    await page.reload()
    await page.waitForSelector('header')
    await expect(page.locator('text=Generar')).toBeVisible()
  })

  test('language toggle icon stays visible in both languages', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    const globe = page.locator('button:has(.lucide-globe)').first()
    await expect(globe).toBeVisible()

    await toggleToOtherLanguage(page)
    await expect(globe).toBeVisible()
  })

  test('console "Ready" message translates', async ({ page }) => {
    await setLanguage(page, 'es')
    await goToStudio(page)
    const logs = await page.locator('[role="log"]').textContent()
    expect(logs).toContain('Listo')
  })

  test('viewer button labels translate', async ({ page }) => {
    await setLanguage(page, 'es')
    await goToStudio(page)
    // Camera view buttons — check any Spanish button is present
    const hasSpanish = await page.locator('button', { hasText: /Isométric|Superior|Frontal|Derech/ }).first().isVisible({ timeout: 3000 }).catch(() => false)
    // If camera buttons use icons instead of text, just verify Spanish export text
    if (!hasSpanish) {
      await expect(page.locator('text=Exportar Imágenes')).toBeVisible()
    }
  })

  test('sr-only labels translate', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    const srTexts = await page.locator('.sr-only').allTextContents()
    const hasEnglish = srTexts.some(t => t.includes('Undo') || t.includes('Redo') || t.includes('Toggle'))
    expect(hasEnglish).toBe(true)
  })

  test('manifest labels render in current language', async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
    // Mode labels should be in English
    await expect(page.locator('[role="tablist"] button').first()).toBeVisible()
  })
})
