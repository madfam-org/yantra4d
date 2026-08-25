import { BasePage } from './base.page.js'

export class ProjectsViewPage extends BasePage {
  constructor(page) {
    super(page)
    this.title = page.locator('h2', { hasText: /Projects|Proyectos/ })
    // Count the links themselves. The old selector required a `.h-full`
    // descendant, which was a detail of the card-grid markup the catalog
    // browser replaced; the anchor is what a project result actually is.
    this.projectCards = page.locator('a[href^="/project/"]')
    this.loadingText = page.locator('text=Loading projects, text=Cargando proyectos')
    this.errorText = page.locator('.text-destructive')
    this.emptyText = page.locator('text=No projects found, text=No se encontraron proyectos')
    this.createCTA = page.locator('button', { hasText: /Import|Importar/ })
  }

  /** Get a project card by slug. */
  projectCard(slug) {
    return this.page.locator(`a[href="/project/${slug}"]`)
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
