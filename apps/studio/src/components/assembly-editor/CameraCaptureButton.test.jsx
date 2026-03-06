import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import CameraCaptureButton from './CameraCaptureButton'

expect.extend(toHaveNoViolations)

describe('CameraCaptureButton', () => {
  it('renders the capture button with label', () => {
    render(<CameraCaptureButton onCapture={vi.fn()} />)
    expect(screen.getByText('Capture Camera Position')).toBeInTheDocument()
  })

  it('renders the instructional help text', () => {
    render(<CameraCaptureButton onCapture={vi.fn()} />)
    expect(screen.getByText(/Orbit the 3D view first/)).toBeInTheDocument()
  })

  it('calls onCapture when button is clicked', () => {
    const onCapture = vi.fn()
    render(<CameraCaptureButton onCapture={onCapture} />)
    fireEvent.click(screen.getByText('Capture Camera Position'))
    expect(onCapture).toHaveBeenCalledTimes(1)
  })

  it('does not call onCapture on render', () => {
    const onCapture = vi.fn()
    render(<CameraCaptureButton onCapture={onCapture} />)
    expect(onCapture).not.toHaveBeenCalled()
  })

  it('calls onCapture on each click', () => {
    const onCapture = vi.fn()
    render(<CameraCaptureButton onCapture={onCapture} />)
    const button = screen.getByText('Capture Camera Position')
    fireEvent.click(button)
    fireEvent.click(button)
    fireEvent.click(button)
    expect(onCapture).toHaveBeenCalledTimes(3)
  })

  it('has no accessibility violations', async () => {
    const { container } = render(<CameraCaptureButton onCapture={vi.fn()} />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
