import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import React from 'react'

// Monaco as a textarea that honours the read-only option.
vi.mock('@monaco-editor/react', () => ({
  default: function MockEditor({ value, onChange, options }) {
    return (
      <textarea
        data-testid="monaco-editor"
        value={value}
        readOnly={Boolean(options?.readOnly)}
        onChange={(e) => onChange?.(e.target.value)}
      />
    )
  },
}))

const mockListFiles = vi.fn()
const mockReadFile = vi.fn()
const mockWriteFile = vi.fn()
const mockDeleteFile = vi.fn()

// The real error type, so the editor sees what the service throws.
vi.mock('../../services/domain/editorService', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    EditorRequestError: actual.EditorRequestError,
    listFiles: (...args) => mockListFiles(...args),
    readFile: (...args) => mockReadFile(...args),
    writeFile: (...args) => mockWriteFile(...args),
    createFile: vi.fn(),
    deleteFile: (...args) => mockDeleteFile(...args),
    updateGraphBindings: vi.fn(),
  }
})

vi.mock('../../contexts/system/ThemeProvider', () => ({ useTheme: () => ({ theme: 'light' }) }))
vi.mock('../../contexts/system/LanguageProvider', () => ({ useLanguage: () => ({ t: (key) => key }) }))
vi.mock('../../lib/scad-language', () => ({ registerScadLanguage: vi.fn(), SCAD_LANGUAGE_ID: 'openscad' }))
vi.mock('../ai/AiChatPanel', () => ({ default: () => null }))

let projectMeta = null
vi.mock('../../hooks/project/useProjectMeta', () => ({
  useProjectMeta: () => projectMeta,
  canWriteCartridge: (meta) => meta?.can_write === true,
}))

import ScadEditor from './ScadEditor'
import { EditorRequestError } from '../../services/domain/editorService'

const OWN_FORK = { source: { type: 'fork', forked_from: 'flange-plate' }, can_write: true, is_owner: true }
const COMMONS = { can_write: false, is_owner: false }
const OTHERS_FORK = { source: { type: 'fork' }, can_write: false, is_owner: false }

function setup(meta, props = {}) {
  projectMeta = meta
  const handleGenerate = vi.fn()
  const onForkRequest = vi.fn()
  render(<ScadEditor slug="p" handleGenerate={handleGenerate} manifest={{ parameters: [] }} onForkRequest={onForkRequest} {...props} />)
  return { handleGenerate, onForkRequest }
}

async function openMain() {
  await waitFor(() => expect(screen.getByText('main.scad')).toBeInTheDocument())
  fireEvent.click(screen.getByText('main.scad'))
  return waitFor(() => screen.getByTestId('monaco-editor'))
}

beforeEach(() => {
  vi.clearAllMocks()
  mockListFiles.mockResolvedValue([{ path: 'main.scad' }, { path: 'parts.scad' }])
  mockReadFile.mockResolvedValue({ content: 'cube(10);' })
  mockWriteFile.mockResolvedValue({ ok: true })
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  console.error.mockRestore?.()
})

