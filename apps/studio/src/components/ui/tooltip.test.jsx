import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { Tooltip } from './tooltip'

// jsdom doesn't have PointerEvent; polyfill for tests
if (typeof globalThis.PointerEvent === 'undefined') {
  globalThis.PointerEvent = class PointerEvent extends MouseEvent {
    constructor(type, params = {}) {
      super(type, params)
      this.pointerType = params.pointerType || ''
    }
  }
}

describe('Tooltip', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders children without tooltip when content is empty', () => {
    render(<Tooltip content="">{<button>Click me</button>}</Tooltip>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('renders children without tooltip when content is null', () => {
    render(<Tooltip content={null}>{<button>Click me</button>}</Tooltip>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('shows tooltip on mouse enter after delay', () => {
    render(
      <Tooltip content="Help text">
        <button>Hover me</button>
      </Tooltip>
    )

    fireEvent.mouseEnter(screen.getByText('Hover me').parentElement)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(200)
    })

    expect(screen.getByRole('tooltip')).toHaveTextContent('Help text')
  })

  it('hides tooltip on mouse leave', () => {
    render(
      <Tooltip content="Help text">
        <button>Hover me</button>
      </Tooltip>
    )

    const wrapper = screen.getByText('Hover me').parentElement
    fireEvent.mouseEnter(wrapper)
    act(() => { vi.advanceTimersByTime(200) })
    expect(screen.getByRole('tooltip')).toBeInTheDocument()

    fireEvent.mouseLeave(wrapper)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('shows tooltip on focus', () => {
    render(
      <Tooltip content="Focus text">
        <button>Focus me</button>
      </Tooltip>
    )

    fireEvent.focus(screen.getByText('Focus me').parentElement)
    act(() => { vi.advanceTimersByTime(200) })

    expect(screen.getByRole('tooltip')).toHaveTextContent('Focus text')
  })

  it('hides tooltip on blur', () => {
    render(
      <Tooltip content="Focus text">
        <button>Focus me</button>
      </Tooltip>
    )

    const wrapper = screen.getByText('Focus me').parentElement
    fireEvent.focus(wrapper)
    act(() => { vi.advanceTimersByTime(200) })
    expect(screen.getByRole('tooltip')).toBeInTheDocument()

    fireEvent.blur(wrapper)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('toggles tooltip on touch pointer down', () => {
    render(
      <Tooltip content="Touch text">
        <button>Tap me</button>
      </Tooltip>
    )

    const wrapper = screen.getByText('Tap me').parentElement

    // First touch opens tooltip
    act(() => {
      wrapper.dispatchEvent(new PointerEvent('pointerdown', { pointerType: 'touch', bubbles: true }))
    })
    expect(screen.getByRole('tooltip')).toHaveTextContent('Touch text')

    // Second touch closes tooltip
    act(() => {
      wrapper.dispatchEvent(new PointerEvent('pointerdown', { pointerType: 'touch', bubbles: true }))
    })
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('auto-dismisses tooltip after 2 seconds on touch', () => {
    render(
      <Tooltip content="Auto dismiss">
        <button>Tap me</button>
      </Tooltip>
    )

    const wrapper = screen.getByText('Tap me').parentElement
    act(() => {
      wrapper.dispatchEvent(new PointerEvent('pointerdown', { pointerType: 'touch', bubbles: true }))
    })
    expect(screen.getByRole('tooltip')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('does not toggle on mouse pointer down (only touch)', () => {
    render(
      <Tooltip content="No toggle">
        <button>Click me</button>
      </Tooltip>
    )

    const wrapper = screen.getByText('Click me').parentElement
    act(() => {
      wrapper.dispatchEvent(new PointerEvent('pointerdown', { pointerType: 'mouse', bubbles: true }))
    })
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('sets aria-describedby when tooltip is visible', () => {
    render(
      <Tooltip content="Accessible">
        <button>Hover me</button>
      </Tooltip>
    )

    const wrapper = screen.getByText('Hover me').parentElement
    expect(wrapper).not.toHaveAttribute('aria-describedby')

    fireEvent.mouseEnter(wrapper)
    act(() => { vi.advanceTimersByTime(200) })

    expect(wrapper).toHaveAttribute('aria-describedby')
    const tooltipId = wrapper.getAttribute('aria-describedby')
    expect(screen.getByRole('tooltip')).toHaveAttribute('id', tooltipId)
  })
})
