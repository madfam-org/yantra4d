import { render, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect, afterEach } from 'vitest'
import ComparisonView from './ComparisonView'

// Mock Viewer since it requires WebGL/Three.js context
vi.mock('../viewer/Viewer', () => ({
  default: ({ parts }) => <div data-testid="viewer-mock">Viewer Mock (Parts: {parts?.length})</div>
}))

// Mock useLanguage hook directly
vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({
    t: (key, params) => (params ? `${key}:${Object.values(params).join(',')}` : key),
  }),
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
    const removeBtn = screen.getByRole('button', { name: 'compare.remove:Slot 1' })
    fireEvent.click(removeBtn)
    expect(mockOnRemoveSlot).toHaveBeenCalledWith('1')
  })

  it('calls onAddCurrent when slots exist but less than 4', () => {
    const slots = [{ id: '1', parts: [], params: {}, label: 'Slot 1' }]
    renderWithProviders(
      <ComparisonView
        slots={slots}
        onAddCurrent={mockOnAddCurrent}
      />
    )
    // There are 2 buttons, one is for "compare.add_current"
    const addBtns = screen.getAllByRole('button', { name: /compare.add_current/i })
    fireEvent.click(addBtns[0])
    expect(mockOnAddCurrent).toHaveBeenCalledTimes(1)
  })

  it('explains how to start when empty', () => {
    renderWithProviders(<ComparisonView slots={[]} onAddCurrent={mockOnAddCurrent} />)
    expect(screen.getByText('compare.empty_hint')).toBeInTheDocument()
    expect(screen.queryByText('compare.add_needs_render')).not.toBeInTheDocument()
  })

  it('disables adding, with a reason, when there is nothing rendered to snapshot', () => {
    renderWithProviders(<ComparisonView slots={[]} onAddCurrent={mockOnAddCurrent} canAddCurrent={false} />)
    const add = screen.getByRole('button', { name: /compare.add_current/i })
    expect(add).toBeDisabled()
    expect(add).toHaveAttribute('aria-describedby', 'compare-add-needs-render')
    expect(screen.getByText('compare.add_needs_render')).toHaveAttribute('id', 'compare-add-needs-render')
    fireEvent.click(add)
    expect(mockOnAddCurrent).not.toHaveBeenCalled()
  })

  it('disables the toolbar add button too when nothing is rendered', () => {
    const slots = [{ id: '1', parts: [], params: {}, label: 'Slot 1' }]
    renderWithProviders(<ComparisonView slots={slots} onAddCurrent={mockOnAddCurrent} canAddCurrent={false} />)
    expect(screen.getByRole('button', { name: /compare.add_current/i })).toBeDisabled()
  })

  it('offers no camera sync: each slot keeps its own camera (owner ruling 2026-11-22)', () => {
    const slots = [{ id: '1', parts: [], params: {}, label: 'Slot 1' }, { id: '2', parts: [], params: {}, label: 'Slot 2' }]
    renderWithProviders(<ComparisonView slots={slots} onAddCurrent={mockOnAddCurrent} />)
    expect(screen.queryByText(/sync_camera/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /sync/i })).not.toBeInTheDocument()
  })

  it('puts the name and remove control of each slot in a bar above its viewer, never over it', () => {
    // They used to float over the viewer's corner, where the viewer's own
    // controls covered the remove button and took its clicks (e2e, every browser).
    const slots = [{ id: '1', parts: [], params: {}, label: 'Slot 1' }]
    renderWithProviders(<ComparisonView slots={slots} onRemoveSlot={mockOnRemoveSlot} />)
    const slot = screen.getByRole('region', { name: 'Slot 1' })
    const remove = screen.getByRole('button', { name: 'compare.remove:Slot 1' })
    const viewer = screen.getByTestId('viewer-mock')
    expect(slot).toContainElement(remove)
    // The bar and the viewer are siblings: the button is not inside the viewer's box.
    expect(viewer.parentElement.contains(remove)).toBe(false)
    expect(remove.parentElement.compareDocumentPosition(viewer.parentElement) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('names unlabelled slots by position, in the language of the visitor', () => {
    const slots = [{ id: 'a', parts: [], params: {} }, { id: 'b', parts: [], params: {} }]
    renderWithProviders(<ComparisonView slots={slots} onRemoveSlot={mockOnRemoveSlot} />)
    expect(screen.getByText('compare.variation:1')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'compare.remove:compare.variation:2' })).toBeInTheDocument()
  })

  it('hides the add control at four slots', () => {
    const slots = [1, 2, 3, 4].map(n => ({ id: String(n), parts: [], params: {}, label: `Slot ${n}` }))
    renderWithProviders(<ComparisonView slots={slots} onAddCurrent={mockOnAddCurrent} onRemoveSlot={mockOnRemoveSlot} />)
    expect(screen.queryByRole('button', { name: /compare.add_current/i })).not.toBeInTheDocument()
    expect(screen.getAllByTestId('comparison-slot')).toHaveLength(4)
  })
})
