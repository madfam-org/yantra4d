import { BasePage } from './base.page.js'

export class StudioHeaderPage extends BasePage {
  constructor(page) {
    super(page)
    this.header = page.locator('header').first()
    this.projectName = this.header.locator('h1')
    this.projectSelector = this.header.locator('select[aria-label="Select project"]')
    this.projectsLink = this.header.locator('a[href="#/projects"]')
    this.undoButton = this.header.locator('button[title="Undo"], button[title="Deshacer"]')
    this.redoButton = this.header.locator('button[title="Redo"], button[title="Rehacer"]')
    this.shareButton = this.header.locator('button[title="Share configuration"], button[title="Compartir configuración"]')
    this.shareToast = this.header.locator('text=Link copied!, text=¡Enlace copiado!')
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

  async toggleLanguage() {
    await this.languageToggle.click()
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
