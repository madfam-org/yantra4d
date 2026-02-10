import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import PluginLoader from './PluginLoader'

describe('PluginLoader', () => {
  it('renders nothing when no url', () => {
    const { container } = render(<PluginLoader url={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows error for cross-origin url not on allowlist', async () => {
    // Current origin is http://localhost:3000 by default in test or similar
    // Function checks window.location.origin
    
    render(<PluginLoader url="https://evil.com/plugin.js" />)
    
    await waitFor(() => {
      expect(screen.getByText(/Plugin origin not allowed/)).toBeInTheDocument()
    })
  })

  it('shows loading state initially for valid url', async () => {
    // We need to bypass the security check for this test to pass if we use a fake URL
    // Or we use a relative URL which resolves to localhost
    
    // Mock import to avoid actual network request error
    // Note: 'import()' is hard to mock directly in some setups without specific transform
    // But since the component uses `import(url)`, if we pass a valid local URL, it might try to fetch.
    
    render(<PluginLoader url="/valid-plugin.js" />)
    expect(screen.getByText('Loading plugin…')).toBeInTheDocument()
  })
})
