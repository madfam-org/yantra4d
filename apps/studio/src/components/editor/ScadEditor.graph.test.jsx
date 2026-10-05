import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import React from 'react'

/**
 * ScadEditor as the owner of the graph editor's save path: where a graph may
 * be written (a fork or an imported repo, never a commons cartridge), when
 * (only once the transpiler would accept it, never for a layout-only move),
 * and together with which binding changes.
 */

vi.mock('@monaco-editor/react', () => ({
  default: function MockEditor({ value, onChange }) {
    return <textarea data-testid="monaco-editor" value={value} onChange={(e) => onChange?.(e.target.value)} />
  },
}))

const mockListFiles = vi.fn()
const mockReadFile = vi.fn()
vi.mock('../../services/domain/editorService', () => ({
  listFiles: (...args) => mockListFiles(...args),
  readFile: (...args) => mockReadFile(...args),
  createFile: vi.fn(),
  deleteFile: vi.fn(),
}))

const mockSaveAndRender = vi.fn()
vi.mock('../../hooks/editor/useEditorRender', () => ({
  useEditorRender: () => ({ saveAndRender: mockSaveAndRender, saveImmediate: vi.fn() }),
}))

const mockSchedule = vi.fn()
const mockSaveNow = vi.fn()
let persistenceOptions = null
vi.mock('../../hooks/editor/useGraphPersistence', () => ({
  useGraphPersistence: (options) => {
    persistenceOptions = options
    return { status: 'idle', error: null, schedule: mockSchedule, saveNow: mockSaveNow, cancel: vi.fn() }
  },
}))

let projectMeta = null
vi.mock('../../hooks/project/useProjectMeta', () => ({ useProjectMeta: () => projectMeta }))
vi.mock('../../contexts/system/ThemeProvider', () => ({ useTheme: () => ({ theme: 'light' }) }))
vi.mock('../../contexts/system/LanguageProvider', () => ({ useLanguage: () => ({ t: (key) => key }) }))
vi.mock('../../lib/scad-language', () => ({ registerScadLanguage: vi.fn(), SCAD_LANGUAGE_ID: 'openscad' }))
vi.mock('../ai/AiChatPanel', () => ({ default: () => null }))

// The graph editor itself is tested in graph/GraphEditor.test.jsx; here it is a
// stub that exposes the props ScadEditor hands it and lets a test fire edits.
let editorProps = null
vi.mock('./graph/GraphEditor', () => ({
  default: function MockGraphEditor(props) {
    editorProps = props
    return (
      <div data-testid="graph-editor-mock" data-save-blocked={props.saveBlockedReason ?? ''}
        data-bind-blocked={props.bindBlockedReason ?? ''} data-status={props.saveStatus}
        data-selected={props.selectedId ?? ''} />
    )
  },
}))

import ScadEditor from './ScadEditor'

const VALID = {
  version: '1.0.0',
  nodes: [
    { id: 'outline', type: 'profile_circle', params: { r: 45 } },
    { id: 'plate', type: 'extrude', inputs: { profile: 'outline' }, params: { height: 8 } },
  ],
  outputs: { flange: 'plate' },
}
const json = (d) => `${JSON.stringify(d, null, 2)}\n`

const manifest = {
  project: { name: 'Flange' },
  parts: [{ id: 'flange' }],
  parameters: [
    { id: 'plate_radius', type: 'slider', default: 45, binding: 'outline.r' },
    { id: 'thickness', type: 'slider', default: 8 },
  ],
}

async function openGraph(handleGenerate = vi.fn()) {
  render(<ScadEditor slug="my-flange" handleGenerate={handleGenerate} manifest={manifest} onForkRequest={vi.fn()} />)
  const option = await screen.findByText('flange.graph.json')
  fireEvent.click(option)
  await screen.findByRole('button', { name: 'Graph' })
  fireEvent.click(screen.getByRole('button', { name: 'Graph' }))
  await screen.findByTestId('graph-editor-mock')
}

beforeEach(() => {
  vi.clearAllMocks()
  editorProps = null
  persistenceOptions = null
  projectMeta = { source: { type: 'fork', forked_from: 'flange-plate' } }
  mockListFiles.mockResolvedValue([{ path: 'flange.graph.json' }])
  mockReadFile.mockResolvedValue({ content: json(VALID) })
  mockSaveNow.mockResolvedValue(true)
})

