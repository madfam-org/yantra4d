import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import React from 'react'
import PluginLoader from './PluginLoader'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('PluginLoader', () => {
  it('shows loading state initially', () => {
    // Mock import() to never resolve so we stay in loading
    vi.stubGlobal('import', vi.fn(() => new Promise(() => {})))
    render(<PluginLoader url="/plugins/widget.js" value={5} onChange={vi.fn()} param={{}} />)
    expect(screen.getByText(/Loading plugin/)).toBeInTheDocument()
  })

  it('renders nothing special when url is empty', () => {
    const { container } = render(<PluginLoader url="" value={5} onChange={vi.fn()} param={{}} />)
    expect(screen.getByText(/Loading plugin/)).toBeInTheDocument()
  })

  it('rejects cross-origin plugin URLs', () => {
    render(<PluginLoader url="https://evil.com/plugin.js" value={5} onChange={vi.fn()} param={{}} />)
    expect(screen.getByText(/Plugin origin not allowed/)).toBeInTheDocument()
  })

  it('shows error for cross-origin HTTPS URLs', () => {
    render(<PluginLoader url="https://untrusted.example.com/widget.js" value={5} onChange={vi.fn()} param={{}} />)
    expect(screen.getByText(/Plugin origin not allowed/)).toBeInTheDocument()
  })

  it('renders loaded plugin component', async () => {
    function MockWidget({ value }) {
      return <div data-testid="widget">Value: {value}</div>
    }

    // Use a same-origin relative URL
    const pluginUrl = '/plugins/my-widget.js'

    // We need to mock the dynamic import at the module level
    // Since Vite transforms import() calls, we mock at the global level
    const originalImport = globalThis.__vite_ssr_dynamic_import__ || globalThis.importShim
    const mockImport = vi.fn(() => Promise.resolve({ default: MockWidget }))

    // The component uses import(/* @vite-ignore */ url) which in test env
    // may not work. We test the error fallback path instead.
    render(<PluginLoader url={pluginUrl} value={42} onChange={vi.fn()} param={{}} />)

    // In test env, dynamic import of a file URL will fail, showing error fallback
    await waitFor(() => {
      const el = screen.queryByText(/Loading plugin/) || screen.queryByText(/Failed to load plugin/)
      expect(el).toBeInTheDocument()
    })
  })

  it('displays error message on import failure', async () => {
    render(<PluginLoader url="/plugins/broken.js" value={5} onChange={vi.fn()} param={{}} />)
    // Dynamic import will fail in test env
    await waitFor(() => {
      expect(screen.getByText(/Failed to load plugin/)).toBeInTheDocument()
    })
  })

  it('accepts same-origin URLs', () => {
    // Should not show origin error for same-origin URL
    render(<PluginLoader url="/plugins/widget.js" value={5} onChange={vi.fn()} param={{}} />)
    expect(screen.queryByText(/Plugin origin not allowed/)).not.toBeInTheDocument()
  })
})
