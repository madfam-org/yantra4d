import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import AssemblyEditorToolbar from './AssemblyEditorToolbar'

expect.extend(toHaveNoViolations)

function renderToolbar(props = {}) {
  const defaultProps = {
    isDirty: false,
    saving: false,
    onSave: vi.fn(),
    onDiscard: vi.fn(),
    onPreview: vi.fn(),
    onClose: vi.fn(),
  }
  return render(<AssemblyEditorToolbar {...defaultProps} {...props} />)
}

describe('AssemblyEditorToolbar', () => {
  it('renders all four buttons', () => {
    renderToolbar()
    expect(screen.getByText('Save')).toBeInTheDocument()
    expect(screen.getByText('Discard')).toBeInTheDocument()
    expect(screen.getByText('Preview')).toBeInTheDocument()
    expect(screen.getByText('Close')).toBeInTheDocument()
  })

  describe('Save button', () => {
    it('is disabled when not dirty', () => {
      renderToolbar({ isDirty: false })
      expect(screen.getByText('Save').closest('button')).toBeDisabled()
    })

    it('is disabled while saving', () => {
      renderToolbar({ isDirty: true, saving: true })
      expect(screen.getByText('Saving...').closest('button')).toBeDisabled()
    })

    it('is enabled when dirty and not saving', () => {
      renderToolbar({ isDirty: true, saving: false })
      expect(screen.getByText('Save').closest('button')).toBeEnabled()
    })

    it('calls onSave when clicked', () => {
      const onSave = vi.fn()
      renderToolbar({ isDirty: true, onSave })
      fireEvent.click(screen.getByText('Save'))
      expect(onSave).toHaveBeenCalledTimes(1)
    })

    it('shows "Saving..." text when saving is true', () => {
      renderToolbar({ isDirty: true, saving: true })
      expect(screen.getByText('Saving...')).toBeInTheDocument()
      expect(screen.queryByText('Save')).not.toBeInTheDocument()
    })
  })

  describe('Discard button', () => {
    it('is disabled when not dirty', () => {
      renderToolbar({ isDirty: false })
      expect(screen.getByText('Discard').closest('button')).toBeDisabled()
    })

    it('is enabled when dirty', () => {
      renderToolbar({ isDirty: true })
      expect(screen.getByText('Discard').closest('button')).toBeEnabled()
    })

    it('calls onDiscard when clicked', () => {
      const onDiscard = vi.fn()
      renderToolbar({ isDirty: true, onDiscard })
      fireEvent.click(screen.getByText('Discard'))
      expect(onDiscard).toHaveBeenCalledTimes(1)
    })
  })

  describe('Preview button', () => {
    it('is always enabled regardless of dirty state', () => {
      renderToolbar({ isDirty: false })
      expect(screen.getByText('Preview').closest('button')).toBeEnabled()
    })

    it('calls onPreview when clicked', () => {
      const onPreview = vi.fn()
      renderToolbar({ onPreview })
      fireEvent.click(screen.getByText('Preview'))
      expect(onPreview).toHaveBeenCalledTimes(1)
    })
  })

  describe('Close button', () => {
    it('is always enabled regardless of dirty state', () => {
      renderToolbar({ isDirty: false })
      expect(screen.getByText('Close').closest('button')).toBeEnabled()
    })

    it('calls onClose when clicked', () => {
      const onClose = vi.fn()
      renderToolbar({ onClose })
      fireEvent.click(screen.getByText('Close'))
      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  it('does not call onSave when button is disabled and clicked', () => {
    const onSave = vi.fn()
    renderToolbar({ isDirty: false, onSave })
    fireEvent.click(screen.getByText('Save').closest('button'))
    expect(onSave).not.toHaveBeenCalled()
  })

  it('has no accessibility violations', async () => {
    const { container } = renderToolbar({ isDirty: true })
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
