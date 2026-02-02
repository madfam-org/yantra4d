import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

const mockSteps = [
  { step: 1, label: { en: 'Place base' }, notes: { en: 'Start here' }, visible_parts: ['bottom'], highlight_parts: [] },
  { step: 2, label: { en: 'Add top' }, notes: { en: 'Snap on' }, visible_parts: ['bottom', 'top'], highlight_parts: ['top'] },
]

vi.mock('../contexts/LanguageProvider', () => ({
  useLanguage: () => ({ language: 'en', t: (k) => k }),
}))

let mockManifest = { assembly_steps: mockSteps }

vi.mock('../contexts/ManifestProvider', () => ({
  useManifest: () => ({
    manifest: mockManifest,
    getLabel: (obj, field, lang) => obj?.[field]?.[lang] || '',
  }),
}))

import AssemblyView from './AssemblyView'

beforeEach(() => {
  mockManifest = { assembly_steps: mockSteps }
  vi.clearAllMocks()
})

describe('AssemblyView', () => {
  it('renders step navigation', () => {
    render(<AssemblyView onStepChange={vi.fn()} />)
    expect(screen.getByText('assembly.title')).toBeInTheDocument()
    expect(screen.getByText(/1 \/ 2/)).toBeInTheDocument()
    expect(screen.getByText('Place base')).toBeInTheDocument()
  })

  it('navigates to next step', () => {
    const onStep = vi.fn()
    render(<AssemblyView onStepChange={onStep} />)
    fireEvent.click(screen.getByLabelText('assembly.next'))
    expect(screen.getByText(/2 \/ 2/)).toBeInTheDocument()
    expect(screen.getByText('Add top')).toBeInTheDocument()
  })

  it('navigates via keyboard', () => {
    const onStep = vi.fn()
    render(<AssemblyView onStepChange={onStep} />)
    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(screen.getByText(/2 \/ 2/)).toBeInTheDocument()
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    expect(screen.getByText(/1 \/ 2/)).toBeInTheDocument()
  })

  it('disables prev on first step', () => {
    render(<AssemblyView onStepChange={vi.fn()} />)
    expect(screen.getByLabelText('assembly.prev')).toBeDisabled()
  })

  it('returns null when no steps', () => {
    mockManifest = { assembly_steps: [] }
    const { container } = render(<AssemblyView onStepChange={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('calls onStepChange on mount with first step', () => {
    const onStep = vi.fn()
    render(<AssemblyView onStepChange={onStep} />)
    expect(onStep).toHaveBeenCalledWith(mockSteps[0])
  })

  it('calls onStepChange(null) on unmount', () => {
    const onStep = vi.fn()
    const { unmount } = render(<AssemblyView onStepChange={onStep} />)
    unmount()
    expect(onStep).toHaveBeenCalledWith(null)
  })

  it('shows notes when present', () => {
    render(<AssemblyView onStepChange={vi.fn()} />)
    expect(screen.getByText('Start here')).toBeInTheDocument()
  })
})
