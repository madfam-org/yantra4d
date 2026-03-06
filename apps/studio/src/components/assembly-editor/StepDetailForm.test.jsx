import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import StepDetailForm from './StepDetailForm'

expect.extend(toHaveNoViolations)

const baseStep = {
  step: 1,
  label: { en: 'Attach base', es: 'Colocar base' },
  notes: { en: 'Press firmly', es: 'Presionar firmemente' },
  visible_parts: ['base'],
  highlight_parts: [],
}

function renderForm(props = {}) {
  const defaultProps = {
    step: baseStep,
    index: 0,
    onUpdate: vi.fn(),
    language: 'en',
  }
  return render(<StepDetailForm {...defaultProps} {...props} />)
}

describe('StepDetailForm', () => {
  it('renders label input with current value', () => {
    renderForm()
    expect(screen.getByDisplayValue('Attach base')).toBeInTheDocument()
  })

  it('renders notes textarea with current value', () => {
    renderForm()
    expect(screen.getByDisplayValue('Press firmly')).toBeInTheDocument()
  })

  it('renders language indicator in field labels', () => {
    renderForm({ language: 'en' })
    expect(screen.getByText('Label (EN)')).toBeInTheDocument()
    expect(screen.getByText('Notes (EN)')).toBeInTheDocument()
  })

  it('renders correct language indicator for Spanish', () => {
    renderForm({ language: 'es' })
    expect(screen.getByText('Label (ES)')).toBeInTheDocument()
    expect(screen.getByText('Notes (ES)')).toBeInTheDocument()
  })

  it('shows Spanish values when language is es', () => {
    renderForm({ language: 'es' })
    expect(screen.getByDisplayValue('Colocar base')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Presionar firmemente')).toBeInTheDocument()
  })

  describe('label changes', () => {
    it('calls onUpdate with merged label object when label changes', () => {
      const onUpdate = vi.fn()
      renderForm({ onUpdate })
      fireEvent.change(screen.getByDisplayValue('Attach base'), {
        target: { value: 'Install base plate' },
      })
      expect(onUpdate).toHaveBeenCalledWith(0, {
        label: { en: 'Install base plate', es: 'Colocar base' },
      })
    })

    it('preserves other language values when updating one language', () => {
      const onUpdate = vi.fn()
      renderForm({ language: 'es', onUpdate })
      fireEvent.change(screen.getByDisplayValue('Colocar base'), {
        target: { value: 'Instalar base' },
      })
      expect(onUpdate).toHaveBeenCalledWith(0, {
        label: { en: 'Attach base', es: 'Instalar base' },
      })
    })

    it('passes correct index to onUpdate', () => {
      const onUpdate = vi.fn()
      renderForm({ index: 3, onUpdate })
      fireEvent.change(screen.getByDisplayValue('Attach base'), {
        target: { value: 'New label' },
      })
      expect(onUpdate).toHaveBeenCalledWith(3, expect.any(Object))
    })
  })

  describe('notes changes', () => {
    it('calls onUpdate with merged notes object when notes change', () => {
      const onUpdate = vi.fn()
      renderForm({ onUpdate })
      fireEvent.change(screen.getByDisplayValue('Press firmly'), {
        target: { value: 'Press firmly until click' },
      })
      expect(onUpdate).toHaveBeenCalledWith(0, {
        notes: { en: 'Press firmly until click', es: 'Presionar firmemente' },
      })
    })

    it('preserves other language notes when updating', () => {
      const onUpdate = vi.fn()
      renderForm({ language: 'es', onUpdate })
      fireEvent.change(screen.getByDisplayValue('Presionar firmemente'), {
        target: { value: 'Apretar fuerte' },
      })
      expect(onUpdate).toHaveBeenCalledWith(0, {
        notes: { en: 'Press firmly', es: 'Apretar fuerte' },
      })
    })
  })

  describe('edge cases', () => {
    it('handles step with missing label', () => {
      const step = { step: 1, notes: { en: 'Some note' } }
      renderForm({ step })
      // Label input should be empty
      const labelInput = screen.getByPlaceholderText('Step title...')
      expect(labelInput).toHaveValue('')
    })

    it('handles step with missing notes', () => {
      const step = { step: 1, label: { en: 'Step one' } }
      renderForm({ step })
      // Notes textarea should be empty
      const notesInput = screen.getByPlaceholderText('Instructions, tips...')
      expect(notesInput).toHaveValue('')
    })

    it('handles step with null label and notes', () => {
      const step = { step: 1, label: null, notes: null }
      renderForm({ step })
      expect(screen.getByPlaceholderText('Step title...')).toHaveValue('')
      expect(screen.getByPlaceholderText('Instructions, tips...')).toHaveValue('')
    })

    it('creates label object from scratch when step has no label', () => {
      const onUpdate = vi.fn()
      const step = { step: 1 }
      renderForm({ step, onUpdate })
      fireEvent.change(screen.getByPlaceholderText('Step title...'), {
        target: { value: 'New step' },
      })
      expect(onUpdate).toHaveBeenCalledWith(0, {
        label: { en: 'New step' },
      })
    })

    it('creates notes object from scratch when step has no notes', () => {
      const onUpdate = vi.fn()
      const step = { step: 1 }
      renderForm({ step, onUpdate })
      fireEvent.change(screen.getByPlaceholderText('Instructions, tips...'), {
        target: { value: 'New note' },
      })
      expect(onUpdate).toHaveBeenCalledWith(0, {
        notes: { en: 'New note' },
      })
    })
  })

  it('has no accessibility violations', async () => {
    const { container } = renderForm()
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
