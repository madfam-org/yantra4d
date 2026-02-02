import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import StepList from './StepList'
import StepDetailForm from './StepDetailForm'
import PartVisibilityPicker from './PartVisibilityPicker'
import CameraCaptureButton from './CameraCaptureButton'
import AssemblyEditorToolbar from './AssemblyEditorToolbar'

const steps = [
  { step: 1, label: { en: 'Base' }, notes: { en: 'note1' }, visible_parts: ['bottom'], highlight_parts: [] },
  { step: 2, label: { en: 'Top' }, notes: { en: '' }, visible_parts: ['top'], highlight_parts: ['top'] },
]

describe('StepList', () => {
  it('renders steps with labels', () => {
    render(<StepList steps={steps} selectedIndex={0} onSelect={vi.fn()} onAdd={vi.fn()} onRemove={vi.fn()} onReorder={vi.fn()} language="en" />)
    expect(screen.getByText('Base')).toBeInTheDocument()
    expect(screen.getByText('Top')).toBeInTheDocument()
    expect(screen.getByText('Steps (2)')).toBeInTheDocument()
  })

  it('calls onSelect when step clicked', () => {
    const onSelect = vi.fn()
    render(<StepList steps={steps} selectedIndex={0} onSelect={onSelect} onAdd={vi.fn()} onRemove={vi.fn()} onReorder={vi.fn()} language="en" />)
    fireEvent.click(screen.getByText('Top'))
    expect(onSelect).toHaveBeenCalledWith(1)
  })

  it('calls onAdd when Add clicked', () => {
    const onAdd = vi.fn()
    render(<StepList steps={steps} selectedIndex={0} onSelect={vi.fn()} onAdd={onAdd} onRemove={vi.fn()} onReorder={vi.fn()} language="en" />)
    fireEvent.click(screen.getByText('Add'))
    expect(onAdd).toHaveBeenCalled()
  })

  it('falls back to step number for missing label', () => {
    const noLabel = [{ step: 1 }]
    render(<StepList steps={noLabel} selectedIndex={0} onSelect={vi.fn()} onAdd={vi.fn()} onRemove={vi.fn()} onReorder={vi.fn()} language="en" />)
    expect(screen.getByText('Step 1')).toBeInTheDocument()
  })

  it('renders reorder/remove buttons for selected step', () => {
    render(<StepList steps={steps} selectedIndex={0} onSelect={vi.fn()} onAdd={vi.fn()} onRemove={vi.fn()} onReorder={vi.fn()} language="en" />)
    const buttons = screen.getAllByRole('button')
    // Add + up + down + remove = 4 minimum
    expect(buttons.length).toBeGreaterThanOrEqual(4)
  })

  it('handles Enter key on step item', () => {
    const onSelect = vi.fn()
    render(<StepList steps={steps} selectedIndex={0} onSelect={onSelect} onAdd={vi.fn()} onRemove={vi.fn()} onReorder={vi.fn()} language="en" />)
    const stepItem = screen.getByText('Top').closest('[role="button"]')
    fireEvent.keyDown(stepItem, { key: 'Enter' })
    expect(onSelect).toHaveBeenCalledWith(1)
  })

  it('handles Space key on step item', () => {
    const onSelect = vi.fn()
    render(<StepList steps={steps} selectedIndex={0} onSelect={onSelect} onAdd={vi.fn()} onRemove={vi.fn()} onReorder={vi.fn()} language="en" />)
    const stepItem = screen.getByText('Top').closest('[role="button"]')
    fireEvent.keyDown(stepItem, { key: ' ' })
    expect(onSelect).toHaveBeenCalledWith(1)
  })

  it('handles string label', () => {
    const strLabel = [{ step: 1, label: 'Hello' }]
    render(<StepList steps={strLabel} selectedIndex={0} onSelect={vi.fn()} onAdd={vi.fn()} onRemove={vi.fn()} onReorder={vi.fn()} language="en" />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})

describe('StepDetailForm', () => {
  it('renders label and notes inputs', () => {
    render(<StepDetailForm step={steps[0]} index={0} onUpdate={vi.fn()} language="en" />)
    expect(screen.getByDisplayValue('Base')).toBeInTheDocument()
    expect(screen.getByDisplayValue('note1')).toBeInTheDocument()
  })

  it('calls onUpdate when label changes', () => {
    const onUpdate = vi.fn()
    render(<StepDetailForm step={steps[0]} index={0} onUpdate={onUpdate} language="en" />)
    fireEvent.change(screen.getByDisplayValue('Base'), { target: { value: 'New' } })
    expect(onUpdate).toHaveBeenCalledWith(0, { label: { en: 'New' } })
  })

  it('calls onUpdate when notes change', () => {
    const onUpdate = vi.fn()
    render(<StepDetailForm step={steps[0]} index={0} onUpdate={onUpdate} language="en" />)
    fireEvent.change(screen.getByDisplayValue('note1'), { target: { value: 'updated' } })
    expect(onUpdate).toHaveBeenCalledWith(0, { notes: { en: 'updated' } })
  })
})

describe('PartVisibilityPicker', () => {
  it('renders all parts', () => {
    render(<PartVisibilityPicker allParts={['bottom', 'top']} visibleParts={['bottom']} highlightParts={[]} onChange={vi.fn()} />)
    expect(screen.getByText('bottom')).toBeInTheDocument()
    expect(screen.getByText('top')).toBeInTheDocument()
  })

  it('toggles visibility via checkbox', () => {
    const onChange = vi.fn()
    render(<PartVisibilityPicker allParts={['bottom', 'top']} visibleParts={['bottom']} highlightParts={[]} onChange={onChange} />)
    // There are 4 checkboxes (2 visible + 2 highlight). Click the first visible checkbox (bottom)
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0]) // toggle bottom visible off
    expect(onChange).toHaveBeenCalledWith([], []) // removed from visible, highlight cleared too
  })

  it('adds part to visible', () => {
    const onChange = vi.fn()
    render(<PartVisibilityPicker allParts={['bottom', 'top']} visibleParts={['bottom']} highlightParts={[]} onChange={onChange} />)
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[2]) // toggle top visible on
    expect(onChange).toHaveBeenCalledWith(['bottom', 'top'], [])
  })

  it('toggles highlight for visible part', () => {
    const onChange = vi.fn()
    render(<PartVisibilityPicker allParts={['bottom', 'top']} visibleParts={['bottom', 'top']} highlightParts={['bottom']} onChange={onChange} />)
    const checkboxes = screen.getAllByRole('checkbox')
    // highlight checkboxes are at index 1, 3
    fireEvent.click(checkboxes[1]) // toggle bottom highlight off
    expect(onChange).toHaveBeenCalledWith(['bottom', 'top'], [])
  })
})

