import { render, screen } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import PluginLoader from './PluginLoader'

describe('PluginLoader', () => {
  const mockOrigin = 'http://localhost:3000'

  beforeEach(() => {
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: {
        origin: mockOrigin,
        href: mockOrigin + '/',
      },
      writable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders nothing when no url is provided', () => {
    const { container } = render(<PluginLoader url="" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows error for cross-origin URLs not in allowlist', async () => {
    render(<PluginLoader url="http://evil.com/plugin.js" />)
    // Wait for validation effect
    expect(await screen.findByText(/Plugin origin not allowed/)).toBeInTheDocument()
    expect(screen.getByText(/http:\/\/evil.com/)).toBeInTheDocument()
  })

  it('shows error for invalid URLs', async () => {
    // Suppress console.error for this test as Vite will log the import error
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => { })
    render(<PluginLoader url="not-a-url" />)
    expect(await screen.findByText(/Failed to load plugin/)).toBeInTheDocument()
    consoleSpy.mockRestore()
  })

  it('shows loading state initially', () => {
    render(<PluginLoader url="http://localhost:3000/valid.js" />)
    expect(screen.getByText(/Loading plugin/)).toBeInTheDocument()
  })
})
