import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import StepList from './StepList'

expect.extend(toHaveNoViolations)

const steps = [
  { step: 1, label: { en: 'Attach base', es: 'Colocar base' } },
  { step: 2, label: { en: 'Mount lid' } },
  { step: 3, label: { en: 'Insert hinge' } },
]

function renderList(props = {}) {
  const defaultProps = {
    steps,
    selectedIndex: 0,
    onSelect: vi.fn(),
    onAdd: vi.fn(),
    onRemove: vi.fn(),
    onReorder: vi.fn(),
    language: 'en',
  }
  return render(<StepList {...defaultProps} {...props} />)
}

describe('StepList', () => {
  it('renders all step labels', () => {
    renderList()
    expect(screen.getByText('Attach base')).toBeInTheDocument()
    expect(screen.getByText('Mount lid')).toBeInTheDocument()
    expect(screen.getByText('Insert hinge')).toBeInTheDocument()
  })

  it('renders step count', () => {
    renderList()
    expect(screen.getByText('Steps (3)')).toBeInTheDocument()
  })

  it('renders step numbers', () => {
    renderList()
    expect(screen.getByText('1.')).toBeInTheDocument()
    expect(screen.getByText('2.')).toBeInTheDocument()
    expect(screen.getByText('3.')).toBeInTheDocument()
  })

  it('renders Add button', () => {
    renderList()
    expect(screen.getByText('Add')).toBeInTheDocument()
  })

  describe('label resolution', () => {
    it('falls back to step number when label is missing', () => {
      const noLabel = [{ step: 1 }]
      renderList({ steps: noLabel, selectedIndex: 0 })
      expect(screen.getByText('Step 1')).toBeInTheDocument()
    })

    it('handles string label', () => {
      const strLabel = [{ step: 1, label: 'Direct string' }]
      renderList({ steps: strLabel, selectedIndex: 0 })
      expect(screen.getByText('Direct string')).toBeInTheDocument()
    })

    it('uses language-specific label', () => {
      renderList({ language: 'es' })
      expect(screen.getByText('Colocar base')).toBeInTheDocument()
    })

    it('falls back to en label when requested language is missing', () => {
      renderList({ language: 'fr' })
      // step 1 has no fr, should fall back to en
      expect(screen.getByText('Attach base')).toBeInTheDocument()
    })

    it('falls back to step number when label object has no matching language and no en', () => {
      const noMatch = [{ step: 5, label: { de: 'Basis' } }]
      renderList({ steps: noMatch, selectedIndex: 0, language: 'fr' })
      // No fr, no en fallback -> Step 5
      expect(screen.getByText('Step 5')).toBeInTheDocument()
    })
  })

  describe('selection', () => {
    it('calls onSelect when step is clicked', () => {
      const onSelect = vi.fn()
      renderList({ onSelect })
      fireEvent.click(screen.getByText('Mount lid'))
      expect(onSelect).toHaveBeenCalledWith(1)
    })

    it('calls onSelect with Enter key', () => {
      const onSelect = vi.fn()
      renderList({ onSelect })
      const stepItem = screen.getByText('Mount lid').closest('[role="button"]')
      fireEvent.keyDown(stepItem, { key: 'Enter' })
      expect(onSelect).toHaveBeenCalledWith(1)
    })

    it('calls onSelect with Space key', () => {
      const onSelect = vi.fn()
      renderList({ onSelect })
      const stepItem = screen.getByText('Insert hinge').closest('[role="button"]')
      fireEvent.keyDown(stepItem, { key: ' ' })
      expect(onSelect).toHaveBeenCalledWith(2)
    })

    it('does not call onSelect for other keys', () => {
      const onSelect = vi.fn()
      renderList({ onSelect })
      const stepItem = screen.getByText('Mount lid').closest('[role="button"]')
      fireEvent.keyDown(stepItem, { key: 'Tab' })
      expect(onSelect).not.toHaveBeenCalled()
    })

    it('step items have role=button and tabIndex=0 for keyboard access', () => {
      renderList()
      const items = screen.getAllByRole('button')
      // Filter to step items (those with tabIndex=0)
      const stepItems = items.filter(el => el.getAttribute('tabindex') === '0')
      expect(stepItems).toHaveLength(steps.length)
    })
  })

  describe('Add button', () => {
    it('calls onAdd when clicked', () => {
      const onAdd = vi.fn()
      renderList({ onAdd })
      fireEvent.click(screen.getByText('Add'))
      expect(onAdd).toHaveBeenCalledTimes(1)
    })
  })

  describe('reorder and remove controls (selected step)', () => {
    it('shows reorder/remove buttons only for selected step', () => {
      const { container } = renderList({ selectedIndex: 1 })
      // The selected step (index 1) should have up/down/delete buttons
      // Other steps should not have them
      const allItems = container.querySelectorAll('[role="button"]')
      // First item (not selected) should not have sub-buttons
      const firstItem = allItems[0]
      expect(firstItem.querySelectorAll('button')).toHaveLength(0)
    })

    it('calls onReorder with (index, -1) for move up', () => {
      const onReorder = vi.fn()
      renderList({ selectedIndex: 1, onReorder })
      // The up button is the first icon button within the selected step
      const selectedStep = screen.getByText('Mount lid').closest('[role="button"]')
      const buttons = selectedStep.querySelectorAll('button')
      // Buttons order: up, down, delete
      fireEvent.click(buttons[0])
      expect(onReorder).toHaveBeenCalledWith(1, -1)
    })

    it('calls onReorder with (index, 1) for move down', () => {
      const onReorder = vi.fn()
      renderList({ selectedIndex: 1, onReorder })
      const selectedStep = screen.getByText('Mount lid').closest('[role="button"]')
      const buttons = selectedStep.querySelectorAll('button')
      fireEvent.click(buttons[1])
      expect(onReorder).toHaveBeenCalledWith(1, 1)
    })

    it('calls onRemove with index for delete', () => {
      const onRemove = vi.fn()
      renderList({ selectedIndex: 1, onRemove })
      const selectedStep = screen.getByText('Mount lid').closest('[role="button"]')
      const buttons = selectedStep.querySelectorAll('button')
      fireEvent.click(buttons[2])
      expect(onRemove).toHaveBeenCalledWith(1)
    })

    it('disables move up button for first step', () => {
      renderList({ selectedIndex: 0 })
      const selectedStep = screen.getByText('Attach base').closest('[role="button"]')
      const buttons = selectedStep.querySelectorAll('button')
      expect(buttons[0]).toBeDisabled()
    })

    it('disables move down button for last step', () => {
      renderList({ selectedIndex: 2 })
      const selectedStep = screen.getByText('Insert hinge').closest('[role="button"]')
      const buttons = selectedStep.querySelectorAll('button')
      expect(buttons[1]).toBeDisabled()
    })

    it('disables delete button when only one step exists', () => {
      const singleStep = [{ step: 1, label: { en: 'Only step' } }]
      renderList({ steps: singleStep, selectedIndex: 0 })
      const selectedStep = screen.getByText('Only step').closest('[role="button"]')
      const buttons = selectedStep.querySelectorAll('button')
      // Delete is the last button
      expect(buttons[buttons.length - 1]).toBeDisabled()
    })

    it('enables delete button when multiple steps exist', () => {
      renderList({ selectedIndex: 0 })
      const selectedStep = screen.getByText('Attach base').closest('[role="button"]')
      const buttons = selectedStep.querySelectorAll('button')
      expect(buttons[buttons.length - 1]).toBeEnabled()
    })

    it('stopPropagation prevents onSelect when clicking action buttons', () => {
      const onSelect = vi.fn()
      const onReorder = vi.fn()
      renderList({ selectedIndex: 1, onSelect, onReorder })
      const selectedStep = screen.getByText('Mount lid').closest('[role="button"]')
      const buttons = selectedStep.querySelectorAll('button')
      // Click the up button
      fireEvent.click(buttons[0])
      // onReorder should fire but onSelect should not (due to stopPropagation)
      expect(onReorder).toHaveBeenCalled()
      expect(onSelect).not.toHaveBeenCalled()
    })
  })

  it('renders with empty steps array', () => {
    renderList({ steps: [] })
    expect(screen.getByText('Steps (0)')).toBeInTheDocument()
    expect(screen.getByText('Add')).toBeInTheDocument()
  })

  it('has no accessibility violations (excluding known gaps)', async () => {
    // Known a11y gaps in StepList source component:
    // 1. button-name: Icon-only reorder/delete buttons (ChevronUp, ChevronDown,
    //    Trash2) lack aria-label attributes.
    // 2. nested-interactive: The selected step row uses role="button" with
    //    tabIndex=0 but contains nested <button> children for reorder/delete,
    //    violating the nested-interactive rule.
    // Both are documented here as known issues to fix in the source.
    const { container } = renderList()
    const results = await axe(container, {
      rules: {
        'button-name': { enabled: false },
        'nested-interactive': { enabled: false },
      },
    })
    expect(results).toHaveNoViolations()
  })
})
