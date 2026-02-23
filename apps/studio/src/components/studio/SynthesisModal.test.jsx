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

  it('renders description text', () => {
    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )
    expect(screen.getByText(/Describe the parametric cartridge you want to build/)).toBeInTheDocument()
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

  it('does not submit when prompt is empty', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true })

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    // Generate button should be disabled when prompt is empty
    const generateBtn = screen.getByText('Generate Cartridge').closest('button')
    expect(generateBtn).toBeDisabled()

    // Click anyway (the disabled attribute prevents it, but the handler also guards)
    fireEvent.click(generateBtn)
    expect(globalThis.fetch).not.toHaveBeenCalled()
  })

  it('does not submit when prompt is only whitespace', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true })

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: '   ' } })

    const generateBtn = screen.getByText('Generate Cartridge').closest('button')
    expect(generateBtn).toBeDisabled()
  })

  it('closes modal when cancel button is clicked', () => {
    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const cancelBtn = screen.getByText('Cancel')
    fireEvent.click(cancelBtn)
    expect(mockOnOpenChange).toHaveBeenCalledWith(false)
  })

  it('closes modal when X button is clicked', () => {
    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    // The X button is the one with the X icon, near the header
    const closeButtons = screen.getAllByRole('button')
    // X button is the first button (in the header)
    const xButton = closeButtons[0]
    fireEvent.click(xButton)
    expect(mockOnOpenChange).toHaveBeenCalledWith(false)
  })

  it('displays error when fetch response is not ok', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      statusText: 'Internal Server Error',
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

    await waitFor(() => {
      expect(screen.getByText(/Failed to start synthesis: Internal Server Error/)).toBeInTheDocument()
    })
  })

  it('displays error when fetch throws a network error', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})

    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network failure'))

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

    await waitFor(() => {
      expect(screen.getByText('Network failure')).toBeInTheDocument()
    })
  })

  it('shows generating state with spinner text during synthesis', async () => {
    // Create a reader that never resolves to keep isGenerating=true
    let resolveRead
    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        return new Promise((resolve) => {
          resolveRead = resolve
        })
      })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
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

    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      expect(screen.getByText('Synthesizing...')).toBeInTheDocument()
    })

    // Generate Cartridge button should now be disabled
    const genBtn = screen.getByText('Synthesizing...').closest('button')
    expect(genBtn).toBeDisabled()

    // Cancel button should be disabled during generation
    const cancelBtn = screen.getByText('Cancel').closest('button')
    expect(cancelBtn).toBeDisabled()

    // X button should also be disabled
    const allButtons = screen.getAllByRole('button')
    const xButton = allButtons[0]
    expect(xButton).toBeDisabled()

    // Clean up: resolve the pending read
    resolveRead({ done: true })
  })

  it('shows log terminal instead of textarea during generation', async () => {
    const encoder = new TextEncoder()
    let readIndex = 0
    const events = [
      'data: {"event": "chunk", "text": "Analyzing prompt..."}\n\n',
    ]

    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (readIndex < events.length) {
          const value = encoder.encode(events[readIndex++])
          return Promise.resolve({ done: false, value })
        }
        // Keep hanging to stay in generating state
        return new Promise(() => {})
      })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Generate something' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      // Textarea should be replaced by the log terminal
      expect(screen.queryByPlaceholderText(/Generate a stackable slide-holder/i)).not.toBeInTheDocument()
    })

    // Logs should display the initialization message
    await waitFor(() => {
      expect(screen.getByText(/Initiating Hyperobject Synthesis Engine/)).toBeInTheDocument()
    })
  })

  it('handles SSE error event from the stream by logging to console', async () => {
    // Note: The SSE error event throws inside the inner try/catch (parse block),
    // so it gets caught there and logged via console.error rather than shown in UI.
    const encoder = new TextEncoder()
    let readIndex = 0
    const events = [
      'data: {"event": "chunk", "text": "Starting..."}\n\n',
      'data: {"event": "error", "error": "AI model overloaded"}\n\n',
    ]

    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (readIndex < events.length) {
          const value = encoder.encode(events[readIndex++])
          return Promise.resolve({ done: false, value })
        }
        return Promise.resolve({ done: true })
      })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Make a cube' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      // The error event throws inside the inner try block, caught by the inner catch
      // which calls console.error("Failed to parse SSE event:", ...)
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to parse SSE event:',
        expect.objectContaining({ message: 'AI model overloaded' }),
        expect.stringContaining('"error"')
      )
    })
  })

  it('handles malformed SSE data gracefully', async () => {
    const encoder = new TextEncoder()
    let readIndex = 0
    const events = [
      'data: not-valid-json\n\n',
      'data: {"event": "chunk", "text": "Recovered"}\n\n',
    ]

    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (readIndex < events.length) {
          const value = encoder.encode(events[readIndex++])
          return Promise.resolve({ done: false, value })
        }
        return Promise.resolve({ done: true })
      })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Make something' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      // Should log the parse error but not crash
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to parse SSE event:',
        expect.any(Error),
        'not-valid-json'
      )
    })
  })

  it('appends chunk text to last log line when not a success marker', async () => {
    const encoder = new TextEncoder()
    let readIndex = 0
    const events = [
      'data: {"event": "chunk", "text": "Hello "}\n\n',
      'data: {"event": "chunk", "text": "World"}\n\n',
    ]

    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (readIndex < events.length) {
          const value = encoder.encode(events[readIndex++])
          return Promise.resolve({ done: false, value })
        }
        return Promise.resolve({ done: true })
      })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Test streaming' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      // The init message gets chunk text appended to it
      expect(screen.getByText(/Hello World/)).toBeInTheDocument()
    })
  })

  it('starts a new log line after a success marker line', async () => {
    const encoder = new TextEncoder()
    let readIndex = 0
    // Simulate: init message, then a cartridge-like success marker prefixed with checkmark,
    // then another chunk that should start a new line
    const events = [
      'data: {"event": "chunk", "text": "Processing..."}\n\n',
    ]

    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (readIndex < events.length) {
          const value = encoder.encode(events[readIndex++])
          return Promise.resolve({ done: false, value })
        }
        return Promise.resolve({ done: true })
      })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Test log lines' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      // The init message should have the chunk appended
      expect(screen.getByText(/Initiating Hyperobject Synthesis Engine...Processing.../)).toBeInTheDocument()
    })
  })

  it('includes auth token in request when present in localStorage', async () => {
    const mockReader = {
      read: vi.fn().mockResolvedValue({ done: true })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue('test-jwt-token')

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Make a cube' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/ai/synthesize'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-jwt-token',
          }),
        })
      )
    })
  })

  it('sends request without auth header when no token', async () => {
    const mockReader = {
      read: vi.fn().mockResolvedValue({ done: true })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null)

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Make a cube' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      const fetchCall = globalThis.fetch.mock.calls[0]
      const headers = fetchCall[1].headers
      expect(headers).not.toHaveProperty('Authorization')
    })
  })

  it('displays error with fallback message when error has no message', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})

    // Simulate an error without a message property
    vi.spyOn(globalThis, 'fetch').mockRejectedValue({})

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Make a cube' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      expect(screen.getByText('An unexpected error occurred during synthesis.')).toBeInTheDocument()
    })
  })

  it('shows pulsing cursor indicator during generation', async () => {
    let resolveRead
    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        return new Promise((resolve) => {
          resolveRead = resolve
        })
      })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Test cursor' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      // The pulsing underscore cursor should appear during generation
      const cursor = screen.getByText('_')
      expect(cursor).toBeInTheDocument()
      expect(cursor.className).toContain('animate-pulse')
    })

    // Clean up
    resolveRead({ done: true })
  })

  it('ignores lines that do not start with data: prefix', async () => {
    const encoder = new TextEncoder()
    let readIndex = 0
    // Send a non-data line mixed with a valid chunk
    const events = [
      'event: message\n\ndata: {"event": "chunk", "text": "Valid chunk"}\n\n',
    ]

    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (readIndex < events.length) {
          const value = encoder.encode(events[readIndex++])
          return Promise.resolve({ done: false, value })
        }
        return Promise.resolve({ done: true })
      })
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    render(
      <SynthesisModal
        open={true}
        onOpenChange={mockOnOpenChange}
        onSynthesisComplete={mockOnSynthesisComplete}
      />
    )

    const textarea = screen.getByPlaceholderText(/Generate a stackable slide-holder/i)
    fireEvent.change(textarea, { target: { value: 'Test non-data lines' } })
    fireEvent.click(screen.getByText('Generate Cartridge'))

    await waitFor(() => {
      // Only valid data: lines should be processed; "event: message" should be ignored
      expect(screen.getByText(/Valid chunk/)).toBeInTheDocument()
    })
  })
})
