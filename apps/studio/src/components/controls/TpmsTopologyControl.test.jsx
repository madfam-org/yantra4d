import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TpmsTopologyControl from './TpmsTopologyControl'

const defaultProps = {
  param: { id: 'tpms_type' },
  value: 0,
  onChange: vi.fn(),
  getLabel: () => 'TPMS Topology',
  language: 'en',
}

describe('TpmsTopologyControl', () => {
  it('renders label from getLabel', () => {
    render(<TpmsTopologyControl {...defaultProps} />)
    expect(screen.getByText('TPMS Topology')).toBeInTheDocument()
  })

  it('renders all three TPMS options', () => {
    render(<TpmsTopologyControl {...defaultProps} />)
    expect(screen.getByText('Gyroid')).toBeInTheDocument()
    expect(screen.getByText('Diamond')).toBeInTheDocument()
    expect(screen.getByText('Schwarz P')).toBeInTheDocument()
  })

  it('renders descriptions for each option', () => {
    render(<TpmsTopologyControl {...defaultProps} />)
    expect(screen.getByText('Labyrinthine lattice')).toBeInTheDocument()
    expect(screen.getByText('High stiffness network')).toBeInTheDocument()
    expect(screen.getByText('Cubic minimal surface')).toBeInTheDocument()
  })

  it('marks the active option with aria-pressed=true', () => {
    render(<TpmsTopologyControl {...defaultProps} value={0} />)
    expect(screen.getByText('Gyroid').closest('button')).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('Diamond').closest('button')).toHaveAttribute('aria-pressed', 'false')
  })

  it('applies primary styling to selected option', () => {
    render(<TpmsTopologyControl {...defaultProps} value={1} />)
    const diamondBtn = screen.getByText('Diamond').closest('button')
    expect(diamondBtn.className).toContain('bg-primary')
    const gyroidBtn = screen.getByText('Gyroid').closest('button')
    expect(gyroidBtn.className).toContain('bg-background')
  })

  it('calls onChange with param id and value array when option clicked', () => {
    const onChange = vi.fn()
    render(<TpmsTopologyControl {...defaultProps} onChange={onChange} />)
    fireEvent.click(screen.getByText('Diamond'))
    expect(onChange).toHaveBeenCalledWith('tpms_type', [1])
  })

  it('calls onChange with Schwarz P value when clicked', () => {
    const onChange = vi.fn()
    render(<TpmsTopologyControl {...defaultProps} onChange={onChange} />)
    fireEvent.click(screen.getByText('Schwarz P'))
    expect(onChange).toHaveBeenCalledWith('tpms_type', [2])
  })

  it('passes param and language to getLabel', () => {
    const getLabel = vi.fn(() => 'Custom Label')
    render(<TpmsTopologyControl {...defaultProps} getLabel={getLabel} language="es" />)
    expect(getLabel).toHaveBeenCalledWith(defaultProps.param, 'label', 'es')
    expect(screen.getByText('Custom Label')).toBeInTheDocument()
  })
})
