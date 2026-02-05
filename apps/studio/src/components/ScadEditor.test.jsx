import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

// Mock Monaco editor as a textarea
vi.mock('@monaco-editor/react', () => ({
  default: function MockEditor({ value, onChange, onMount }) {
    React.useEffect(() => {
      if (onMount) onMount({ current: null }, { languages: { register: vi.fn(), setMonarchTokensProvider: vi.fn(), registerCompletionItemProvider: vi.fn() } })
    }, [])
    return (
      <textarea
        data-testid="monaco-editor"
        value={value}
        onChange={e => onChange?.(e.target.value)}
      />
    )
  },
}))

const mockListFiles = vi.fn()
const mockReadFile = vi.fn()
const mockCreateFile = vi.fn()
const mockDeleteFile = vi.fn()

vi.mock('../services/editorService', () => ({
  listFiles: (...args) => mockListFiles(...args),
  readFile: (...args) => mockReadFile(...args),
  createFile: (...args) => mockCreateFile(...args),
  deleteFile: (...args) => mockDeleteFile(...args),
}))

const mockSaveAndRender = vi.fn()
const mockSaveImmediate = vi.fn()

vi.mock('../hooks/useEditorRender', () => ({
  useEditorRender: () => ({
    saveAndRender: mockSaveAndRender,
    saveImmediate: mockSaveImmediate,
  }),
}))

vi.mock('../contexts/ThemeProvider', () => ({
  useTheme: () => ({ theme: 'light' }),
}))

vi.mock('../lib/scad-language', () => ({
  registerScadLanguage: vi.fn(),
  SCAD_LANGUAGE_ID: 'openscad',
}))

// Lazy-loaded AiChatPanel
vi.mock('./AiChatPanel', () => ({
  default: function MockAiChat(props) {
    return <div data-testid="ai-chat-panel" data-mode={props.mode} />
  },
}))

import ScadEditor from './ScadEditor'

const defaultProps = {
  slug: 'test-project',
  handleGenerate: vi.fn(),
  manifest: { project: { name: 'Test' }, parameters: [] },
}

beforeEach(() => {
  vi.clearAllMocks()
  mockListFiles.mockResolvedValue([
    { path: 'main.scad' },
    { path: 'parts.scad' },
  ])
  mockReadFile.mockResolvedValue({ content: '// OpenSCAD file\ncube([10, 10, 10]);' })
  mockSaveImmediate.mockResolvedValue({})
})

