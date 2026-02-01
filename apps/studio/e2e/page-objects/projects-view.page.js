import { BasePage } from './base.page.js'

export class ProjectsViewPage extends BasePage {
  constructor(page) {
    super(page)
    this.title = page.locator('h2', { hasText: /Projects|Proyectos/ })
    this.projectCards = page.locator('a[href^="#/"] .h-full')
    this.loadingText = page.locator('text=Loading projects, text=Cargando proyectos')
    this.errorText = page.locator('.text-destructive')
    this.emptyText = page.locator('text=No projects found, text=No se encontraron proyectos')
    this.createCTA = page.locator('a[href="#/onboard"]')
  }

  /** Get a project card by slug. */
  projectCard(slug) {
    return this.page.locator(`a[href="#/${slug}"]`)
  }

  /** Click a project card. */
  async selectProject(slug) {
    await this.projectCard(slug).click()
  }

  /** Get project card count. */
  async getCardCount() {
    return this.projectCards.count()
  }
}
