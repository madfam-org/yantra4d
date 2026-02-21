import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import OnboardingWizard from './OnboardingWizard'

// Mock dependencies
vi.mock('../../contexts/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key) => key }),
}))

vi.mock('../../services/core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

const defaultProps = {
  onComplete: vi.fn(),
  onCancel: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
  globalThis.fetch = vi.fn()
})

describe('OnboardingWizard', () => {
  describe('Step 0: Upload', () => {
    it('renders upload step initially', () => {
      render(<OnboardingWizard {...defaultProps} />)
      expect(screen.getByText('onboard.upload_title')).toBeInTheDocument()
      expect(screen.getByText('onboard.drop_text')).toBeInTheDocument()
      expect(screen.getByText('onboard.browse')).toBeInTheDocument()
    })

    it('renders all step indicators', () => {
      render(<OnboardingWizard {...defaultProps} />)
      expect(screen.getByText('onboard.step_upload')).toBeInTheDocument()
      expect(screen.getByText('onboard.step_review')).toBeInTheDocument()
      expect(screen.getByText('onboard.step_edit')).toBeInTheDocument()
      expect(screen.getByText('onboard.step_save')).toBeInTheDocument()
    })

    it('renders slug input with default value', () => {
      render(<OnboardingWizard {...defaultProps} />)
      const slugInput = screen.getByPlaceholderText('onboard.slug_placeholder')
      expect(slugInput.value).toBe('new-project')
    })

    it('disables analyze button when no files uploaded', () => {
      render(<OnboardingWizard {...defaultProps} />)
      const analyzeBtn = screen.getByText('onboard.analyze_btn')
      expect(analyzeBtn.closest('button')).toBeDisabled()
    })

    it('shows error when analyze fails', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ error: 'Analysis failed' }),
      })

      render(<OnboardingWizard {...defaultProps} />)

      // Simulate file selection via input change
      const fileInput = document.getElementById('scad-upload')
      const testFile = new File(['module test() {}'], 'test.scad', { type: '' })
      fireEvent.change(fileInput, { target: { files: [testFile] } })

      // Click analyze
      const analyzeBtn = screen.getByText('onboard.analyze_btn')
      fireEvent.click(analyzeBtn)

      await waitFor(() => {
        expect(screen.getByText('Analysis failed')).toBeInTheDocument()
      })
    })

    it('shows file list after file selection', () => {
      render(<OnboardingWizard {...defaultProps} />)

      const fileInput = document.getElementById('scad-upload')
      const testFile = new File(['module test() {}'], 'test.scad', { type: '' })
      fireEvent.change(fileInput, { target: { files: [testFile] } })

      expect(screen.getByText('test.scad')).toBeInTheDocument()
      expect(screen.getByText(/1/)).toBeInTheDocument()
    })

    it('advances to step 1 on successful analysis', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          analysis: {
            files: {
              'test.scad': {
                variables: [{ name: 'height' }],
                modules: [],
                includes: [],
                render_modes: [],
              },
            },
          },
          manifest: {
            project: { name: 'Test', slug: 'test' },
            modes: [{ id: 'default', label: 'Default', scad_file: 'test.scad' }],
            parameters: [],
          },
          warnings: [],
        }),
      })

      render(<OnboardingWizard {...defaultProps} />)

      const fileInput = document.getElementById('scad-upload')
      const testFile = new File(['module test() {}'], 'test.scad', { type: '' })
      fireEvent.change(fileInput, { target: { files: [testFile] } })
      fireEvent.click(screen.getByText('onboard.analyze_btn'))

      await waitFor(() => {
        expect(screen.getByText('onboard.review_title')).toBeInTheDocument()
      })
    })
  })

  describe('Step 1: Review', () => {
    async function renderAtStep1(overrides = {}) {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          analysis: {
            files: {
              'main.scad': {
                variables: [{ name: 'width' }],
                modules: ['box'],
                includes: [],
                render_modes: ['default'],
              },
            },
          },
          manifest: {
            project: { name: 'Test', slug: 'test' },
            modes: [{ id: 'default', label: 'Default', scad_file: 'main.scad' }],
            parameters: [{ id: 'width', type: 'slider', default: 10, min: 1, max: 100 }],
          },
          warnings: overrides.warnings || [],
        }),
      })

      render(<OnboardingWizard {...defaultProps} />)

      const fileInput = document.getElementById('scad-upload')
      fireEvent.change(fileInput, { target: { files: [new File(['content'], 'main.scad')] } })
      fireEvent.click(screen.getByText('onboard.analyze_btn'))

      await waitFor(() => {
        expect(screen.getByText('onboard.review_title')).toBeInTheDocument()
      })
    }

    it('shows file analysis details', async () => {
      await renderAtStep1()
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    it('shows warnings when present', async () => {
      await renderAtStep1({ warnings: ['Missing module'] })
      expect(screen.getByText('Missing module')).toBeInTheDocument()
    })

    it('navigates back to upload step', async () => {
      await renderAtStep1()
      fireEvent.click(screen.getByText('onboard.back'))
      expect(screen.getByText('onboard.upload_title')).toBeInTheDocument()
    })

    it('navigates forward to edit step', async () => {
      await renderAtStep1({ warnings: [] })
      const nextBtn = screen.getByText('onboard.edit_manifest')
      fireEvent.click(nextBtn)
      await waitFor(() => {
        expect(screen.getByText('onboard.edit_title')).toBeInTheDocument()
      })
    })
  })

  describe('Step 2: Edit Manifest', () => {
    async function renderAtStep2() {
      // Mock analysis result
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          analysis: {
            files: {
              'main.scad': {
                variables: [],
                modules: [],
                includes: [],
                render_modes: [],
              }
            }
          },
          manifest: {
            project: { name: 'Test', slug: 'test' },
            modes: [{ id: 'default', label: 'Default', scad_file: 'main.scad' }],
            parameters: [
              { id: 'width', type: 'slider', default: 10, min: 1, max: 100 },
              { id: 'show', type: 'checkbox', default: true },
            ],
          },
          warnings: [],
        }),
      })

      render(<OnboardingWizard {...defaultProps} />)

      // Upload & Analyze
      const fileInput = document.getElementById('scad-upload')
      fireEvent.change(fileInput, { target: { files: [new File(['content'], 'main.scad')] } })
      fireEvent.click(screen.getByText('onboard.analyze_btn'))

      // Wait for review step
      await waitFor(() => screen.getByText('onboard.review_title'))

      // Go to edit step
      fireEvent.click(screen.getByText('onboard.edit_manifest'))
      await waitFor(() => screen.getByText('onboard.edit_title'))
    }

    it('renders parameter list', async () => {
      await renderAtStep2()
      expect(screen.getByText('width')).toBeInTheDocument()
      expect(screen.getByText('show')).toBeInTheDocument()
    })





    it('updates parameter min/max', async () => {
      await renderAtStep2()
      // inputs: default, min, max (if applicable) for slider type
      const inputs = screen.getAllByRole('spinbutton')
      // width is first parameter (slider):
      // 1. default value input
      // 2. min value input
      // 3. max value input
      const minInput = inputs[1]
      fireEvent.change(minInput, { target: { value: '5' } })
      expect(minInput.value).toBe('5')
    })

    it('navigates to save step', async () => {
      await renderAtStep2()
      fireEvent.click(screen.getByText('onboard.review_save'))
      expect(screen.getByText('onboard.save_title')).toBeInTheDocument()
    })
  })

  describe('Step 3: Save', () => {
    async function renderAtStep3() {
      // Setup same as Step 2 but advance one more
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          analysis: {
            files: {
              'main.scad': {
                variables: [],
                modules: [],
                includes: [],
                render_modes: [],
              }
            }
          },
          manifest: {
            project: { name: 'Test', slug: 'test' },
            modes: [{ id: 'default', label: 'Default', scad_file: 'main.scad' }],
            parameters: [],
          },
          warnings: [],
        }),
      })

      render(<OnboardingWizard {...defaultProps} />)

      // Upload
      const fileInput = document.getElementById('scad-upload')
      fireEvent.change(fileInput, { target: { files: [new File(['content'], 'main.scad')] } })
      fireEvent.click(screen.getByText('onboard.analyze_btn'))
      await waitFor(() => screen.getByText('onboard.review_title'))

      // Edit
      fireEvent.click(screen.getByText('onboard.edit_manifest'))
      await waitFor(() => screen.getByText('onboard.edit_title'))

      // Save
      fireEvent.click(screen.getByText('onboard.review_save'))
      await waitFor(() => screen.getByText('onboard.save_title'))
    }

    it('renders save summary', async () => {
      await renderAtStep3()
      // "onboard.save_summary" is just the key in mock, so we look for it
      // The real component replaces placeholders, but our mock language provider just returns the key
      // Actually, wait - let's verify what the component renders.
      // It renders {saveSummary} which comes from t("onboard.save_summary").replace(...)
      // Since our t(key) returns key, it will try to replace on the key string "onboard.save_summary".
      // It won't find placeholders. So it just renders "onboard.save_summary".
      expect(screen.getByText('onboard.save_summary')).toBeInTheDocument()
    })

    it('saves project on create click', async () => {
      await renderAtStep3()

      // Mock save response
      globalThis.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })

      fireEvent.click(screen.getByText('onboard.create_btn'))

      await waitFor(() => {
        expect(defaultProps.onComplete).toHaveBeenCalled()
      })
    })

    it('shows error if save fails', async () => {
      await renderAtStep3()

      // Mock save failure
      globalThis.fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: 'Save failed' }),
      })

      fireEvent.click(screen.getByText('onboard.create_btn'))

      await waitFor(() => {
        expect(screen.getByText('Save failed')).toBeInTheDocument()
      })
    })
  })
})
