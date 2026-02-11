import { render, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect, afterEach } from 'vitest'
import ComparisonView from './ComparisonView'

// Mock Viewer since it requires WebGL/Three.js context
vi.mock('../Viewer', () => ({
  default: ({ parts }) => <div data-testid="viewer-mock">Viewer Mock (Parts: {parts?.length})</div>
}))

// Mock useLanguage hook directly
vi.mock('../../contexts/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key) => key }),
  LanguageProvider: ({ children }) => children
}))

const renderWithProviders = (ui) => {
  return render(ui)
}

describe('ComparisonView', () => {
  const mockOnAddCurrent = vi.fn()
  const mockOnRemoveSlot = vi.fn()

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty state when no slots provided', () => {
    renderWithProviders(
      <ComparisonView
        slots={[]}
        onAddCurrent={mockOnAddCurrent}
        onRemoveSlot={mockOnRemoveSlot}
      />
    )
    expect(screen.getByText('compare.empty')).toBeInTheDocument()
    expect(screen.getByText('compare.add_current')).toBeInTheDocument()
  })

  it('calls onAddCurrent when add button clicked in empty state', () => {
    renderWithProviders(
      <ComparisonView
        slots={[]}
        onAddCurrent={mockOnAddCurrent}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /compare.add_current/i }))
    expect(mockOnAddCurrent).toHaveBeenCalledTimes(1)
  })

  it('renders populated slots', () => {
    const slots = [
      { id: '1', parts: [], params: {}, label: 'Slot 1' },
      { id: '2', parts: [], params: {}, label: 'Slot 2' }
    ]
    renderWithProviders(
      <ComparisonView
        slots={slots}
        onRemoveSlot={mockOnRemoveSlot}
      />
    )
    expect(screen.getByText('Slot 1')).toBeInTheDocument()
    expect(screen.getByText('Slot 2')).toBeInTheDocument()
    expect(screen.getAllByTestId('viewer-mock')).toHaveLength(2)
  })

  it('calls onRemoveSlot when remove button clicked', () => {
    const slots = [{ id: '1', parts: [], params: {}, label: 'Slot 1' }]
    renderWithProviders(
      <ComparisonView
        slots={slots}
        onRemoveSlot={mockOnRemoveSlot}
      />
    )
    const removeBtn = screen.getByLabelText('Remove slot')
    fireEvent.click(removeBtn)
    expect(mockOnRemoveSlot).toHaveBeenCalledWith('1')
  })
})
