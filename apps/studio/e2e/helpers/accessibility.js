import AxeBuilder from '@axe-core/playwright'

/**
 * Run axe accessibility audit on the page.
 * @param {import('@playwright/test').Page} page
 * @param {string[]} [disableRules] - Rules to disable
 * @returns {Promise<import('axe-core').AxeResults>}
 */
export async function runAxeAudit(page, disableRules = []) {
  const results = await new AxeBuilder({ page })
    .disableRules(disableRules)
    .analyze()
  return results
}

/**
 * Assert zero accessibility violations.
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test').Expect} expect
 * @param {string[]} [disableRules]
 */
export async function expectNoA11yViolations(page, expect, disableRules = []) {
  const results = await runAxeAudit(page, disableRules)
  expect(results.violations).toEqual([])
}
