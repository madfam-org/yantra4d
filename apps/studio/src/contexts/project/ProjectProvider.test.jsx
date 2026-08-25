import { useEffect } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { renderHook } from '@testing-library/react'

// ProjectProvider composes four large hooks. They have their own specs; what is
// under test here is the provider's own logic — the splash gate that decides
// whether the requested project's manifest has arrived yet, and the contract
// that useProject outside a provider fails loudly instead of returning
// undefined and breaking somewhere further away.

const manifestState = {
  projectSlug: 'gridfinity',
  manifest: { project: { slug: 'gridfinity' } },
  manifestError: null,
}

vi.mock('./ManifestProvider', () => ({
  useManifest: () => manifestState,
}))

vi.mock('../system/LanguageProvider', () => ({
  useLanguage: () => ({ t: (k) => k, language: 'en' }),
}))

vi.mock('../../hooks/project/useProjectParams', () => ({
  // The job handlers below call setLoading and read parts, so the stub has to
  // carry them — otherwise handleRunPhysics throws before it reaches fetch.
  useProjectParams: () => ({
    mode: 'cup',
    params: {},
    setParams: vi.fn(),
    colors: {},
    parts: [{ type: 'body', url: 'blob:body' }],
    setLoading: vi.fn(),
    setLogs: vi.fn(),
    setParts: vi.fn(),
  }),
}))

vi.mock('../../hooks/project/useProjectActions', () => ({
  useProjectActions: () => ({}),
}))

vi.mock('../../hooks/editor/useAssemblyGuide', () => ({
  useAssemblyGuide: () => ({}),
}))

vi.mock('../../components/feedback/SplashScreen', () => ({
  default: function MockSplash({ exiting }) {
    return <div data-testid="splash" data-exiting={String(!!exiting)} />
  },
}))

import { ProjectProvider, useProject } from './ProjectProvider'

// Defined at module scope: a component that writes to an outer binding during
// render is fine for a probe, but only if it is a real top-level component.
const captured = { ctx: null }

function Capture() {
  const ctx = useProject()
  // Assigned in an effect, not during render: the React Compiler lint forbids
  // writing to an outer binding while rendering, and it would be a real hazard
  // under concurrent rendering.
  useEffect(() => { captured.ctx = ctx }, [ctx])
  return (
    <div
      data-testid="job-state"
      data-physics-id={String(ctx.physicsJobId)}
      data-physics-progress={String(ctx.physicsProgress)}
      data-opt-id={String(ctx.optimizationJobId)}
      data-opt-progress={String(ctx.optimizationProgress)}
    />
  )
}

function Probe() {
  const ctx = useProject()
  return <div data-testid="probe" data-mode={ctx.mode} />
}

beforeEach(() => {
  manifestState.projectSlug = 'gridfinity'
  manifestState.manifest = { project: { slug: 'gridfinity' } }
  manifestState.manifestError = null
  vi.useRealTimers()
})

