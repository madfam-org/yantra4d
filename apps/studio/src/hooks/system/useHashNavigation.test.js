import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'

// --- Mock react-router-dom ---
let mockPathname = '/'
let mockSearch = ''
const mockNavigate = vi.fn()

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: mockPathname, search: mockSearch }),
  useNavigate: () => mockNavigate,
}))

import {
  isDemoView,
  isProjectsView,
  parseHash,
  buildHash,
  useHashNavigation,
} from './useHashNavigation'

// --- Shared test fixtures ---
const modes = [
  { id: 'unit', label: 'Unit' },
  { id: 'grid', label: 'Grid' },
  { id: 'assembly', label: 'Assembly' },
]

const presets = [
  { id: 'default', label: 'Default', visible_in_modes: ['unit'] },
  { id: 'compact', label: 'Compact', visible_in_modes: ['unit', 'grid'] },
  { id: 'wide', label: 'Wide', visible_in_modes: ['grid'] },
]

beforeEach(() => {
  vi.clearAllMocks()
  mockPathname = '/'
  mockSearch = ''
})

// ========================================================================
// isDemoView
// ========================================================================
describe('isDemoView', () => {
  it('returns true for /demo path', () => {
    expect(isDemoView('/demo')).toBe(true)
  })

  it('returns true for /demo/something nested path', () => {
    expect(isDemoView('/demo/gridfinity')).toBe(true)
  })

  it('returns false for root path', () => {
    expect(isDemoView('/')).toBe(false)
  })

  it('returns false for empty string', () => {
    expect(isDemoView('')).toBe(false)
  })

  it('returns false for /project path', () => {
    expect(isDemoView('/project/slug')).toBe(false)
  })

  it('returns false for /projects path', () => {
    expect(isDemoView('/projects')).toBe(false)
  })

  it('returns false for path containing demo as substring', () => {
    expect(isDemoView('/demonstration')).toBe(false)
  })

  it('returns false for path with demo in a later segment', () => {
    expect(isDemoView('/project/demo')).toBe(false)
  })
})

// ========================================================================
// isProjectsView
// ========================================================================
describe('isProjectsView', () => {
  it('returns true for root path /', () => {
    expect(isProjectsView('/')).toBe(true)
  })

  it('returns true for empty string', () => {
    expect(isProjectsView('')).toBe(true)
  })

  it('returns true for /projects', () => {
    expect(isProjectsView('/projects')).toBe(true)
  })

  it('returns true for /demo path', () => {
    expect(isProjectsView('/demo')).toBe(true)
  })

  it('returns true for /demo/nested', () => {
    expect(isProjectsView('/demo/something')).toBe(true)
  })

  it('returns false for /project/slug (studio view)', () => {
    expect(isProjectsView('/project/gridfinity')).toBe(false)
  })

  it('returns false for /project/slug/mode/preset', () => {
    expect(isProjectsView('/project/gridfinity/unit/default')).toBe(false)
  })

  it('returns false for arbitrary non-matching path', () => {
    expect(isProjectsView('/settings')).toBe(false)
  })
})

