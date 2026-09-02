/**
 * E2E: the render placement indicator and control.
 *
 * The studio renders in the visitor's browser by default — free for us,
 * unmetered for them — and only hands work to the server when something says
 * the browser cannot do it. These tests assert the two things a visitor can
 * actually see: which placement is in force, and their ability to change it.
 *
 * DETERMINISM. Two things would otherwise make this a test of the CI runner
 * rather than of the app:
 *
 *   1. `navigator.hardwareConcurrency` / `deviceMemory` differ per runner, and
 *      they feed the capability tier.
 *   2. The capability probe instantiates a real 13 MB OpenSCAD WASM module on
 *      first need. On a runner where that fails, the probe correctly records
 *      `incapable` — correct, but not what these tests are about.
 *
 * So each test seeds the versioned capability record in localStorage before the
 * app loads. That is the same record a real probe writes, so nothing is faked
 * beyond skipping the measurement.
 */

import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage } from '../../helpers/test-utils.js'

const CAPABILITY_KEY = 'y4d.render_capability.v1'
const PREFERENCE_KEY = 'y4d.render_placement_preference.v1'

/** Seed a capability record so the probe is skipped and the tier is known. */
async function seedCapability(page, tier, benchmarkMs = 120) {
  await page.addInitScript(([key, t, ms]) => {
    try {
      localStorage.setItem(key, JSON.stringify({
        version: 1,
        tier: t,
        benchmarkMs: ms,
        at: Date.now(),
        signals: {
          wasm: true, simd: true, cores: 8, memoryGb: 8, mobile: false,
          crossOriginIsolated: false, saveData: false, reducedData: false,
        },
      }))
    } catch { /* storage disabled — the app copes, and so does this test */ }
  }, [CAPABILITY_KEY, tier, benchmarkMs])
}

/** Seed the visitor's stored placement preference. */
async function seedPreference(page, preference) {
  await page.addInitScript(([key, value]) => {
    try { localStorage.setItem(key, value) } catch { /* see seedCapability */ }
  }, [PREFERENCE_KEY, preference])
}

/**
 * Answer GET /api/projects/<slug>/wasm-bundle.
 *
 * `unsupported` is what makes a cartridge server-only under rule 3, but the
 * indicator only learns about it once a render has actually fetched the bundle
 * — and this environment ships no WASM binary, so no browser render completes
 * here. Rule 3 is covered exhaustively in renderPlacement.test.js instead.
 */
async function mockBundle(page, { unsupported = [] } = {}) {
  await page.route('**/api/projects/*/wasm-bundle', (route) => {
    const slug = new URL(route.request().url()).pathname.split('/').at(-2)
    route.fulfill({
      json: {
        slug,
        engine: 'openscad',
        entry_files: ['test.scad'],
        files: { [`projects/${slug}/test.scad`]: 'cube(10);' },
        fonts: {},
        unsupported,
        bytes: 10,
        etag: 'e2e',
      },
    })
  })
}

const placement = (page) => page.getByTestId('render-placement')
const badge = (page) => page.getByTestId('render-placement-badge')
const control = (page) => page.getByTestId('render-placement-select')
const reason = (page) => page.getByTestId('render-placement-reason')

test.describe('Render placement indicator', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await mockBundle(page)
  })

  test('a capable device renders in the browser, and says the render is free', async ({ page }) => {
    await seedCapability(page, 'capable')
    await goToStudio(page)

    await expect(placement(page)).toBeVisible()
    await expect(placement(page)).toHaveAttribute('data-placement', 'browser')
    await expect(badge(page)).toHaveText('Rendering in your browser (free)')
  })

  test('the browser badge never shows a rate-limit quota', async ({ page }) => {
    // A browser render consumes no quota. Showing a number next to it would
    // teach the visitor that everything they do here is metered.
    await seedCapability(page, 'capable')
    await goToStudio(page)

    await expect(badge(page)).toHaveText('Rendering in your browser (free)')
    await expect(badge(page)).not.toContainText('left this hour')
  })

  test('an incapable device is routed to the server, with a reason', async ({ page }) => {
    await seedCapability(page, 'incapable', 9000)
    await goToStudio(page)

    await expect(placement(page)).toHaveAttribute('data-placement', 'server')
    await expect(badge(page)).toContainText('Rendering on our server')
    await expect(reason(page)).toHaveText('This device is too limited for browser rendering.')
  })

  test('?render=backend still pins the server', async ({ page }) => {
    await seedCapability(page, 'capable')
    await page.goto('/project/test?render=backend')
    await expect(placement(page)).toHaveAttribute('data-placement', 'server')
    await expect(reason(page)).toHaveText('Pinned to the server by a support link.')
  })

  test('?render=wasm still pins the browser, even on an incapable device', async ({ page }) => {
    await seedCapability(page, 'incapable', 9000)
    await page.goto('/project/test?render=wasm')
    await expect(placement(page)).toHaveAttribute('data-placement', 'browser')
    await expect(reason(page)).toHaveText('Pinned to the browser by a support link.')
  })
})

test.describe('Render placement control', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await mockBundle(page)
    await seedCapability(page, 'capable')
  })

  test('offers Auto, Browser and Server', async ({ page }) => {
    await goToStudio(page)

    await control(page).click()
    const listbox = page.getByRole('listbox')
    await expect(listbox.getByRole('option', { name: 'Auto' })).toBeVisible()
    await expect(listbox.getByRole('option', { name: 'Browser' })).toBeVisible()
    await expect(listbox.getByRole('option', { name: 'Server' })).toBeVisible()
  })

  test('choosing Server moves the render to the server and explains why', async ({ page }) => {
    await goToStudio(page)
    await expect(placement(page)).toHaveAttribute('data-placement', 'browser')

    await control(page).click()
    await page.getByRole('option', { name: 'Server' }).click()

    await expect(placement(page)).toHaveAttribute('data-placement', 'server')
    await expect(reason(page)).toHaveText('You chose server rendering.')
  })

  test('the choice survives a reload', async ({ page }) => {
    await goToStudio(page)
    await control(page).click()
    await page.getByRole('option', { name: 'Server' }).click()
    await expect(placement(page)).toHaveAttribute('data-placement', 'server')

    await page.reload()
    await expect(placement(page)).toHaveAttribute('data-placement', 'server')
  })

  test('a stored Browser preference beats an incapable device', async ({ page }) => {
    // Rule 6 sits above rule 7: if the visitor insists, they get what they asked
    // for rather than a silent charge against their server quota.
    await seedCapability(page, 'incapable', 9000)
    await seedPreference(page, 'browser')
    await goToStudio(page)

    await expect(placement(page)).toHaveAttribute('data-placement', 'browser')
    await expect(reason(page)).toHaveText('You chose browser rendering.')
  })
})
