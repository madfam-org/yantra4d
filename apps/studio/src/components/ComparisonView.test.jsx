import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

vi.mock('./Viewer', () => ({
  default: function MockViewer(props) {
    return <div data-testid="viewer" />
  },
}))

const mockT = vi.fn((key) => ({
  'compare.empty': 'No comparisons yet',
  'compare.add_current': 'Add current',
  'compare.title': 'Comparison',
  'compare.sync_camera': 'Sync camera',
}[key] || key))

vi.mock('../contexts/LanguageProvider', () => ({
  useLanguage: () => ({ t: mockT }),
}))

import ComparisonView from './ComparisonView'

const baseProps = {
  slots: [],
  onRemoveSlot: vi.fn(),
  onAddCurrent: vi.fn(),
  colors: {},
  wireframe: false,
  mode: 'full',
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ComparisonView', () => {
  it('renders empty state when no slots', () => {
    render(<ComparisonView {...baseProps} />)
    expect(screen.getByText('No comparisons yet')).toBeInTheDocument()
    expect(screen.getByText('Add current')).toBeInTheDocument()
  })

  it('calls onAddCurrent when clicking add button in empty state', () => {
    render(<ComparisonView {...baseProps} />)
    fireEvent.click(screen.getByText('Add current'))
    expect(baseProps.onAddCurrent).toHaveBeenCalledOnce()
  })

  it('renders slots with viewers', () => {
    const slots = [
      { id: '1', label: 'Variant A', parts: [{ id: 'body' }], params: { width: 10 } },
      { id: '2', label: 'Variant B', parts: [{ id: 'body' }], params: { width: 20 } },
    ]
    render(<ComparisonView {...baseProps} slots={slots} />)
    expect(screen.getAllByTestId('viewer')).toHaveLength(2)
    expect(screen.getByText('Variant A')).toBeInTheDocument()
    expect(screen.getByText('Variant B')).toBeInTheDocument()
  })

  it('shows count indicator', () => {
    const slots = [
      { id: '1', parts: [], params: {} },
      { id: '2', parts: [], params: {} },
    ]
    render(<ComparisonView {...baseProps} slots={slots} />)
    expect(screen.getByText('(2/4)')).toBeInTheDocument()
  })

  it('shows add button when fewer than 4 slots', () => {
    const slots = [{ id: '1', parts: [], params: {} }]
    render(<ComparisonView {...baseProps} slots={slots} />)
    // The add button in the toolbar
    const addButtons = screen.getAllByText('Add current')
    expect(addButtons.length).toBeGreaterThan(0)
  })

  it('hides add button when 4 slots', () => {
    const slots = [
      { id: '1', parts: [], params: {} },
      { id: '2', parts: [], params: {} },
      { id: '3', parts: [], params: {} },
      { id: '4', parts: [], params: {} },
    ]
    render(<ComparisonView {...baseProps} slots={slots} />)
    expect(screen.getByText('(4/4)')).toBeInTheDocument()
    // Only the title bar text, no add button
    expect(screen.queryByRole('button', { name: /add current/i })).not.toBeInTheDocument()
  })

  it('calls onRemoveSlot when clicking remove button', () => {
    const slots = [{ id: '1', label: 'A', parts: [], params: {} }]
    const onRemoveSlot = vi.fn()
    render(<ComparisonView {...baseProps} slots={slots} onRemoveSlot={onRemoveSlot} />)
    // The slot container has a label span and a remove button next to it
    // The remove button is the one with hover:bg-destructive class inside the slot overlay
    const slotLabel = screen.getByText('A')
    const removeBtn = slotLabel.parentElement.querySelector('button')
    fireEvent.click(removeBtn)
    expect(onRemoveSlot).toHaveBeenCalledWith('1')
  })

  it('toggles sync camera button', () => {
    const slots = [{ id: '1', parts: [], params: {} }]
    render(<ComparisonView {...baseProps} slots={slots} />)
    const syncBtn = screen.getByText('Sync camera')
    expect(syncBtn).toBeInTheDocument()
    fireEvent.click(syncBtn)
    // Sync camera toggles — button is still visible
    expect(screen.getByText('Sync camera')).toBeInTheDocument()
  })

  it('assigns fallback label when slot has no label', () => {
    const slots = [{ id: '1', parts: [], params: {} }]
    render(<ComparisonView {...baseProps} slots={slots} />)
    expect(screen.getByText('#1')).toBeInTheDocument()
  })
})
