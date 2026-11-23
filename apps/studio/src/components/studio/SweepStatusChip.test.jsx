import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { axe } from '../../test/axe-setup'
import { toHaveNoViolations } from 'jest-axe'
import { LanguageProvider } from '../../contexts/system/LanguageProvider'
import SweepStatusChip from './SweepStatusChip'

expect.extend(toHaveNoViolations)

const FRAMES = [{ frame_index: 0, parts: [] }, { frame_index: 1, parts: [] }, { frame_index: 2, parts: [] }]

const player = (overrides = {}) => ({
  status: 'idle', sweep: { id: 'grow' }, progress: 0, frames: [], index: 0, error: null, exporting: false, loops: true,
  play: vi.fn(), cancel: vi.fn(), pause: vi.fn(), resume: vi.fn(), seek: vi.fn(), stop: vi.fn(), exportWebM: vi.fn(),
  ...overrides,
})

const renderChip = (p) => render(
  <LanguageProvider defaultLanguage="en" storageKey="test-lang-chip">
    <SweepStatusChip player={p} label="Grow" />
  </LanguageProvider>,
)

describe('SweepStatusChip', () => {
  it('renders nothing while no sweep is active', () => {
    const { container } = renderChip(player())
    expect(container).toBeEmptyDOMElement()
  })

  it('while rendering, shows progress and cancels', () => {
    const p = player({ status: 'rendering', progress: 37.6 })
    renderChip(p)
    expect(screen.getByText('Rendering frames · 38%')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Rendering the frames of Grow')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(p.cancel).toHaveBeenCalled()
  })

  it('while playing, names the sweep and the frame, and pauses or stops', () => {
    const p = player({ status: 'playing', frames: FRAMES, index: 1 })
    renderChip(p)
    expect(screen.getByRole('group', { name: 'Sweep playback' })).toHaveTextContent('Grow')
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(p.pause).toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Stop and show my configuration' }))
    expect(p.stop).toHaveBeenCalled()
  })

  it('while paused, resumes', () => {
    const p = player({ status: 'paused', frames: FRAMES })
    renderChip(p)
    expect(screen.getByRole('status')).toHaveTextContent('Grow paused')
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    expect(p.resume).toHaveBeenCalled()
  })

  it('offers no pause for a single frame', () => {
    renderChip(player({ status: 'paused', frames: [FRAMES[0]] }))
    expect(screen.queryByRole('button', { name: 'Play' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Stop and show my configuration' })).toBeInTheDocument()
  })

  it('on an error, says so and can be dismissed', () => {
    const p = player({ status: 'error', error: { code: 'render_failed' } })
    renderChip(p)
    expect(screen.getAllByText("The sweep's frames could not be rendered.").length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(p.stop).toHaveBeenCalled()
  })

  it('has no axe violations while playing', async () => {
    const { container } = renderChip(player({ status: 'playing', frames: FRAMES }))
    expect(await axe(container)).toHaveNoViolations()
  })
})
