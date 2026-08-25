import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, goToProjects, setLanguage, setTheme } from '../../helpers/test-utils.js'

// Skipped until baselines exist. Every one of these 19 tests fails on every
// browser with:
//
//   A snapshot doesn't exist at .../studio-light-chromium-linux.png,
//   writing actual.
//
// The -snapshots directory is empty and nothing is gitignored — baseline PNGs
// have simply never been committed, so the suite has never been capable of
// passing in CI. That was 57 of the suite's 228 failures, a quarter of the
// total, permanently red and drowning out the failures that can be fixed.
//
// To re-enable: generate baselines on the CI platform, not a developer machine.
// Playwright names them per platform (chromium-linux), and screenshots taken on
// macOS will differ on font rendering and antialiasing alone. Run
// `npx playwright test 18-visual-regression --update-snapshots` in a
// mcr.microsoft.com/playwright container matching the CI image, commit the
// PNGs, then drop the .skip here.
test.describe.skip('Visual Regression', () => {
  // Studio view baselines
  test('studio view — light theme', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToStudio(page)
    await page.waitForTimeout(1000)
    await expect(page).toHaveScreenshot('studio-light.png', {
      maxDiffPixelRatio: 0.05,
      animations: 'disabled',
    })
  })

  test('studio view — dark theme', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'dark')
    await goToStudio(page)
    await page.waitForTimeout(1000)
    await expect(page).toHaveScreenshot('studio-dark.png', {
      maxDiffPixelRatio: 0.05,
      animations: 'disabled',
    })
  })

  // Projects view baselines
  test('projects view — light theme', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToProjects(page)
    await page.waitForTimeout(1000)
    await expect(page).toHaveScreenshot('projects-light.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('projects view — dark theme', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'dark')
    await goToProjects(page)
    await page.waitForTimeout(1000)
    await expect(page).toHaveScreenshot('projects-dark.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  // Spanish locale baselines
  test('studio view — Spanish', async ({ page }) => {
    await setLanguage(page, 'es')
    await setTheme(page, 'light')
    await goToStudio(page)
    await page.waitForTimeout(1000)
    await expect(page).toHaveScreenshot('studio-es.png', {
      maxDiffPixelRatio: 0.05,
      animations: 'disabled',
    })
  })

  test('projects view — Spanish', async ({ page }) => {
    await setLanguage(page, 'es')
    await setTheme(page, 'light')
    await goToProjects(page)
    await page.waitForTimeout(1000)
    await expect(page).toHaveScreenshot('projects-es.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  // Component snapshots
  test('header component', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToStudio(page)
    await page.waitForTimeout(500)
    const header = page.locator('header').first()
    await expect(header).toHaveScreenshot('header.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('header component — dark', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'dark')
    await goToStudio(page)
    await page.waitForTimeout(500)
    const header = page.locator('header').first()
    await expect(header).toHaveScreenshot('header-dark.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('sidebar component', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToStudio(page)
    await page.waitForTimeout(500)
    const sidebar = page.locator('[data-testid="studio-sidebar"]').first()
    await expect(sidebar).toHaveScreenshot('sidebar.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('sidebar component — dark', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'dark')
    await goToStudio(page)
    await page.waitForTimeout(500)
    const sidebar = page.locator('[data-testid="studio-sidebar"]').first()
    await expect(sidebar).toHaveScreenshot('sidebar-dark.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('export panel component', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToStudio(page)
    await page.waitForTimeout(500)
    const exportPanel = page.getByTestId('export-panel')
    await expect(exportPanel).toHaveScreenshot('export-panel.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('mode tabs component', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToStudio(page)
    await page.waitForTimeout(500)
    const tabs = page.locator('[role="tablist"]').first()
    await expect(tabs).toHaveScreenshot('mode-tabs.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('camera view buttons', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToStudio(page)
    await page.waitForTimeout(500)
    const viewBtns = page.locator('.absolute.top-2.right-2')
    await expect(viewBtns).toHaveScreenshot('camera-views.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('project card component', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToProjects(page)
    await page.waitForTimeout(500)
    const card = page.getByTestId('project-row').first()
    await expect(card).toHaveScreenshot('project-card.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('project card — dark theme', async ({ page }) => {
    await setLanguage(page, 'en')
    await setTheme(page, 'dark')
    await goToProjects(page)
    await page.waitForTimeout(500)
    const card = page.getByTestId('project-row').first()
    await expect(card).toHaveScreenshot('project-card-dark.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  // Mobile snapshots
  test('studio mobile view', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToStudio(page)
    await page.waitForTimeout(1000)
    await expect(page).toHaveScreenshot('studio-mobile.png', {
      maxDiffPixelRatio: 0.05,
      animations: 'disabled',
    })
  })

  test('projects mobile view', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToProjects(page)
    await page.waitForTimeout(1000)
    await expect(page).toHaveScreenshot('projects-mobile.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  // Empty/error state snapshots
  test('empty projects view', async ({ page }) => {
    await page.route('**/api/admin/projects', (route) => route.fulfill({ json: [] }))
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToProjects(page)
    await page.waitForTimeout(500)
    await expect(page).toHaveScreenshot('projects-empty.png', {
      maxDiffPixelRatio: 0.05,
    })
  })

  test('error projects view', async ({ page }) => {
    await page.route('**/api/admin/projects', (route) => {
      route.fulfill({ status: 500, json: { error: 'Error' } })
    })
    await setLanguage(page, 'en')
    await setTheme(page, 'light')
    await goToProjects(page)
    await page.waitForTimeout(500)
    await expect(page).toHaveScreenshot('projects-error.png', {
      maxDiffPixelRatio: 0.05,
    })
  })
})
