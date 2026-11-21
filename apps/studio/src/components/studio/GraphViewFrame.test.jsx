import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key, params) => (params ? `${key}(${Object.values(params).join(',')})` : key) }),
}))
// The panel is tested on its own; here it only reports what the frame hands it.
vi.mock('./InsidePanel', () => ({
  default: (props) => (
    <div
      data-testid="inside-panel-stub"
      data-status={props.state.status}
      data-active={props.activeParamId ?? ''}
      data-bindings={JSON.stringify(props.bindings)}
    >
      <button type="button" onClick={props.onRetry}>retry</button>
    </div>
  ),
}))
vi.mock('../../services/domain/graphViewService', () => ({ fetchModeGraph: vi.fn() }))

import GraphViewFrame, { CHANGE_HIGHLIGHT_MS } from './GraphViewFrame'
import { fetchModeGraph } from '../../services/domain/graphViewService'
import { clearModeGraphCache } from '../../hooks/project/useModeGraph'

const GRAPH = { mode: 'flange', path: 'flange.graph.json', role: 'source', script: null, content: '{"nodes":[],"outputs":{}}' }
const PARAMS = [
  { id: 'plate_radius', type: 'slider', default: 45, binding: 'outline.r' },
  { id: 'thickness', type: 'slider', default: 8, binding: 'plate.height' },
]

function Frame(props) {
  return (
    <GraphViewFrame
      slug="flange-plate"
      mode="flange"
      isDesktop
      parameters={PARAMS}
      values={{ plate_radius: 45, thickness: 8 }}
      hoveredParamId={null}
      labelOf={(id) => id}
      {...props}
    >
      <div data-testid="viewer-stub" />
    </GraphViewFrame>
  )
}

beforeEach(() => {
  clearModeGraphCache()
  fetchModeGraph.mockReset()
  fetchModeGraph.mockResolvedValue(GRAPH)
  try { localStorage.clear() } catch { /* jsdom storage */ }
})
afterEach(() => vi.useRealTimers())

describe('GraphViewFrame on desktop', () => {
  it('starts with the 3D view alone and costs no request', () => {
    render(<Frame />)
    expect(screen.getByTestId('viewer-stub')).toBeVisible()
    expect(screen.queryByTestId('graph-view-inside')).toBeNull()
    expect(fetchModeGraph).not.toHaveBeenCalled()
  })

  it('opens Inside beside the 3D view, which stays on screen', async () => {
    render(<Frame />)
    fireEvent.click(screen.getByTestId('inside-toggle'))
    expect(screen.getByTestId('graph-view-inside')).toBeInTheDocument()
    expect(screen.getByTestId('graph-view-3d')).not.toHaveClass('hidden')
    await waitFor(() => expect(screen.getByTestId('inside-panel-stub').dataset.status).toBe('ready'))
    expect(fetchModeGraph).toHaveBeenCalledWith('flange-plate', 'flange', expect.any(AbortSignal))
  })

  it('remembers that it was open', () => {
    const { unmount } = render(<Frame />)
    fireEvent.click(screen.getByTestId('inside-toggle'))
    unmount()
    render(<Frame />)
    expect(screen.getByTestId('graph-view-inside')).toBeInTheDocument()
  })

  it('hands the panel the manifest bindings', () => {
    render(<Frame />)
    fireEvent.click(screen.getByTestId('inside-toggle'))
    expect(JSON.parse(screen.getByTestId('inside-panel-stub').dataset.bindings)).toEqual({
      plate_radius: ['outline.r'], thickness: ['plate.height'],
    })
  })

  it('does not fetch a graph twice for the same mode', async () => {
    render(<Frame />)
    fireEvent.click(screen.getByTestId('inside-toggle'))
    await waitFor(() => expect(screen.getByTestId('inside-panel-stub').dataset.status).toBe('ready'))
    fireEvent.click(screen.getByTestId('inside-toggle'))
    fireEvent.click(screen.getByTestId('inside-toggle'))
    expect(screen.getByTestId('inside-panel-stub').dataset.status).toBe('ready')
    expect(fetchModeGraph).toHaveBeenCalledTimes(1)
  })

  it('reports a failed load and retries on request', async () => {
    fetchModeGraph.mockRejectedValueOnce(new Error('offline'))
    render(<Frame />)
    fireEvent.click(screen.getByTestId('inside-toggle'))
    await waitFor(() => expect(screen.getByTestId('inside-panel-stub').dataset.status).toBe('error'))
    fireEvent.click(screen.getByText('retry'))
    await waitFor(() => expect(screen.getByTestId('inside-panel-stub').dataset.status).toBe('ready'))
    expect(fetchModeGraph).toHaveBeenCalledTimes(2)
  })
})

describe('GraphViewFrame on a phone', () => {
  it('switches between 3D and Inside, keeping the viewer mounted', async () => {
    render(<Frame isDesktop={false} />)
    expect(screen.queryByTestId('inside-toggle')).toBeNull()
    fireEvent.click(screen.getByRole('radio', { name: /inside.toggle/ }))
    expect(screen.getByTestId('graph-view-3d')).toHaveClass('hidden')
    expect(screen.getByTestId('viewer-stub')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('inside-panel-stub').dataset.status).toBe('ready'))
    fireEvent.click(screen.getByRole('radio', { name: /inside.view_3d/ }))
    expect(screen.queryByTestId('graph-view-inside')).toBeNull()
    expect(screen.getByTestId('graph-view-3d')).not.toHaveClass('hidden')
  })
})

describe('GraphViewFrame: which parameter is active', () => {
  it('follows the hovered parameter', () => {
    render(<Frame hoveredParamId="thickness" />)
    fireEvent.click(screen.getByTestId('inside-toggle'))
    expect(screen.getByTestId('inside-panel-stub').dataset.active).toBe('thickness')
  })

  it('marks a changed parameter for a while after it changes', () => {
    vi.useFakeTimers()
    const { rerender } = render(<Frame />)
    fireEvent.click(screen.getByTestId('inside-toggle'))
    rerender(<Frame values={{ plate_radius: 50, thickness: 8 }} />)
    expect(screen.getByTestId('inside-panel-stub').dataset.active).toBe('plate_radius')
    act(() => { vi.advanceTimersByTime(CHANGE_HIGHLIGHT_MS + 10) })
    expect(screen.getByTestId('inside-panel-stub').dataset.active).toBe('')
  })

  it('marks nothing when a preset changes several values at once', () => {
    const { rerender } = render(<Frame />)
    fireEvent.click(screen.getByTestId('inside-toggle'))
    rerender(<Frame values={{ plate_radius: 50, thickness: 10 }} />)
    expect(screen.getByTestId('inside-panel-stub').dataset.active).toBe('')
  })

  it('the hovered parameter wins over a recent change', () => {
    const { rerender } = render(<Frame />)
    fireEvent.click(screen.getByTestId('inside-toggle'))
    rerender(<Frame values={{ plate_radius: 50, thickness: 8 }} hoveredParamId="thickness" />)
    expect(screen.getByTestId('inside-panel-stub').dataset.active).toBe('thickness')
  })
})