describe('ScadEditor graph save path', () => {
  it('hands the graph editor the manifest parameters, parts and bindings', async () => {
    await openGraph()
    expect(editorProps.partIds).toEqual(['flange'])
    expect(editorProps.bindings).toEqual({ plate_radius: ['outline.r'] })
    expect(editorProps.bindable.map((p) => p.id)).toEqual(['plate_radius', 'thickness'])
    expect(editorProps.fileName).toBe('flange.graph.json')
  })

  it('on a fork, a valid geometry edit is saved and rendered', async () => {
    await openGraph()
    const edited = structuredClone(VALID)
    edited.nodes[1].params.height = 12
    act(() => editorProps.onDocumentChange(json(edited), { layoutOnly: false }))
    expect(mockSchedule).toHaveBeenCalledWith('flange.graph.json', json(edited), {})
    expect(screen.getByTestId('graph-editor-mock').dataset.status).toBe('dirty')
  })

  it('does not write a document the transpiler would reject', async () => {
    await openGraph()
    const broken = structuredClone(VALID)
    delete broken.nodes[1].inputs.profile
    act(() => editorProps.onDocumentChange(json(broken), { layoutOnly: false }))
    expect(mockSchedule).not.toHaveBeenCalled()
  })

  it('does not write a param that is both bound and an expression', async () => {
    await openGraph()
    const edited = structuredClone(VALID)
    edited.version = '1.1.0'
    edited.parameters = { plate_radius: { default: 45 } }
    edited.nodes[0].params.r = { expr: 'plate_radius' }
    // plate_radius still binds outline.r in the manifest
    act(() => editorProps.onDocumentChange(json(edited), { layoutOnly: false }))
    expect(mockSchedule).not.toHaveBeenCalled()
    // unbinding it makes the same document savable
    act(() => editorProps.onDocumentChange(json(edited), { layoutOnly: false, bindings: {} }))
    expect(mockSchedule).toHaveBeenCalledWith('flange.graph.json', json(edited), { plate_radius: null })
  })

  it('does not save or render when only node positions moved', async () => {
    await openGraph()
    const moved = structuredClone(VALID)
    moved.nodes[0].meta = { position: { x: 10, y: 20 } }
    act(() => editorProps.onDocumentChange(json(moved), { layoutOnly: true }))
    expect(mockSchedule).not.toHaveBeenCalled()
    expect(screen.getByTestId('graph-editor-mock').dataset.status).toBe('dirty')
  })

  it('saves binding changes made by the same edit together with the graph', async () => {
    await openGraph()
    const edited = structuredClone(VALID)
    edited.nodes[1].params.height = 9
    act(() => editorProps.onDocumentChange(json(edited), { layoutOnly: false, bindings: {} }))
    expect(mockSchedule).toHaveBeenCalledWith('flange.graph.json', json(edited), { plate_radius: null })
    expect(editorProps.bindings).toEqual({})
  })

  it('a binding edit previews like a geometry edit', async () => {
    await openGraph()
    act(() => editorProps.onBindingsChange({ plate_radius: ['outline.r'], thickness: ['plate.height'] }))
    expect(mockSchedule).toHaveBeenCalledWith('flange.graph.json', json(VALID), { thickness: 'plate.height' })
  })

  it('Ctrl+S saves the graph and the pending bindings at once', async () => {
    await openGraph()
    act(() => editorProps.onBindingsChange({ plate_radius: ['outline.r'], thickness: ['plate.height'] }))
    fireEvent.keyDown(window, { key: 's', ctrlKey: true })
    await waitFor(() => expect(mockSaveNow).toHaveBeenCalledWith('flange.graph.json', json(VALID), { thickness: 'plate.height' }))
  })

  it('takes the server binding map as saved once bindings are written', async () => {
    await openGraph()
    act(() => editorProps.onBindingsChange({ plate_radius: ['outline.r'], thickness: ['plate.height'] }))
    act(() => persistenceOptions.onBindingsSaved({ bindings: { plate_radius: 'outline.r', thickness: 'plate.height' } }))
    act(() => persistenceOptions.onSaved('flange.graph.json', json(VALID)))
    expect(screen.getByTestId('graph-editor-mock').dataset.status).toBe('clean')
  })

  it('never writes a commons cartridge: no autosave, no Ctrl+S, no text-view save', async () => {
    projectMeta = null
    await openGraph()
    const mock = screen.getByTestId('graph-editor-mock')
    expect(mock.dataset.saveBlocked).toBe('graph.save_blocked_commons')
    expect(mock.dataset.bindBlocked).toBe('graph.bind_blocked_not_fork')

    const edited = structuredClone(VALID)
    edited.nodes[1].params.height = 12
    act(() => editorProps.onDocumentChange(json(edited), { layoutOnly: false }))
    act(() => editorProps.onBindingsChange({}))
    fireEvent.keyDown(window, { key: 's', ctrlKey: true })
    expect(mockSchedule).not.toHaveBeenCalled()
    expect(mockSaveNow).not.toHaveBeenCalled()
    expect(await screen.findByText('graph.save_blocked_commons')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Text' }))
    fireEvent.change(screen.getByTestId('monaco-editor'), { target: { value: json(VALID) } })
    expect(mockSaveAndRender).not.toHaveBeenCalled()
  })

  it('an imported repository saves the graph but cannot change manifest bindings', async () => {
    projectMeta = { source: { type: 'github' } }
    await openGraph()
    expect(screen.getByTestId('graph-editor-mock').dataset.saveBlocked).toBe('')
    expect(screen.getByTestId('graph-editor-mock').dataset.bindBlocked).toBe('graph.bind_blocked_not_fork')
    const edited = structuredClone(VALID)
    edited.nodes[1].params.height = 12
    act(() => editorProps.onDocumentChange(json(edited), { layoutOnly: false, bindings: {} }))
    expect(mockSchedule).toHaveBeenCalledWith('flange.graph.json', json(edited), null)
    act(() => editorProps.onBindingsChange({}))
    expect(mockSchedule).toHaveBeenCalledTimes(1)
  })

  it('selecting an issue selects its node in the graph editor', async () => {
    await openGraph()
    const broken = structuredClone(VALID)
    broken.nodes[1].params.nope = 1
    act(() => editorProps.onDocumentChange(json(broken), { layoutOnly: false }))
    fireEvent.click(await screen.findByRole('button', { name: 'plate.nope:' }))
    expect(screen.getByTestId('graph-editor-mock').dataset.selected).toBe('plate')
  })
})
