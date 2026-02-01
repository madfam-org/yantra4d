/**
 * Base page object with common selectors and actions.
 */
export class BasePage {
  /** @param {import('@playwright/test').Page} page */
  constructor(page) {
    this.page = page
  }

  /** Wait for the app shell to be visible. */
  async waitForReady() {
    await this.page.waitForSelector('header', { timeout: 15_000 })
  }

  /** Get text content of an element. */
  async getText(selector) {
    return this.page.textContent(selector)
  }

  /** Check if element is visible. */
  async isVisible(selector) {
    return this.page.isVisible(selector)
  }

  /** Get current URL hash. */
  async getHash() {
    return this.page.evaluate(() => window.location.hash)
  }

  /** Get localStorage value. */
  async getLocalStorage(key) {
    return this.page.evaluate((k) => localStorage.getItem(k), key)
  }

  /** Set localStorage value. */
  async setLocalStorage(key, value) {
    await this.page.evaluate(({ k, v }) => localStorage.setItem(k, v), { k: key, v: value })
  }
}
