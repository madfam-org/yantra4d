import { describe, it, expect, vi, beforeAll } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AiChatPanel from './AiChatPanel'

beforeAll(() => {
  // jsdom doesn't implement scrollIntoView
  Element.prototype.scrollIntoView = vi.fn()
})

vi.mock('../hooks/useAiChat', () => ({
  useAiChat: () => ({
    messages: [],
    sendMessage: vi.fn(),
    isStreaming: false,
    streamingText: '',
    pendingEdits: [],
    setPendingEdits: vi.fn(),
    resetSession: vi.fn(),
  }),
}))

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
})