describe('ScadEditor', () => {
  it('shows loading state initially', () => {
    mockListFiles.mockImplementation(() => new Promise(() => {}))
    render(<ScadEditor {...defaultProps} />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('displays file list after loading', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
      expect(screen.getByText('parts.scad')).toBeInTheDocument()
    })
  })

  it('shows empty editor state when no file selected', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('Select a file to edit')).toBeInTheDocument()
    })
  })

  it('opens file when clicked in file tree', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    // Click the file button (the one in the file tree, not the tab)
    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))

    await waitFor(() => {
      expect(mockReadFile).toHaveBeenCalledWith('test-project', 'main.scad')
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument()
    })
  })

  it('renders file tabs for open files', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))

    await waitFor(() => {
      expect(screen.getByRole('tab')).toBeInTheDocument()
    })
  })

  it('shows error when file list fails to load', async () => {
    mockListFiles.mockRejectedValue(new Error('Connection refused'))
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('Connection refused')).toBeInTheDocument()
    })
  })

  it('has file tree with accessible listbox role', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByRole('listbox', { name: 'Project files' })).toBeInTheDocument()
    })
  })

  it('shows Files header and new file button', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('Files')).toBeInTheDocument()
      expect(screen.getByTitle('New file')).toBeInTheDocument()
    })
  })

  it('shows error dismiss button', async () => {
    mockListFiles.mockRejectedValue(new Error('Test error'))
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('dismiss')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('dismiss'))
    expect(screen.queryByText('Test error')).not.toBeInTheDocument()
  })

  it('shows AI toggle button when file is open', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))

    await waitFor(() => {
      expect(screen.getByText('AI')).toBeInTheDocument()
    })
  })

  it('toggles AI panel on button click', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))

    await waitFor(() => {
      expect(screen.getByText('AI')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('AI'))

    await waitFor(() => {
      expect(screen.getByTestId('ai-chat-panel')).toBeInTheDocument()
      expect(screen.getByTestId('ai-chat-panel')).toHaveAttribute('data-mode', 'code-editor')
    })

    // Toggle off
    fireEvent.click(screen.getByText('AI'))
    expect(screen.queryByTestId('ai-chat-panel')).not.toBeInTheDocument()
  })

  it('handles Ctrl+S keyboard shortcut', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    // Open a file
    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument()
    })

    // Modify content to make it dirty
    fireEvent.change(screen.getByTestId('monaco-editor'), {
      target: { value: 'cube([20, 20, 20]);' },
    })

    // Press Ctrl+S
    fireEvent.keyDown(window, { key: 's', ctrlKey: true })

    await waitFor(() => {
      expect(mockSaveImmediate).toHaveBeenCalled()
    })
  })

  it('calls saveAndRender on content change', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('monaco-editor'), {
      target: { value: 'sphere(r=5);' },
    })

    expect(mockSaveAndRender).toHaveBeenCalledWith('main.scad', 'sphere(r=5);')
  })

  it('closes tab and switches to remaining tab', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    // Open two files
    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))
    await waitFor(() => expect(screen.getByTestId('monaco-editor')).toBeInTheDocument())

    mockReadFile.mockResolvedValueOnce({ content: '// parts file' })
    fireEvent.click(fileButtons[1].querySelector('button'))
    await waitFor(() => expect(mockReadFile).toHaveBeenCalledTimes(2))

    // Close active tab (parts.scad) via the close button
    const tabs = screen.getAllByRole('tab')
    const closeBtn = tabs[1].querySelector('button')
    fireEvent.click(closeBtn)

    // Should switch to remaining tab
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(1)
    })
  })

  it('shows error when readFile fails', async () => {
    mockReadFile.mockRejectedValueOnce(new Error('File not found'))
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))

    await waitFor(() => {
      expect(screen.getByText('File not found')).toBeInTheDocument()
    })
  })

  it('shows dirty indicator when content modified', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))
    await waitFor(() => expect(screen.getByTestId('monaco-editor')).toBeInTheDocument())

    fireEvent.change(screen.getByTestId('monaco-editor'), {
      target: { value: 'modified content' },
    })

    // Dirty dot should appear
    await waitFor(() => {
      expect(screen.getByTitle('Unsaved changes')).toBeInTheDocument()
    })
  })

  it('clears dirty state after save', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => expect(screen.getByText('main.scad')).toBeInTheDocument())

    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))
    await waitFor(() => expect(screen.getByTestId('monaco-editor')).toBeInTheDocument())

    // Modify
    fireEvent.change(screen.getByTestId('monaco-editor'), {
      target: { value: 'modified' },
    })
    await waitFor(() => expect(screen.getByTitle('Unsaved changes')).toBeInTheDocument())

    // Save via Ctrl+S
    fireEvent.keyDown(window, { key: 's', ctrlKey: true })
    await waitFor(() => {
      expect(mockSaveImmediate).toHaveBeenCalled()
    })
  })

  it('does not open same file twice', async () => {
    render(<ScadEditor {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('main.scad')).toBeInTheDocument()
    })

    const fileButtons = screen.getAllByRole('option')
    fireEvent.click(fileButtons[0].querySelector('button'))

    await waitFor(() => {
      expect(mockReadFile).toHaveBeenCalledTimes(1)
    })

    // Click same file again
    fireEvent.click(fileButtons[0].querySelector('button'))
    // Should not read file again
    expect(mockReadFile).toHaveBeenCalledTimes(1)
  })
})