// ========================================================================
// parseHash
// ========================================================================
describe('parseHash', () => {
  describe('with /project/ prefix paths', () => {
    it('parses slug + mode + preset from full path', () => {
      const result = parseHash('/project/gridfinity/unit/default', presets, modes)
      expect(result.mode.id).toBe('unit')
      expect(result.preset.id).toBe('default')
    })

    it('parses slug + mode without preset', () => {
      const result = parseHash('/project/gridfinity/grid', presets, modes)
      expect(result.mode.id).toBe('grid')
      // Falls back to first preset
      expect(result.preset.id).toBe('default')
    })

    it('parses slug only — falls back to first mode and first preset', () => {
      const result = parseHash('/project/gridfinity', presets, modes)
      expect(result.mode.id).toBe('unit')
      expect(result.preset.id).toBe('default')
    })
  })

  describe('with /projects/ prefix paths', () => {
    it('strips /projects/ prefix and parses remaining segments', () => {
      const result = parseHash('/projects/gridfinity/unit/compact', presets, modes)
      expect(result.mode.id).toBe('unit')
      expect(result.preset.id).toBe('compact')
    })
  })

  describe('with /demo prefix paths', () => {
    it('keeps demo as first segment — treats second segment as mode', () => {
      // /demo => parts = ['demo'], parts.length === 1, so modeId = null
      const result = parseHash('/demo', presets, modes)
      expect(result.mode.id).toBe('unit') // fallback to first mode
      expect(result.preset.id).toBe('default') // fallback to first preset
    })

    it('treats /demo/unit as demo + mode', () => {
      // /demo/unit => parts = ['demo', 'unit'] (demo prefix kept)
      // parts.length === 2, modeId = parts[1] = 'unit'
      const result = parseHash('/demo/unit', presets, modes)
      expect(result.mode.id).toBe('unit')
    })

    it('treats /demo/unit/compact as demo + mode + preset', () => {
      // /demo/unit/compact => parts = ['demo', 'unit', 'compact']
      // parts.length >= 3, modeId = parts[1] = 'unit', presetId = parts[2] = 'compact'
      const result = parseHash('/demo/unit/compact', presets, modes)
      expect(result.mode.id).toBe('unit')
      expect(result.preset.id).toBe('compact')
    })
  })

  describe('fallback behavior', () => {
    it('falls back to first mode when modeId does not match', () => {
      const result = parseHash('/project/slug/nonexistent', presets, modes)
      expect(result.mode.id).toBe('unit')
    })

    it('falls back to first preset when presetId does not match', () => {
      const result = parseHash('/project/slug/unit/nonexistent', presets, modes)
      expect(result.preset.id).toBe('default')
    })

    it('falls back to first mode and first preset on root path', () => {
      const result = parseHash('/', presets, modes)
      expect(result.mode.id).toBe('unit')
      expect(result.preset.id).toBe('default')
    })

    it('falls back to first mode and first preset on empty string', () => {
      const result = parseHash('', presets, modes)
      expect(result.mode.id).toBe('unit')
      expect(result.preset.id).toBe('default')
    })

    it('returns null mode when modes array is empty', () => {
      const result = parseHash('/project/slug/unit/default', presets, [])
      expect(result.mode).toBeNull()
    })

    it('returns null preset when presets array is empty', () => {
      const result = parseHash('/project/slug/unit/default', [], modes)
      expect(result.preset).toBeNull()
    })

    it('returns null for both when both arrays are empty', () => {
      const result = parseHash('/project/slug/unit', [], [])
      expect(result.mode).toBeNull()
      expect(result.preset).toBeNull()
    })
  })

  describe('preset visible_in_modes inference', () => {
    it('infers mode from preset visible_in_modes when mode does not match', () => {
      // /project/slug/badmode/wide => modeId = 'badmode' (no match),
      // presetId = 'wide' => preset.visible_in_modes = ['grid'] => mode = 'grid'
      const result = parseHash('/project/slug/badmode/wide', presets, modes)
      expect(result.mode.id).toBe('grid')
      expect(result.preset.id).toBe('wide')
    })

    it('falls back to first mode when preset has no visible_in_modes', () => {
      const presetsNoModes = [
        { id: 'bare', label: 'Bare' },
      ]
      const result = parseHash('/project/slug/badmode/bare', presetsNoModes, modes)
      expect(result.mode.id).toBe('unit') // first mode fallback
    })

    it('falls back to first mode when preset visible_in_modes is empty', () => {
      const presetsEmpty = [
        { id: 'bare', label: 'Bare', visible_in_modes: [] },
      ]
      const result = parseHash('/project/slug/badmode/bare', presetsEmpty, modes)
      expect(result.mode.id).toBe('unit')
    })
  })

  describe('edge cases in path parsing', () => {
    it('handles trailing slash', () => {
      const result = parseHash('/project/slug/unit/default/', presets, modes)
      expect(result.mode.id).toBe('unit')
      expect(result.preset.id).toBe('default')
    })

    it('handles multiple consecutive slashes', () => {
      const result = parseHash('///project///slug///unit', presets, modes)
      // filter(Boolean) strips empty segments, so parts = ['project','slug','unit']
      // after stripping /project/ prefix: ['slug', 'unit']
      // parts.length === 2, modeId = parts[1] = 'unit'
      expect(result.mode.id).toBe('unit')
    })

    it('handles extra path segments beyond preset', () => {
      const result = parseHash('/project/slug/unit/default/extra/segments', presets, modes)
      expect(result.mode.id).toBe('unit')
      expect(result.preset.id).toBe('default')
    })
  })
})

// ========================================================================
// buildHash
// ========================================================================
describe('buildHash', () => {
  it('builds path with project slug, mode, and preset', () => {
    expect(buildHash('gridfinity', 'unit', 'default'))
      .toBe('/project/gridfinity/unit/default')
  })

  it('builds path without preset when presetId is null', () => {
    expect(buildHash('gridfinity', 'unit', null))
      .toBe('/project/gridfinity/unit')
  })

  it('builds path without preset when presetId is undefined', () => {
    expect(buildHash('gridfinity', 'unit', undefined))
      .toBe('/project/gridfinity/unit')
  })

  it('builds path without preset when presetId is empty string', () => {
    // empty string is falsy, so presetId check fails
    expect(buildHash('gridfinity', 'unit', ''))
      .toBe('/project/gridfinity/unit')
  })

  it('handles slug with special characters', () => {
    expect(buildHash('my-cool-project', 'grid', 'compact'))
      .toBe('/project/my-cool-project/grid/compact')
  })
})

