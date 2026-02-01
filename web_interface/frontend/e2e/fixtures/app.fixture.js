/* eslint-disable react-hooks/rules-of-hooks */
import { test as base } from '@playwright/test'
import { StudioHeaderPage } from '../page-objects/studio-header.page.js'
import { StudioSidebarPage } from '../page-objects/studio-sidebar.page.js'
import { StudioViewerPage } from '../page-objects/studio-viewer.page.js'
import { ProjectsViewPage } from '../page-objects/projects-view.page.js'
import { OnboardingPage } from '../page-objects/onboarding.page.js'
import { mockAllAPIs } from '../helpers/api-mocker.js'

/**
 * Extended test fixture providing page objects and optional API mocking.
 *
 * API mocks are set up via Playwright route interception BEFORE any navigation,
 * so the app always sees mocked responses from its first request.
 */
export const test = base.extend({
  /** Auto-mock APIs unless test opts out via `test.use({ mockAPIs: false })`. */
  mockAPIs: [true, { option: true }],

  /** Studio header page object. */
  header: async ({ page }, use) => {
    await use(new StudioHeaderPage(page))
  },

  /** Studio sidebar page object. */
  sidebar: async ({ page }, use) => {
    await use(new StudioSidebarPage(page))
  },

  /** Studio viewer page object. */
  viewer: async ({ page }, use) => {
    await use(new StudioViewerPage(page))
  },

  /** Projects view page object. */
  projectsView: async ({ page }, use) => {
    await use(new ProjectsViewPage(page))
  },

  /** Onboarding wizard page object. */
  onboarding: async ({ page }, use) => {
    await use(new OnboardingPage(page))
  },

  /**
   * Auto-setup: mock APIs before each test if enabled.
   * Routes are registered before any page.goto() call, so the app
   * always sees mocked data from the very first network request.
   */
   
  autoMock: [async ({ page, mockAPIs }, use) => {
    if (mockAPIs) {
      await mockAllAPIs(page)
    }
    await use()
  }, { auto: true }],
})

export { expect } from '@playwright/test'
