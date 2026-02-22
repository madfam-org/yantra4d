import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import SynthesisModal from './SynthesisModal'

describe('SynthesisModal', () => {
  const mockOnOpenChange = vi.fn()
  const mockOnSynthesisComplete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders correctly when open', () => {
    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )
    
    expect(screen.getByText('Hyperobject Synthesis Engine')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Generate a stackable slide-holder/i)).toBeInTheDocument()
    expect(screen.getByText('Generate Cartridge')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    const { container } = render(
      <SynthesisModal
        open={false}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('handles input and generation', async () => {
    // Setup a mock SSE stream response
    const encoder = new TextEncoder()
    const mockEvents = [
      'data: {"event": "chunk", "text": "Thinking..."}\n\n',
      'data: {"event": "cartridge", "slug": "generated-slug"}\n\n'
    ]
    
    // Create a mock stream reader
    let eventIndex = 0
    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (eventIndex < mockEvents.length) {
          const value = encoder.encode(mockEvents[eventIndex++])
          return Promise.resolve({ done: false, value })
        }
        return Promise.resolve({ done: true })
      })
    }
    
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (url.toString().includes('/api/ai/synthesize')) {
        return {
          ok: true,
          body: {
            getReader: () => mockReader
          }
        }
      }
      return { ok: true }
    })

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )
    
    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Make a cube' } })
    
    const generateBtn = screen.getByText('Generate Cartridge')
    fireEvent.click(generateBtn)
    
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    
    await waitFor(() => {
      expect(mockOnSynthesisComplete).toHaveBeenCalledWith('generated-slug')
      expect(mockOnOpenChange).toHaveBeenCalledWith(false)
    }, { timeout: 3000 })
  })
})