describe('CameraCaptureButton', () => {
  it('renders and calls onCapture', () => {
    const onCapture = vi.fn()
    render(<CameraCaptureButton onCapture={onCapture} />)
    fireEvent.click(screen.getByText('Capture Camera Position'))
    expect(onCapture).toHaveBeenCalled()
  })
})

describe('AssemblyEditorToolbar', () => {
  it('renders all buttons', () => {
    render(<AssemblyEditorToolbar isDirty={true} saving={false} onSave={vi.fn()} onDiscard={vi.fn()} onClose={vi.fn()} onPreview={vi.fn()} />)
    expect(screen.getByText('Save')).toBeInTheDocument()
    expect(screen.getByText('Discard')).toBeInTheDocument()
    expect(screen.getByText('Preview')).toBeInTheDocument()
    expect(screen.getByText('Close')).toBeInTheDocument()
  })

  it('disables save when not dirty', () => {
    render(<AssemblyEditorToolbar isDirty={false} saving={false} onSave={vi.fn()} onDiscard={vi.fn()} onClose={vi.fn()} onPreview={vi.fn()} />)
    expect(screen.getByText('Save').closest('button')).toBeDisabled()
  })

  it('shows Saving... when saving', () => {
    render(<AssemblyEditorToolbar isDirty={true} saving={true} onSave={vi.fn()} onDiscard={vi.fn()} onClose={vi.fn()} onPreview={vi.fn()} />)
    expect(screen.getByText('Saving...')).toBeInTheDocument()
  })

  it('calls onSave, onDiscard, onPreview, onClose', () => {
    const onSave = vi.fn(), onDiscard = vi.fn(), onPreview = vi.fn(), onClose = vi.fn()
    render(<AssemblyEditorToolbar isDirty={true} saving={false} onSave={onSave} onDiscard={onDiscard} onClose={onClose} onPreview={onPreview} />)
    fireEvent.click(screen.getByText('Save'))
    fireEvent.click(screen.getByText('Discard'))
    fireEvent.click(screen.getByText('Preview'))
    fireEvent.click(screen.getByText('Close'))
    expect(onSave).toHaveBeenCalled()
    expect(onDiscard).toHaveBeenCalled()
    expect(onPreview).toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })
})
