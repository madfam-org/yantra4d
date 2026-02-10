import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ComparisonView from './ComparisonView'

// Mock dependencies
vi.mock('../../contexts/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key) => key }),
}))

vi.mock('../Viewer', () => ({
  default: ({ label }) => <div data-testid="mock-viewer">{label}</div>,
}))

describe('ComparisonView', () => {
  const mockSlots = [
    { id: '1', label: 'Slot 1', parts: [], params: {} },
    { id: '2', label: 'Slot 2', parts: [], params: {} },
  ]

  it('renders empty state when no slots', () => {
    render(
      <ComparisonView
        slots={[]}
        onRemoveSlot={() => {}}
        onAddCurrent={() => {}}
      />
    )
    expect(screen.getByText('compare.empty')).toBeInTheDocument()
    expect(screen.getByText('compare.add_current')).toBeInTheDocument()
  })

  it('renders slots when provided', () => {
    render(
      <ComparisonView
        slots={mockSlots}
        onRemoveSlot={() => {}}
        onAddCurrent={() => {}}
      />
    )
    expect(screen.getByText('compare.title')).toBeInTheDocument()
    expect(screen.getAllByTestId('mock-viewer')).toHaveLength(2)
  })

  it('calls onAddCurrent when add button clicked', () => {
    const onAddCurrent = vi.fn()
    render(
      <ComparisonView
        slots={[]}
        onRemoveSlot={() => {}}
        onAddCurrent={onAddCurrent}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /compare.add_current/i }))
    expect(onAddCurrent).toHaveBeenCalled()
  })

  it('calls onRemoveSlot when remove button clicked', () => {
    const onRemoveSlot = vi.fn()
    render(
      <ComparisonView
        slots={mockSlots}
        onRemoveSlot={onRemoveSlot}
        onAddCurrent={() => {}}
      />
    )
    const removeButtons = screen.getAllByRole('button', { name: 'Remove slot' })
    expect(removeButtons).toHaveLength(2)
    fireEvent.click(removeButtons[0])
    expect(onRemoveSlot).toHaveBeenCalledWith('1')
  })
  
  it('toggles camera sync', () => {
    render(
      <ComparisonView
        slots={mockSlots}
        onRemoveSlot={() => {}}
        onAddCurrent={() => {}}
      />
    )
    const syncButton = screen.getByText('compare.sync_camera')
    fireEvent.click(syncButton)
    // It just changes internal state, so we expect no crash
    expect(syncButton).toBeInTheDocument()
  })
})
