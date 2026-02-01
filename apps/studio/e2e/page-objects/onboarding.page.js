import { BasePage } from './base.page.js'

export class OnboardingPage extends BasePage {
  constructor(page) {
    super(page)
    this.stepIndicators = page.locator('.flex.items-center.gap-2.text-sm')
    this.errorBanner = page.locator('.bg-destructive\\/10')
  }

  // Step 0: Upload
  get slugInput() { return this.page.locator('input[placeholder="my-project"], input[placeholder="mi-proyecto"]') }
  get dropZone() { return this.page.locator('.border-dashed') }
  get fileInput() { return this.page.locator('#scad-upload') }
  get analyzeButton() { return this.page.locator('button', { hasText: /Analyze|Analizar/ }) }

  // Step 1: Review
  get reviewTitle() { return this.page.locator('text=Analysis Results, text=Resultados del Análisis') }
  get warningsBanner() { return this.page.locator('text=Warnings, text=Advertencias').locator('..') }
  get fileCards() { return this.page.locator('.border.border-border.rounded-md') }

  // Step 2: Edit
  get projectNameInput() { return this.page.locator('input').nth(0) }
  get manifestTextarea() { return this.page.locator('textarea') }

  // Step 3: Save
  get saveTitle() { return this.page.locator('text=Save Project, text=Guardar Proyecto') }
  get createButton() { return this.page.locator('button', { hasText: /Create Project|Crear Proyecto/ }) }

  // Navigation
  get backButton() { return this.page.locator('button', { hasText: /Back|Atrás/ }) }
  get nextButton() { return this.page.locator('button:has(.lucide-chevron-right)').last() }

  /** Get current step (0-3) based on active indicator. */
  async getCurrentStep() {
    const _text = await this.stepIndicators.textContent()
    const steps = ['Upload', 'Review', 'Edit', 'Save', 'Subir', 'Revisar', 'Editar', 'Guardar']
    // Find which step has font-semibold
    const active = this.page.locator('.font-semibold', { hasText: new RegExp(steps.join('|')) })
    const activeText = await active.textContent()
    const stepMap = { Upload: 0, Subir: 0, Review: 1, Revisar: 1, Edit: 2, Editar: 2, Save: 3, Guardar: 3 }
    return stepMap[activeText.trim()] ?? -1
  }
}