// ========================================================================
// useHashNavigation hook
// ========================================================================
describe('useHashNavigation', () => {
  const defaultProps = {
    presets,
    modes,
    projectSlug: 'gridfinity',
    onHashChange: vi.fn(),
  }

  function renderNav(overrides = {}) {
    return renderHook(() => useHashNavigation({ ...defaultProps, ...overrides }))
  }

  // ---------- currentView ----------
  describe('currentView', () => {
    it('returns "projects" for root path', () => {
      mockPathname = '/'
      const { result } = renderNav()
      expect(result.current.currentView).toBe('projects')
    })

    it('returns "projects" for /projects path', () => {
      mockPathname = '/projects'
      const { result } = renderNav()
      expect(result.current.currentView).toBe('projects')
    })

    it('returns "projects" for /demo path', () => {
      mockPathname = '/demo'
      const { result } = renderNav()
      expect(result.current.currentView).toBe('projects')
    })

    it('returns "studio" for /project/slug path', () => {
      mockPathname = '/project/gridfinity/unit/default'
      const { result } = renderNav()
      expect(result.current.currentView).toBe('studio')
    })

    it('returns "studio" for /project/slug/mode path', () => {
      mockPathname = '/project/gridfinity/grid'
      const { result } = renderNav()
      expect(result.current.currentView).toBe('studio')
    })
  })

  // ---------- isDemo ----------
  describe('isDemo', () => {
    it('returns true for /demo path', () => {
      mockPathname = '/demo'
      const { result } = renderNav()
      expect(result.current.isDemo).toBe(true)
    })

    it('returns true for /demo/something path', () => {
      mockPathname = '/demo/gridfinity'
      const { result } = renderNav()
      expect(result.current.isDemo).toBe(true)
    })

    it('returns false for root path', () => {
      mockPathname = '/'
      const { result } = renderNav()
      expect(result.current.isDemo).toBe(false)
    })

    it('returns false for /project path', () => {
      mockPathname = '/project/gridfinity/unit/default'
      const { result } = renderNav()
      expect(result.current.isDemo).toBe(false)
    })
  })

  // ---------- onHashChange callback ----------
  describe('onHashChange callback', () => {
    it('calls onHashChange with parsed mode and preset for studio paths', () => {
      mockPathname = '/project/gridfinity/unit/compact'
      const onHashChange = vi.fn()
      renderNav({ onHashChange })

      expect(onHashChange).toHaveBeenCalledWith({
        mode: expect.objectContaining({ id: 'unit' }),
        preset: expect.objectContaining({ id: 'compact' }),
      })
    })

    it('does not call onHashChange for projects view', () => {
      mockPathname = '/'
      const onHashChange = vi.fn()
      renderNav({ onHashChange })

      expect(onHashChange).not.toHaveBeenCalled()
    })

    it('does not call onHashChange for /demo path', () => {
      mockPathname = '/demo'
      const onHashChange = vi.fn()
      renderNav({ onHashChange })

      expect(onHashChange).not.toHaveBeenCalled()
    })

    it('does not call onHashChange when modes is empty', () => {
      mockPathname = '/project/gridfinity/unit/default'
      const onHashChange = vi.fn()
      renderNav({ onHashChange, modes: [] })

      expect(onHashChange).not.toHaveBeenCalled()
    })

    it('does not call onHashChange when modes is null', () => {
      mockPathname = '/project/gridfinity/unit/default'
      const onHashChange = vi.fn()
      renderNav({ onHashChange, modes: null })

      expect(onHashChange).not.toHaveBeenCalled()
    })

    it('handles onHashChange being undefined without error', () => {
      mockPathname = '/project/gridfinity/unit/default'
      expect(() => renderNav({ onHashChange: undefined })).not.toThrow()
    })
  })

  // ---------- navigate (initial path canonicalization) ----------
  describe('initial path canonicalization', () => {
    it('navigates to canonical path when path is incomplete', () => {
      mockPathname = '/project/gridfinity'
      renderNav()

      expect(mockNavigate).toHaveBeenCalledWith(
        '/project/gridfinity/unit/default',
        { replace: true }
      )
    })

    it('does not navigate when path already matches canonical', () => {
      mockPathname = '/project/gridfinity/unit/default'
      renderNav()

      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('does not navigate for projects view', () => {
      mockPathname = '/'
      renderNav()

      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('does not navigate for /projects view', () => {
      mockPathname = '/projects'
      renderNav()

      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('does not navigate when modes is empty', () => {
      mockPathname = '/project/gridfinity'
      renderNav({ modes: [] })

      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('preserves search params when navigating to canonical path', () => {
      mockPathname = '/project/gridfinity'
      mockSearch = '?p=abc123'
      renderNav()

      expect(mockNavigate).toHaveBeenCalledWith(
        '/project/gridfinity/unit/default?p=abc123',
        { replace: true }
      )
    })

    it('navigates with replace: true (not push)', () => {
      mockPathname = '/project/gridfinity'
      renderNav()

      const navigateCall = mockNavigate.mock.calls[0]
      expect(navigateCall[1]).toEqual({ replace: true })
    })
  })

  // ---------- return value shape ----------
  describe('return value', () => {
    it('returns object with currentView and isDemo properties', () => {
      mockPathname = '/project/gridfinity/unit/default'
      const { result } = renderNav()

      expect(result.current).toHaveProperty('currentView')
      expect(result.current).toHaveProperty('isDemo')
      expect(typeof result.current.currentView).toBe('string')
      expect(typeof result.current.isDemo).toBe('boolean')
    })
  })
})
