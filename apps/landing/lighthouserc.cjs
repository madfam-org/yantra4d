/**
 * Lighthouse CI for the landing (`npm run lhci` = `lhci autorun`).
 *
 * Every threshold is derived from perf-budgets.json at load time — the same
 * file the bundle-budget step and the Playwright suite read — so a budget is
 * changed in exactly one place. CommonJS because the package is `type: module`
 * and Lighthouse CI `require()`s its rc file.
 *
 * What runs: the built `dist/`, served by Lighthouse CI's own static server,
 * three URLs, three runs each, Lighthouse's default MOBILE emulation (the
 * budgets' `lcpMs.mobile` and `performanceMobile` are written for it).
 *
 *   /index.html?tier=full     the immersive tier, forced (headless Chrome is
 *                             classified `still` by user agent otherwise)
 *   /index.html               what a crawler / headless agent gets: `still`
 *   /en/index.html?tier=full  the English page, immersive tier
 *
 * Chrome: Lighthouse launches its own. Set CHROME_PATH to pin one; when it is
 * unset, this file points Lighthouse at the Chromium Playwright installed for
 * the e2e suite, so local runs and the runner measure with the same browser
 * build:
 *
 *   export CHROME_PATH="$(node -e "console.log(require('@playwright/test').chromium.executablePath())")"
 *
 * Reading a failure: `lhci assert` prints one block per failed assertion with
 * the URL, the audit id, the expected and the actual value; the full reports
 * are in .lighthouseci/ (uploaded as a CI artifact on failure) — open the
 * `.html` next to the failing `.json` for the waterfall and the audit details.
 */
/* global require, module, process */
/* eslint-disable @typescript-eslint/no-require-imports -- CommonJS by contract: Lighthouse CI require()s this file */
const budgets = require('./perf-budgets.json');

const { vitals, lighthouse } = budgets;
const KIB = 1024;
/** Category scores are 0–1 in assertions, percentages in the budgets file. */
const score = (percent) => percent / 100;

function playwrightChromium() {
  try {
    return require('@playwright/test').chromium.executablePath();
  } catch {
    return undefined; // no Playwright here — let Lighthouse find a Chrome
  }
}

/**
 * The budgets in Lighthouse's budget.json shape, generated from
 * perf-budgets.json: the vitals for the mobile profile Lighthouse emulates.
 *
 * No `resourceSizes` here, on purpose. Lighthouse CI's static server speaks
 * gzip, so every byte figure it observes runs ~10% above the brotli numbers
 * the budgets are written in, and Chrome's lazy-load distance pulls the first
 * grid thumbnails into a "total" that has nothing to do with the initial page.
 * Bytes are gated where they can be measured exactly: the CI bundle step
 * (`npm run budget`, brotli on disk) and the Playwright suite (bodies
 * re-compressed with brotli). Lighthouse owns what it is good at — the
 * category scores and the field-like timings on a throttled mobile profile.
 */
const lighthouseBudgets = [
  {
    path: '/*',
    timings: [
      { metric: 'largest-contentful-paint', budget: vitals.lcpMs.mobile },
      { metric: 'total-blocking-time', budget: vitals.tbtMs },
      { metric: 'cumulative-layout-shift', budget: vitals.cls },
    ],
  },
];

/**
 * Lighthouse CI refuses `budgetsFile` alongside `assertions`, so the budgets
 * are converted here exactly the way @lhci/utils/src/budgets-converter.js
 * does it (resource sizes ×1024, timings as maxNumericValue) and merged into
 * the category assertions. Single `/*` path, so no per-URL matrix is needed.
 */
function budgetAssertions(list) {
  const assertions = {};
  for (const budget of list) {
    for (const { metric, budget: maxNumericValue } of budget.timings || []) {
      assertions[metric] = ['error', { maxNumericValue }];
    }
    for (const { resourceType, budget: maxNumericValue } of budget.resourceSizes || []) {
      assertions[`resource-summary:${resourceType}:size`] = ['error', { maxNumericValue: maxNumericValue * KIB }];
    }
    for (const { resourceType, budget: maxNumericValue } of budget.resourceCounts || []) {
      assertions[`resource-summary:${resourceType}:count`] = ['error', { maxNumericValue }];
    }
  }
  return assertions;
}

module.exports = {
  /** Exposed for tooling and tests; Lighthouse CI itself reads only `ci`. */
  budgets: lighthouseBudgets,
  ci: {
    collect: {
      staticDistDir: './dist',
      url: ['/index.html?tier=full', '/index.html', '/en/index.html?tier=full'],
      numberOfRuns: 3,
      chromePath: process.env.CHROME_PATH || playwrightChromium(),
      settings: {
        // The ARC runner executes the job inside a container, where Chrome's
        // sandbox cannot set itself up; Playwright's launcher already runs
        // without it there. Locally the sandbox stays on.
        //
        // --disable-dev-shm-usage: the container's /dev/shm is tiny, and a
        // full-tier page (WebGL stage on SwiftShader, 4× CPU throttle) crashes
        // the renderer with TARGET_CRASHED ("Browser tab has unexpectedly
        // crashed") when Chrome keeps its shared memory there — seen on the
        // first CI run, 2026-09-19. Playwright passes the same flag by default,
        // which is why the e2e suite never hit it.
        chromeFlags: process.env.CI ? '--no-sandbox --disable-dev-shm-usage' : undefined,
      },
    },
    assert: {
      // The median of the three runs, so one noisy run on the shared runner
      // neither fails nor rescues the gate.
      aggregationMethod: 'median-run',
      assertions: {
        'categories:performance': ['error', { minScore: score(lighthouse.performanceMobile) }],
        'categories:accessibility': ['error', { minScore: score(lighthouse.accessibility) }],
        'categories:best-practices': ['error', { minScore: score(lighthouse.bestPractices) }],
        'categories:seo': ['error', { minScore: score(lighthouse.seo) }],
        ...budgetAssertions(lighthouseBudgets),
      },
    },
    upload: {
      target: 'filesystem',
      outputDir: './.lighthouseci',
    },
  },
};
