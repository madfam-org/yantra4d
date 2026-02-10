import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

let mockMessages = []
let mockIsStreaming = false
let mockStreamingText = ''
let mockPendingEdits = []
const mockSendMessage = vi.fn()
const mockResetSession = vi.fn()
const mockSetPendingEdits = vi.fn()

vi.mock('../../hooks/useAiChat', () => ({
  useAiChat: () => ({
    messages: mockMessages,
    sendMessage: mockSendMessage,
    isStreaming: mockIsStreaming,
    streamingText: mockStreamingText,
    pendingEdits: mockPendingEdits,
    setPendingEdits: mockSetPendingEdits,
    resetSession: mockResetSession,
  }),
}))

import AiChatPanel from './AiChatPanel'

beforeEach(() => {
  mockMessages = []
  mockIsStreaming = false
  mockStreamingText = ''
  mockPendingEdits = []
  vi.clearAllMocks()
})

const defaultProps = {
  mode: 'configurator',
  projectSlug: 'test-project',
  manifest: { project: { name: 'Test' }, parameters: [] },
  params: {},
  setParams: vi.fn(),
}

describe('AiChatPanel', () => {
  it('renders configurator mode header', () => {
    render(<AiChatPanel {...defaultProps} />)
    expect(screen.getByText('AI Configurator')).toBeInTheDocument()
  })

  it('renders code-editor mode header', () => {
    render(<AiChatPanel {...defaultProps} mode="code-editor" />)
    expect(screen.getByText('AI Code Editor')).toBeInTheDocument()
  })

  it('shows placeholder text for configurator', () => {
    render(<AiChatPanel {...defaultProps} />)
    expect(screen.getByText(/Describe how you want to adjust/)).toBeInTheDocument()
  })

  it('has send button disabled when input is empty', () => {
    render(<AiChatPanel {...defaultProps} />)
    const sendBtn = screen.getByRole('button', { name: /send/i })
    expect(sendBtn).toBeDisabled()
  })

  it('has new conversation button', () => {
    render(<AiChatPanel {...defaultProps} />)
    expect(screen.getByRole('button', { name: /new conversation/i })).toBeInTheDocument()
  })

  it('renders user and assistant messages', () => {
    mockMessages = [
      { role: 'user', content: 'make it wider' },
      { role: 'assistant', content: 'Width increased.' },
    ]
    render(<AiChatPanel {...defaultProps} />)
    expect(screen.getByText('make it wider')).toBeInTheDocument()
    expect(screen.getByText('Width increased.')).toBeInTheDocument()
  })

  it('renders param change system messages', () => {
    mockMessages = [{ role: 'system', content: 'params', changes: { width: 30 } }]
    render(<AiChatPanel {...defaultProps} />)
    expect(screen.getByText(/width → 30/)).toBeInTheDocument()
  })

  it('sends message on Enter key', () => {
    render(<AiChatPanel {...defaultProps} />)
    const input = screen.getByPlaceholderText(/make it wider/)
    fireEvent.change(input, { target: { value: 'hello' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(mockSendMessage).toHaveBeenCalledWith('hello', undefined)
  })

  it('does not send empty message', () => {
    render(<AiChatPanel {...defaultProps} />)
    const input = screen.getByPlaceholderText(/make it wider/)
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(mockSendMessage).not.toHaveBeenCalled()
  })

  it('disables input when streaming', () => {
    mockIsStreaming = true
    render(<AiChatPanel {...defaultProps} />)
    expect(screen.getByPlaceholderText(/make it wider/)).toBeDisabled()
  })

  it('shows streaming text', () => {
    mockIsStreaming = true
    mockStreamingText = 'analyzing...'
    render(<AiChatPanel {...defaultProps} />)
    expect(screen.getByText('analyzing...')).toBeInTheDocument()
  })

  it('shows thinking indicator when streaming without text', () => {
    mockIsStreaming = true
    render(<AiChatPanel {...defaultProps} />)
    expect(screen.getByText('Thinking...')).toBeInTheDocument()
  })

  it('shows pending edits banner in code-editor mode', () => {
    mockPendingEdits = [{ file: 'test.scad' }]
    render(<AiChatPanel {...defaultProps} mode="code-editor" onApplyEdits={vi.fn()} />)
    expect(screen.getByText(/1 edit pending/)).toBeInTheDocument()
  })

  it('apply all calls onApplyEdits', () => {
    const onApply = vi.fn()
    mockPendingEdits = [{ file: 'a.scad' }]
    render(<AiChatPanel {...defaultProps} mode="code-editor" onApplyEdits={onApply} />)
    fireEvent.click(screen.getByText('Apply All'))
    expect(onApply).toHaveBeenCalled()
    expect(mockSetPendingEdits).toHaveBeenCalledWith([])
  })

  it('reject clears pending edits', () => {
    mockPendingEdits = [{ file: 'a.scad' }]
    render(<AiChatPanel {...defaultProps} mode="code-editor" onApplyEdits={vi.fn()} />)
    fireEvent.click(screen.getByText('Reject'))
    expect(mockSetPendingEdits).toHaveBeenCalledWith([])
  })

  it('reset button calls resetSession', () => {
    render(<AiChatPanel {...defaultProps} />)
    fireEvent.click(screen.getByTitle('New conversation'))
    expect(mockResetSession).toHaveBeenCalled()
  })

  it('does not show pending edits in configurator mode', () => {
    mockPendingEdits = [{ file: 'a.scad' }]
    render(<AiChatPanel {...defaultProps} />)
    expect(screen.queryByText(/edit pending/)).not.toBeInTheDocument()
  })
})
