import { BasePage } from './base.page.js'

export class StudioHeaderPage extends BasePage {
  constructor(page) {
    super(page)
    this.header = page.locator('header').first()
    this.projectName = this.header.locator('h1')
    this.projectSelector = this.header.locator('select[aria-label="Select project"]')
    this.projectsLink = this.header.locator('a[href="#/projects"]')
    this.undoButton = this.header.locator('button:has(.lucide-undo-2)')
    this.redoButton = this.header.locator('button:has(.lucide-redo-2)')
    this.shareButton = this.header.locator('button:has(.lucide-share-2)')
    this.languageToggle = this.header.locator('button:has(.lucide-globe)')
    this.themeToggle = this.header.locator('button:has(.lucide-sun), button:has(.lucide-moon), button:has(.lucide-monitor)')
    this.authButton = this.header.locator('button:has(.lucide-log-in), button:has(.lucide-log-out)')
  }

  async clickUndo() {
    await this.undoButton.click()
  }

  async clickRedo() {
    await this.redoButton.click()
  }

  async clickShare() {
    await this.shareButton.click()
  }

  /** Toggle language — opens dropdown, clicks the other language option. */
  async toggleLanguage() {
    await this.languageToggle.click()
    // Wait for dropdown to appear
    const dropdown = this.page.locator('.absolute.top-full button').first()
    await dropdown.waitFor({ timeout: 3000 })
    // Click the non-bold option (the one not currently selected)
    const options = this.page.locator('.absolute.top-full button')
    const count = await options.count()
    for (let i = 0; i < count; i++) {
      const isBold = await options.nth(i).evaluate(el => el.classList.contains('font-semibold'))
      if (!isBold) {
        await options.nth(i).click()
        return
      }
    }
    // Fallback: click the last option
    if (count > 0) await options.last().click()
  }

  async cycleTheme() {
    await this.themeToggle.click()
  }

  async selectProject(slug) {
    await this.projectSelector.selectOption(slug)
  }

  async getProjectName() {
    return this.projectName.textContent()
  }

  async isUndoDisabled() {
    return this.undoButton.isDisabled()
  }

  async isRedoDisabled() {
    return this.redoButton.isDisabled()
  }
}
