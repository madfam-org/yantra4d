/* global Buffer */
import { test, expect } from '../../fixtures/app.fixture.js'
import { setLanguage } from '../../helpers/test-utils.js'

// Skipped: OnboardingWizard route (#/onboard) is not integrated into the app's
// routing system. The component is lazy-imported but never rendered.
test.describe.skip('Onboarding Wizard', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await page.goto('/#/onboard')
    await page.waitForSelector('header')
  })

  // Step 0: Upload
  test('step 0 shows upload title', async ({ page }) => {
    await expect(page.locator('text=Upload SCAD Files')).toBeVisible()
  })

  test('slug input is visible with default value', async ({ onboarding }) => {
    await expect(onboarding.slugInput).toBeVisible()
    const val = await onboarding.slugInput.inputValue()
    expect(val).toBe('new-project')
  })

  test('slug input sanitizes special characters', async ({ onboarding }) => {
    await onboarding.slugInput.fill('')
    await onboarding.slugInput.type('My Project! @#$')
    const val = await onboarding.slugInput.inputValue()
    expect(val).not.toContain(' ')
    expect(val).not.toContain('!')
    expect(val).not.toContain('@')
  })

  test('drop zone is visible', async ({ onboarding }) => {
    await expect(onboarding.dropZone).toBeVisible()
  })

  test('analyze button is disabled without files', async ({ onboarding }) => {
    expect(await onboarding.analyzeButton.isDisabled()).toBe(true)
  })

  test('browse link is visible', async ({ page }) => {
    await expect(page.locator('text=Browse files')).toBeVisible()
  })

  test('step indicator shows Upload as active', async ({ onboarding }) => {
    const step = await onboarding.getCurrentStep()
    expect(step).toBe(0)
  })

  // Step navigation with mocked analysis
  test('analyze triggers API and advances to step 1', async ({ page, onboarding }) => {
    // Mock the analyze API
    await page.route('**/api/projects/analyze', (route) => {
      route.fulfill({
        json: {
          analysis: {
            files: {
              'test.scad': { variables: ['a', 'b'], modules: ['mod1'], includes: [], render_modes: ['single'] },
            },
          },
          manifest: {
            project: { name: 'Test', slug: 'test', version: '0.1.0' },
            modes: [{ id: 'single', label: 'Single' }],
            parameters: [],
          },
          warnings: ['No render_mode variable found'],
        },
      })
    })

    // Upload a fake file via the hidden input
    const fileInput = page.locator('#scad-upload')
    await fileInput.setInputFiles({
      name: 'test.scad',
      mimeType: 'text/plain',
      buffer: Buffer.from('cube(10);'),
    })

    await onboarding.analyzeButton.click()
    await expect(page.locator('text=Analysis Results')).toBeVisible()
  })

  test('step 1 shows file analysis cards', async ({ page, onboarding }) => {
    await page.route('**/api/projects/analyze', (route) => {
      route.fulfill({
        json: {
          analysis: { files: { 'test.scad': { variables: [], modules: [], includes: [], render_modes: [] } } },
          manifest: { project: { name: 'Test', slug: 'test', version: '0.1.0' }, modes: [], parameters: [] },
          warnings: [],
        },
      })
    })

    await page.locator('#scad-upload').setInputFiles({
      name: 'test.scad', mimeType: 'text/plain', buffer: Buffer.from('cube(10);'),
    })
    await onboarding.analyzeButton.click()
    await expect(page.locator('.font-mono', { hasText: 'test.scad' })).toBeVisible()
  })

  test('step 1 shows warnings when present', async ({ page, onboarding }) => {
    await page.route('**/api/projects/analyze', (route) => {
      route.fulfill({
        json: {
          analysis: { files: { 'test.scad': { variables: [], modules: [], includes: [], render_modes: [] } } },
          manifest: { project: { name: 'Test', slug: 'test', version: '0.1.0' }, modes: [], parameters: [] },
          warnings: ['Missing render_mode variable'],
        },
      })
    })

    await page.locator('#scad-upload').setInputFiles({
      name: 'test.scad', mimeType: 'text/plain', buffer: Buffer.from('cube(10);'),
    })
    await onboarding.analyzeButton.click()
    await expect(page.locator('text=Warnings')).toBeVisible()
  })

  // Step 2: Edit manifest
  test('step 2 shows manifest JSON editor', async ({ page }) => {
    // Fast-forward to step 2 by mocking and clicking through
    await page.route('**/api/projects/analyze', (route) => {
      route.fulfill({
        json: {
          analysis: { files: { 'test.scad': { variables: [], modules: [], includes: [], render_modes: [] } } },
          manifest: { project: { name: 'Test', slug: 'test', version: '0.1.0' }, modes: [], parameters: [] },
          warnings: [],
        },
      })
    })

    await page.locator('#scad-upload').setInputFiles({
      name: 'test.scad', mimeType: 'text/plain', buffer: Buffer.from('cube(10);'),
    })
    await page.locator('button', { hasText: 'Analyze Files' }).click()
    await page.locator('button', { hasText: 'Edit Manifest' }).click()
    await expect(page.locator('textarea')).toBeVisible()
  })

  test('step 2 shows validation error for invalid JSON', async ({ page }) => {
    await page.route('**/api/projects/analyze', (route) => {
      route.fulfill({
        json: {
          analysis: { files: { 'test.scad': { variables: [], modules: [], includes: [], render_modes: [] } } },
          manifest: { project: { name: 'Test', slug: 'test', version: '0.1.0' }, modes: [], parameters: [] },
          warnings: [],
        },
      })
    })

    await page.locator('#scad-upload').setInputFiles({
      name: 'test.scad', mimeType: 'text/plain', buffer: Buffer.from('cube(10);'),
    })
    await page.locator('button', { hasText: 'Analyze Files' }).click()
    await page.locator('button', { hasText: 'Edit Manifest' }).click()

    const textarea = page.locator('textarea')
    await textarea.fill('{invalid json')
    await expect(page.locator('text=Invalid JSON')).toBeVisible()
  })

  // Step 3: Save
  test('step 3 shows save summary and create button', async ({ page }) => {
    await page.route('**/api/projects/analyze', (route) => {
      route.fulfill({
        json: {
          analysis: { files: { 'test.scad': { variables: [], modules: [], includes: [], render_modes: [] } } },
          manifest: { project: { name: 'Test', slug: 'test', version: '0.1.0' }, modes: [{ id: 's' }], parameters: [{ id: 'a' }] },
          warnings: [],
        },
      })
    })

    await page.locator('#scad-upload').setInputFiles({
      name: 'test.scad', mimeType: 'text/plain', buffer: Buffer.from('cube(10);'),
    })
    await page.locator('button', { hasText: 'Analyze Files' }).click()
    await page.locator('button', { hasText: 'Edit Manifest' }).click()
    await page.locator('button', { hasText: 'Review & Save' }).click()
    await expect(page.locator('text=Save Project')).toBeVisible()
    await expect(page.locator('button', { hasText: 'Create Project' })).toBeVisible()
  })

  // Back navigation
  test('back button navigates to previous step', async ({ page }) => {
    await page.route('**/api/projects/analyze', (route) => {
      route.fulfill({
        json: {
          analysis: { files: { 'test.scad': { variables: [], modules: [], includes: [], render_modes: [] } } },
          manifest: { project: { name: 'Test', slug: 'test', version: '0.1.0' }, modes: [], parameters: [] },
          warnings: [],
        },
      })
    })

    await page.locator('#scad-upload').setInputFiles({
      name: 'test.scad', mimeType: 'text/plain', buffer: Buffer.from('cube(10);'),
    })
    await page.locator('button', { hasText: 'Analyze Files' }).click()
    await expect(page.locator('text=Analysis Results')).toBeVisible()

    await page.locator('button', { hasText: 'Back' }).click()
    await expect(page.locator('text=Upload SCAD Files')).toBeVisible()
  })
})
