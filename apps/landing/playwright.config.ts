import { defineConfig, devices } from '@playwright/test';
import type { LandingOptions } from './e2e/fixtures';

const HOST = '127.0.0.1';
const PORT = 4321;
const BASE_URL = `http://${HOST}:${PORT}`;

/**
 * Three profiles, one browser. Chromium only: the budgets are about bytes and
 * tiers, not rendering engines, and the self-hosted runner installs one browser.
 *
 *   desktop-full  Desktop Chrome, every navigation pinned to `?tier=full`
 *   mobile-lite   Pixel 5, pinned to `?tier=lite`
 *   still         Desktop Chrome with prefers-reduced-motion and NO override:
 *                 the page must reach `still` from its own signals
 *
 * The 3D profiles pin the tier because headless Chromium is classified `still`
 * by user agent (BOT_UA_RE) and its software WebGL would demote it again in the
 * probe; `?tier=` is the QA override the page provides for exactly this.
 */
export default defineConfig<LandingOptions>({
  testDir: './e2e',
  timeout: 120_000,
  // Same floor as the studio suite: the shared ARC pods render slower than a
  // laptop, and tight waits are where flakes come from.
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  // CI-only retry budget; a retried pass is reported as "flaky", not hidden.
  retries: process.env.CI ? 2 : 0,
  // One worker on CI: the long-task and transfer measurements share one runner
  // and one preview server; concurrency would only add noise.
  workers: process.env.CI ? 1 : undefined,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    tier: null,
  },
  projects: [
    {
      name: 'desktop-full',
      use: { ...devices['Desktop Chrome'], tier: 'full' },
    },
    {
      name: 'mobile-lite',
      use: { ...devices['Pixel 5'], tier: 'lite' },
      // axe runs in the still and full profiles; parity compares the two tiers itself.
      testIgnore: [/a11y\.spec/, /parity\.spec/],
    },
    {
      name: 'still',
      use: { ...devices['Desktop Chrome'], reducedMotion: 'reduce', tier: null },
      testIgnore: [/parity\.spec/],
    },
  ],
  webServer: {
    // The built site, exactly as deployed: `astro preview` of dist/ on
    // 127.0.0.1:4321. `npm run build` must have run first (CI does; locally,
    // build once and Playwright reuses a server already on the port).
    //
    // Through Astro's JS API (e2e/preview-server.mjs) rather than `npm run
    // preview`: the Astro 7 CLI daemonises the preview when it detects an
    // agent shell, and Playwright then sees its process exit early. Same
    // server and flags either way.
    command: 'node e2e/preview-server.mjs',
    env: { LANDING_E2E_HOST: HOST, LANDING_E2E_PORT: String(PORT) },
    url: `${BASE_URL}/`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