describe('a refused autosave says why', () => {
  it.each([
    [403, 'read_only_cartridge', 'editor.save_refused_read_only', true],
    [403, 'not_cartridge_owner', 'editor.save_refused_not_owner', true],
    [409, 'file_already_exists', 'editor.save_conflict', false],
    [500, 'failed_to_write_file_eio', 'editor.save_server_error', false],
    [502, null, 'editor.save_server_error', false],
  ])('%i %s: an alert, the edit kept, no render', async (status, code, message, forkable) => {
    mockWriteFile.mockRejectedValue(new EditorRequestError('server text', status, code))
    const { handleGenerate, onForkRequest } = setup(OWN_FORK)
    const editor = await openMain()
    fireEvent.change(editor, { target: { value: 'cube(20);' } })

    const alert = await screen.findByRole('alert', {}, { timeout: 3000 })
    expect(alert).toHaveTextContent(message)
    expect(alert).not.toHaveTextContent('server text')
    expect(mockWriteFile).toHaveBeenCalledWith('p', 'main.scad', 'cube(20);')
    expect(handleGenerate).not.toHaveBeenCalled()
    // Still unsaved: the tab keeps its marker and the buffer keeps the edit.
    expect(within(screen.getByRole('tab')).getByTitle('Unsaved changes')).toBeInTheDocument()
    expect(screen.getByTestId('monaco-editor')).toHaveValue('cube(20);')

    const fork = within(alert).queryByRole('button', { name: 'editor.fork_to_save' })
    if (forkable) {
      fireEvent.click(fork)
      expect(onForkRequest).toHaveBeenCalledTimes(1)
    } else {
      expect(fork).toBeNull()
    }
    fireEvent.click(within(alert).getByRole('button', { name: 'editor.dismiss' }))
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('a successful autosave renders and marks the tab saved', async () => {
    const { handleGenerate } = setup(OWN_FORK)
    const editor = await openMain()
    fireEvent.change(editor, { target: { value: 'cube(20);' } })
    await waitFor(() => expect(handleGenerate).toHaveBeenCalledTimes(1), { timeout: 3000 })
    expect(screen.queryByRole('alert')).toBeNull()
    expect(within(screen.getByRole('tab')).queryByTitle('Unsaved changes')).toBeNull()
  })

  it('a refused Ctrl+S shows the same message', async () => {
    mockWriteFile.mockRejectedValue(new EditorRequestError('Fork it', 403, 'not_cartridge_owner'))
    setup(OWN_FORK)
    const editor = await openMain()
    fireEvent.change(editor, { target: { value: 'cube(30);' } })
    fireEvent.keyDown(window, { key: 's', ctrlKey: true })
    expect(await screen.findByRole('alert')).toHaveTextContent('editor.save_refused_not_owner')
  })

  it('a refused delete shows the refusal', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockDeleteFile.mockRejectedValue(new EditorRequestError('read only', 403, 'read_only_cartridge'))
    setup(OWN_FORK)
    await waitFor(() => expect(screen.getByText('main.scad')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Delete main.scad' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('editor.save_refused_read_only')
    window.confirm.mockRestore()
  })
})

describe('write controls follow can_write', () => {
  it('your own fork offers new file and delete', async () => {
    setup(OWN_FORK)
    await waitFor(() => expect(screen.getByText('main.scad')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Delete main.scad' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'New file' })).toBeInTheDocument()
    expect(screen.queryByText('editor.read_only_panel')).toBeNull()
  })

  it.each([
    ['a commons cartridge', COMMONS],
    ['another account\'s fork', OTHERS_FORK],
    ['a cartridge whose meta has not loaded', null],
  ])('%s offers neither delete nor new file', async (_label, meta) => {
    setup(meta)
    await waitFor(() => expect(screen.getByText('main.scad')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: /^Delete / })).toBeNull()
    expect(screen.queryByRole('button', { name: 'New file' })).toBeNull()
  })
})

describe('a panel restored on a cartridge you may not write opens read-only', () => {
  it.each([
    ['a commons cartridge', COMMONS],
    ['another account\'s fork', OTHERS_FORK],
  ])('%s: says so, offers the fork, and never writes', async (_label, meta) => {
    const { handleGenerate, onForkRequest } = setup(meta)
    const status = await screen.findByRole('status')
    expect(status).toHaveTextContent('editor.read_only_panel')
    fireEvent.click(within(status).getByRole('button', { name: 'editor.fork_to_save' }))
    expect(onForkRequest).toHaveBeenCalledTimes(1)

    const editor = await openMain()
    expect(editor).toHaveAttribute('readonly')
    fireEvent.change(editor, { target: { value: 'cube(99);' } })
    fireEvent.keyDown(window, { key: 's', ctrlKey: true })
    expect(await screen.findByRole('alert')).toHaveTextContent('editor.read_only_panel')
    await new Promise((r) => setTimeout(r, 1000))
    expect(mockWriteFile).not.toHaveBeenCalled()
    expect(handleGenerate).not.toHaveBeenCalled()
  })

  it('your own fork is editable', async () => {
    setup(OWN_FORK)
    const editor = await openMain()
    expect(editor).not.toHaveAttribute('readonly')
  })
})

describe('editor tab bar', () => {
  it('renders no button inside another button', async () => {
    setup(OWN_FORK)
    await openMain()
    fireEvent.click(screen.getByText('parts.scad'))
    await waitFor(() => expect(screen.getAllByRole('tab')).toHaveLength(2))
    for (const button of document.querySelectorAll('button')) {
      expect(button.querySelector('button')).toBeNull()
    }
    const nesting = console.error.mock.calls.flat().map(String).filter((m) => /descendant of <button>|nested|validateDOMNesting/i.test(m))
    expect(nesting).toEqual([])
  })
})
