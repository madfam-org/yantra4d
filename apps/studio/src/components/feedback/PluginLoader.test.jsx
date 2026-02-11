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
    render(<PluginLoader url="not-a-url" />)
    expect(await screen.findByText(/Failed to load plugin/)).toBeInTheDocument()
  })

  // Note: Testing successful plugin loading via dynamic import would require
  // complex mocking of the native import() keyword which is out of scope 
  // for this test environment.
})