describe('ProjectProvider', () => {
  it('renders children once the manifest matches the requested project', () => {
    render(<ProjectProvider><Probe /></ProjectProvider>)
    expect(screen.getByTestId('probe')).toBeInTheDocument()
    expect(screen.queryByTestId('splash')).not.toBeInTheDocument()
  })

  it('holds the splash while the loaded manifest belongs to another project', () => {
    // The fallback manifest loads instantly; showing one project's UI against
    // another's manifest would render the wrong geometry, so the provider waits.
    manifestState.projectSlug = 'nema-mount'
    manifestState.manifest = { project: { slug: 'gridfinity' } }

    render(<ProjectProvider><Probe /></ProjectProvider>)
    expect(screen.getByTestId('splash')).toBeInTheDocument()
    expect(screen.queryByTestId('probe')).not.toBeInTheDocument()
  })

  it('does not hold the splash when the manifest failed to load', () => {
    // With an error there is no correct manifest coming, so waiting forever
    // would strand the user on a splash screen. The error page takes over.
    manifestState.projectSlug = 'nema-mount'
    manifestState.manifest = { project: { slug: 'gridfinity' } }
    manifestState.manifestError = 'network_error'

    render(<ProjectProvider><Probe /></ProjectProvider>)
    expect(screen.queryByTestId('splash')).not.toBeInTheDocument()
    expect(screen.getByTestId('probe')).toBeInTheDocument()
  })

  it('does not hold the splash before a project has been chosen', () => {
    // Views that do not depend on a manifest, such as the catalog, must render
    // immediately rather than waiting on a slug that will never arrive.
    manifestState.projectSlug = null
    manifestState.manifest = { project: { slug: 'gridfinity' } }

    render(<ProjectProvider><Probe /></ProjectProvider>)
    expect(screen.getByTestId('probe')).toBeInTheDocument()
  })

  it('does not hold the splash when the manifest declares no slug', () => {
    manifestState.projectSlug = 'gridfinity'
    manifestState.manifest = { project: {} }

    render(<ProjectProvider><Probe /></ProjectProvider>)
    expect(screen.getByTestId('probe')).toBeInTheDocument()
  })

  it('fades the splash out before revealing the project', () => {
    vi.useFakeTimers()
    manifestState.projectSlug = 'nema-mount'
    manifestState.manifest = { project: { slug: 'gridfinity' } }

    const { rerender } = render(<ProjectProvider><Probe /></ProjectProvider>)
    expect(screen.getByTestId('splash')).toHaveAttribute('data-exiting', 'false')

    // The correct manifest arrives.
    manifestState.manifest = { project: { slug: 'nema-mount' } }
    rerender(<ProjectProvider><Probe /></ProjectProvider>)
    expect(screen.getByTestId('splash')).toHaveAttribute('data-exiting', 'true')

    act(() => { vi.advanceTimersByTime(300) })
    expect(screen.queryByTestId('splash')).not.toBeInTheDocument()
    expect(screen.getByTestId('probe')).toBeInTheDocument()
  })

  it('useProject outside a provider throws rather than returning undefined', () => {
    // Silence the error React logs for the thrown render.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => { })
    expect(() => renderHook(() => useProject())).toThrow()
    spy.mockRestore()
  })

  // --- Simulation jobs ------------------------------------------------------
  // handleRunPhysics and handleOptimizeTopology each start a job and then poll
  // for it. None of that ran: no test reached the provider at all.

  const jobState = (attr) => screen.getByTestId('job-state').getAttribute(attr)

  const renderProvider = () => render(<ProjectProvider><Capture /></ProjectProvider>)

  const mockFetchSequence = (responses) => {
    let i = 0
    return vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      const next = responses[Math.min(i, responses.length - 1)]
      i += 1
      return Promise.resolve({ ok: next.ok !== false, json: () => Promise.resolve(next.body) })
    })
  }

  it('a physics start that returns no job id leaves no job running', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => { })
    mockFetchSequence([{ ok: false, body: { error: 'no solver' } }])
    renderProvider()

    await act(async () => { await captured.ctx.handleRunPhysics() })
    expect(jobState('data-physics-id')).toBe('null')
    spy.mockRestore()
  })

  it('a failed physics job stops polling instead of spinning forever', async () => {
    vi.useFakeTimers()
    const spy = vi.spyOn(console, 'error').mockImplementation(() => { })
    mockFetchSequence([
      { body: { job_id: 'phys-1' } },
      { body: { status: 'failed', error: 'diverged' } },
    ])
    renderProvider()

    await act(async () => { await captured.ctx.handleRunPhysics() })
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(jobState('data-physics-id')).toBe('null')
    spy.mockRestore()
  })

  it('starting a topology optimization records its job id', async () => {
    mockFetchSequence([{ body: { job_id: 'opt-1' } }])
    renderProvider()

    await act(async () => { await captured.ctx.handleOptimizeTopology() })
    expect(jobState('data-opt-id')).toBe('opt-1')
  })

  it('running FEA records the returned simulation', async () => {
    mockFetchSequence([{ body: { status: 'success', simulation: { max_stress: 12 } } }])
    renderProvider()

    await act(async () => { await captured.ctx.handleRunFEA() })
    expect(captured.ctx.stressData).toMatchObject({ max_stress: 12 })
  })
})

