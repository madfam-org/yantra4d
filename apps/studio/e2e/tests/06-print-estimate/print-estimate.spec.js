import { test, expect } from '../../fixtures/app.fixture.js'
import { goToStudio, setLanguage } from '../../helpers/test-utils.js'

// PrintEstimateOverlay only computes an estimate when volumeMm3 > 0 and a
// bounding box exists (see the `estimate` useMemo in
// src/components/export/PrintEstimateOverlay.tsx), so none of its fields exist
// in the DOM until a render has produced geometry.
//
// Most of this file used to assert `expect(page.locator('canvas')).toBeVisible()`
// under names like "overlay displays weight field" and "material dropdown
// includes PLA/PETG/ABS/TPU" — eight different tests all checking the same
// thing, none of them the thing they were named for. Two more asserted
// `expect(true).toBe(true)`. They failed on a strict-mode violation because the
// Studio renders more than one canvas, and making that locator specific would
// only have converted a loud failure into a quiet pretence.
//
// What can be checked without a render is checked. What cannot is marked
// test.fixme with the reason, so the gap stays visible instead of being
// papered over by an assertion that always holds.
test.describe('Print Estimate Overlay', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await goToStudio(page)
  })

  test('overlay is hidden when no render has been done', async ({ viewer }) => {
    const overlay = viewer.printEstimate()
    await expect(overlay).not.toBeVisible()
  })

  test('material select is absent before any geometry exists', async ({ viewer }) => {
    await expect(viewer.materialSelect()).toHaveCount(0)
  })

  test('infill select is absent before any geometry exists', async ({ viewer }) => {
    await expect(viewer.infillSelect()).toHaveCount(0)
  })

  // Everything below needs a completed render on the mock 'test' project, which
  // goToStudio does not produce. Implementing these means driving a render and
  // waiting for geometry stats, then asserting the individual field — not
  // asserting that a canvas exists.
  test.fixme('overlay displays print time field', async () => {})
  test.fixme('overlay displays weight field', async () => {})
  test.fixme('overlay displays filament length field', async () => {})
  test.fixme('overlay displays cost field', async () => {})
  test.fixme('material dropdown includes PLA/PETG/ABS/TPU', async () => {})
  test.fixme('infill dropdown has expected options', async () => {})
})
