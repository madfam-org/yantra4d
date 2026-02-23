import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import EnergySliderControl from './EnergySliderControl'

const defaultThermo = {
  glass_transition_temp: 60,
  melting_temp: 200,
}

const defaultProps = {
  value: 25,
  onChange: vi.fn(),
  thermodynamics: defaultThermo,
  language: 'en',
}

function renderEnergy(overrides = {}) {
  return render(<EnergySliderControl {...defaultProps} {...overrides} />)
}

describe('EnergySliderControl', () => {
  it('returns null when thermodynamics is null', () => {
    const { container } = render(
      <EnergySliderControl value={25} onChange={vi.fn()} thermodynamics={null} language="en" />
    )
    expect(container.innerHTML).toBe('')
  })

  it('returns null when thermodynamics is undefined', () => {
    const { container } = render(
      <EnergySliderControl value={25} onChange={vi.fn()} thermodynamics={undefined} language="en" />
    )
    expect(container.innerHTML).toBe('')
  })

  it('renders the energy simulation label in English', () => {
    renderEnergy()
    expect(screen.getByText('Energy Simulation (Digital Twin)')).toBeInTheDocument()
  })

  it('renders the energy simulation label in Spanish', () => {
    renderEnergy({ language: 'es' })
    expect(screen.getByText('Simulación de Energía (Digital Twin)')).toBeInTheDocument()
  })

  it('shows Rigid Solid state for low temperature (green)', () => {
    renderEnergy({ value: 10 })
    expect(screen.getByText('Rigid Solid')).toBeInTheDocument()
  })

  it('shows Approaching Transition Limit for near-Tg temperature (yellow)', () => {
    // Tg=60, 0.8*60=48. Value 50 >= 48 but < 60
    renderEnergy({ value: 50 })
    expect(screen.getByText('Approaching Transition Limit')).toBeInTheDocument()
  })

  it('shows Structural Deformation for temperature at/above Tg (red)', () => {
    renderEnergy({ value: 60 })
    expect(screen.getByText('Structural Deformation (Collapse)')).toBeInTheDocument()
  })

  it('shows Spanish state labels when language is es', () => {
    renderEnergy({ value: 60, language: 'es' })
    expect(screen.getByText('Deformación Estructural (Colapso)')).toBeInTheDocument()
  })

  it('shows Spanish near-transition label', () => {
    renderEnergy({ value: 50, language: 'es' })
    expect(screen.getByText('Cerca del Límite de Transición')).toBeInTheDocument()
  })

  it('shows Spanish rigid label', () => {
    renderEnergy({ value: 10, language: 'es' })
    expect(screen.getByText('Sólido Rígido')).toBeInTheDocument()
  })

  it('displays current temperature and Tg values', () => {
    renderEnergy({ value: 42 })
    expect(screen.getByText('Current: 42°C')).toBeInTheDocument()
    expect(screen.getByText('Tg: 60°C')).toBeInTheDocument()
  })

  it('displays 0°C when value is falsy', () => {
    renderEnergy({ value: 0 })
    expect(screen.getByText('Current: 0°C')).toBeInTheDocument()
  })

  it('uses default Tg=100 when glass_transition_temp is missing', () => {
    renderEnergy({ thermodynamics: { melting_temp: 200 }, value: 85 })
    // Tg defaults to 100, 0.8*100=80. value=85 >= 80 but < 100
    expect(screen.getByText('Approaching Transition Limit')).toBeInTheDocument()
    expect(screen.getByText('Tg: 100°C')).toBeInTheDocument()
  })

  it('uses default melting_temp=200 when missing', () => {
    renderEnergy({ thermodynamics: { glass_transition_temp: 60 } })
    // maxTemp = (200 || 200) + 50 = 250
    expect(screen.getByText('250°C')).toBeInTheDocument()
  })

  it('calls onChange with simulated_energy and float value', () => {
    const onChange = vi.fn()
    renderEnergy({ onChange })
    const slider = screen.getByRole('slider')
    fireEvent.change(slider, { target: { value: '75' } })
    expect(onChange).toHaveBeenCalledWith('simulated_energy', 75)
  })

  it('renders max temperature label from thermodynamics', () => {
    renderEnergy({ thermodynamics: { glass_transition_temp: 60, melting_temp: 300 } })
    // maxTemp = 300 + 50 = 350
    expect(screen.getByText('350°C')).toBeInTheDocument()
  })
})
