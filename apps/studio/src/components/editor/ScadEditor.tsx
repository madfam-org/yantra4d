import { useState, useEffect, useCallback, useMemo, useRef, lazy, Suspense } from 'react'
import Editor from '@monaco-editor/react'
import type { OnMount, OnChange } from '@monaco-editor/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from '@/components/ui/alert-dialog'
import { FileCode, Plus, X, Loader2, Sparkles } from 'lucide-react'

const AiChatPanel = lazy(() => import('../ai/AiChatPanel'))
import { useTheme } from '../../contexts/system/ThemeProvider'
import GraphIssues from './GraphIssues'
const GraphEditor = lazy(() => import('./graph/GraphEditor'))
import { listFiles, readFile, createFile, deleteFile } from '../../services/domain/editorService'
import type { GraphBindingsResponse } from '../../services/domain/editorService'
import { registerScadLanguage, SCAD_LANGUAGE_ID } from '../../lib/scad-language'
import { useEditorRender } from '../../hooks/editor/useEditorRender'
import { editorSaveFailure } from '../../lib/editorSaveMessage'
import { useGraphPersistence } from '../../hooks/editor/useGraphPersistence'
import { useProjectMeta } from '../../hooks/project/useProjectMeta'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { validateGraph } from '../../lib/graph/graphDocument'
import { bindableParameters, bindingChanges, bindingConflicts, bindingsFromManifest } from '../../lib/graph/graphBindings'
import type { BindingMap } from '../../lib/graph/graphBindings'
import type { ManifestParameterLike } from '../../lib/graph/graphExpressions'

interface FileEntry {
  path: string
  [key: string]: unknown
}

interface OpenTab {
  path: string
  content: string
  originalContent: string
  dirty: boolean
}

interface CodeEdit {
  file: string
  search: string
  replace: string
}

interface ScadEditorProps {
  slug: string
  handleGenerate: () => void
  manifest: Record<string, unknown>
  /** Opens the fork dialog — how a commons cartridge becomes something this editor may save. */
  onForkRequest?: () => void
}

/**
 * Whether a graph buffer, with the binding map it would be saved with, would
 * pass the transpiler's rules (an expression-valued param cannot also be bound).
 */
function isSavableGraph(content: string, bindings: BindingMap = {}): boolean {
  try {
    const doc = JSON.parse(content)
    return validateGraph(doc).length === 0 && bindingConflicts(doc, bindings).length === 0
  } catch {
    return false
  }
}

export default function ScadEditor({ slug, handleGenerate, manifest, onForkRequest }: ScadEditorProps) {
  const { theme } = useTheme()
  const { t } = useLanguage()
  const [files, setFiles] = useState<FileEntry[]>([])
  const [openTabs, setOpenTabs] = useState<OpenTab[]>([])
  const [activeTab, setActiveTab] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Set when the last failure was a refused write that forking would fix.
  const [errorForkable, setErrorForkable] = useState(false)
  const [aiOpen, setAiOpen] = useState(false)
  const [showNewFileDialog, setShowNewFileDialog] = useState(false)
  const [newFileName, setNewFileName] = useState('')
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null)
  const monacoRef = useRef<Parameters<OnMount>[1] | null>(null)

  // A failed save says why, in words, where the author is looking: a refused
  // write to a commons cartridge or someone else's fork offers the fork.
  const showSaveFailure = useCallback((e: unknown) => {
    const failure = editorSaveFailure(e, t)
    setError(failure.message)
    setErrorForkable(failure.forkable)
  }, [t])
  const onAutosaved = useCallback((path: string, content: string) => {
    setOpenTabs(prev => prev.map(tab =>
      tab.path === path ? { ...tab, originalContent: content, dirty: tab.content !== content } : tab
    ))
  }, [])
  const { saveAndRender, saveImmediate } = useEditorRender({ slug, handleGenerate, onSaveError: showSaveFailure, onSaved: onAutosaved })

  // ── Graph editing: where saves may go, and the manifest bindings ──────────
  // A project with no `source.type` in project.meta.json is a commons
  // cartridge (the header offers "Fork & Edit" instead of the editor). The
  // graph editor never writes one: edits stay in the buffer, export works,
  // and saving means forking first. Bindings live in the manifest and the
  // server only accepts binding edits on a fork.
  // A fork or import is saved only by the account that created it (or an
  // admin): the API reports that as `can_write`, and one it says no to is
  // treated like a commons cartridge here — buffer, export, "Fork to save".
  const projectMeta = useProjectMeta(slug)
  const sourceType = ((projectMeta?.source as Record<string, unknown> | undefined)?.type as string | undefined) ?? null
  const writableSource = sourceType === 'fork' || sourceType === 'github'
  const notOwner = writableSource && projectMeta?.can_write === false
  const graphSaveBlocked = !writableSource
    ? t('graph.save_blocked_commons')
    : notOwner ? t('graph.save_blocked_not_owner') : null
  const bindBlocked = notOwner
    ? t('graph.save_blocked_not_owner')
    : sourceType === 'fork' ? null : t('graph.bind_blocked_not_fork')
  const manifestParameters = useMemo(
    () => ((manifest?.parameters as ManifestParameterLike[] | undefined) ?? []).filter((p) => p && typeof p.id === 'string'),
    [manifest],
  )
  const partIds = useMemo(
    () => ((manifest?.parts as Array<{ id?: unknown }> | undefined) ?? []).map((p) => p?.id).filter((id): id is string => typeof id === 'string'),
    [manifest],
  )
  const bindable = useMemo(() => bindableParameters(manifestParameters), [manifestParameters])
  const manifestBindings = useMemo(() => bindingsFromManifest(manifestParameters), [manifestParameters])
  const [bindingState, setBindingState] = useState<{ source: BindingMap; saved: BindingMap; draft: BindingMap }>(
    () => ({ source: manifestBindings, saved: manifestBindings, draft: manifestBindings }),
  )
  if (bindingState.source !== manifestBindings) {
    setBindingState({ source: manifestBindings, saved: manifestBindings, draft: manifestBindings })
  }
  const { saved: savedBindings, draft: draftBindings } = bindingState
  const pendingBindings = useMemo(() => bindingChanges(savedBindings, draftBindings), [savedBindings, draftBindings])
  const onBindingsSaved = useCallback((response: GraphBindingsResponse) => {
    const saved: BindingMap = {}
    for (const [pid, value] of Object.entries(response.bindings)) saved[pid] = Array.isArray(value) ? value : [value]
    setBindingState((prev) => ({ ...prev, saved }))
  }, [])
  const onGraphSaved = useCallback((path: string, content: string) => {
    setOpenTabs(prev => prev.map(t =>
      t.path === path ? { ...t, originalContent: content, dirty: t.content !== content } : t
    ))
  }, [])
  const graphPersistence = useGraphPersistence({ slug, handleGenerate, onBindingsSaved, onSaved: onGraphSaved })

  // Load file list
  useEffect(() => {
    let cancelled = false
    listFiles(slug)
      .then((f: unknown) => { if (!cancelled) { setFiles(f as FileEntry[]); setError(null); setLoading(false) } })
      .catch((e: Error) => { if (!cancelled) { setError(e.message); setErrorForkable(false); setLoading(false) } })
    return () => { cancelled = true }
  }, [slug])

  const handleEditorMount: OnMount = useCallback((editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco
    registerScadLanguage(monaco)
  }, [])

  const openFile = useCallback(async (path: string) => {
    // Already open?
    const existing = openTabs.find(t => t.path === path)
    if (existing) {
      setActiveTab(path)
      return
    }
    try {
      const data = await readFile(slug, path)
      setOpenTabs(prev => [...prev, { path, content: data.content, originalContent: data.content, dirty: false }])
      setActiveTab(path)
    } catch (e) {
      setError((e as Error).message)
      setErrorForkable(false)
    }
  }, [slug, openTabs])

  const closeTab = useCallback((path: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    setOpenTabs(prev => prev.filter(t => t.path !== path))
    if (activeTab === path) {
      const remaining = openTabs.filter(t => t.path !== path)
      setActiveTab(remaining.length > 0 ? remaining[remaining.length - 1].path : null)
    }
  }, [activeTab, openTabs])

  const handleContentChange: OnChange = useCallback((value) => {
    if (!activeTab) return
    setOpenTabs(prev => prev.map(t =>
      t.path === activeTab
        ? { ...t, content: value ?? '', dirty: (value ?? '') !== t.originalContent }
        : t
    ))
    // A graph document in a commons cartridge is never written: edit, export, or fork it.
    if (activeTab.endsWith('.graph.json') && graphSaveBlocked) return
    saveAndRender(activeTab, value ?? '')
  }, [activeTab, saveAndRender, graphSaveBlocked])

  const handleSave = useCallback(async () => {
    const tab = openTabs.find(t => t.path === activeTab)
    if (tab && tab.path.endsWith('.graph.json')) {
      // Graph documents save through the graph path: never into a commons
      // cartridge, and together with any binding the author changed.
      if (graphSaveBlocked) { setError(graphSaveBlocked); setErrorForkable(true); return }
      const changes = bindBlocked ? null : pendingBindings
      if (!tab.dirty && (!changes || Object.keys(changes).length === 0)) return
      setSaving(true)
      await graphPersistence.saveNow(tab.path, tab.content, changes)
      setSaving(false)
      return
    }
    if (!tab || !tab.dirty) return
    setSaving(true)
    try {
      await saveImmediate(tab.path, tab.content)
      setOpenTabs(prev => prev.map(t =>
        t.path === activeTab ? { ...t, originalContent: t.content, dirty: false } : t
      ))
    } catch (e) {
      showSaveFailure(e)
    }
    setSaving(false)
  }, [activeTab, openTabs, saveImmediate, graphSaveBlocked, bindBlocked, pendingBindings, graphPersistence, showSaveFailure])

  // Ctrl+S handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleSave])

  const handleNewFile = useCallback(async (name: string) => {
    if (!name || !name.endsWith('.scad')) return
    try {
      await createFile(slug, name)
      const updated = await listFiles(slug)
      setFiles(updated as unknown as FileEntry[])
      openFile(name)
    } catch (e) {
      showSaveFailure(e)
    }
  }, [slug, openFile, showSaveFailure])

  const handleNewFileConfirm = useCallback(() => {
    const name = newFileName.trim()
    if (!name) return
    const finalName = name.endsWith('.scad') ? name : `${name}.scad`
    setShowNewFileDialog(false)
    setNewFileName('')
    handleNewFile(finalName)
  }, [newFileName, handleNewFile])

  const handleDeleteFile = useCallback(async (path: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    if (!confirm(`Delete ${path}?`)) return
    try {
      await deleteFile(slug, path)
      closeTab(path)
      const updated = await listFiles(slug)
      setFiles(updated as unknown as FileEntry[])
    } catch (err) {
      showSaveFailure(err)
    }
  }, [slug, closeTab, showSaveFailure])

  const activeContent = openTabs.find(t => t.path === activeTab)?.content || ''
  // Graph documents are JSON, not OpenSCAD — highlight them as such and run the
  // transpiler's validation rules against the buffer as the author types.
  const isGraphFile = (activeTab ?? '').endsWith('.graph.json')
  const [graphView, setGraphView] = useState(false)
  const showCanvas = isGraphFile && graphView
  const [graphSelection, setGraphSelection] = useState<string | null>(null)

  const handleGraphChange = useCallback((
    content: string,
    { layoutOnly, bindings }: { layoutOnly: boolean; bindings?: BindingMap },
  ) => {
    if (!activeTab) return
    setOpenTabs(prev => prev.map(t =>
      t.path === activeTab ? { ...t, content, dirty: content !== t.originalContent } : t
    ))
    if (bindings) setBindingState(prev => ({ ...prev, draft: bindings }))
    const changes = bindings ? bindingChanges(savedBindings, bindings) : pendingBindings
    // Geometry edits preview through the existing render, but only where a
    // save is allowed and only once the transpiler would accept the document;
    // moving a node changes no geometry, so it waits for an explicit save.
    if (layoutOnly || graphSaveBlocked || !isSavableGraph(content, bindings ?? draftBindings)) return
    graphPersistence.schedule(activeTab, content, bindBlocked ? null : changes)
  }, [activeTab, graphSaveBlocked, bindBlocked, savedBindings, draftBindings, pendingBindings, graphPersistence])

  const handleGraphBindingsChange = useCallback((draft: BindingMap) => {
    setBindingState(prev => ({ ...prev, draft }))
    // A binding changes what the render reads, so it previews like a geometry edit.
    const tab = openTabs.find(t => t.path === activeTab)
    if (!tab || graphSaveBlocked || bindBlocked || !isSavableGraph(tab.content, draft)) return
    graphPersistence.schedule(tab.path, tab.content, bindingChanges(savedBindings, draft))
  }, [openTabs, activeTab, graphSaveBlocked, bindBlocked, savedBindings, graphPersistence])

  const activeGraphTab = openTabs.find(t => t.path === activeTab)
  const graphSaveStatus = graphPersistence.status === 'saving' ? 'saving'
    : graphPersistence.status === 'error' ? 'error'
      : (activeGraphTab?.dirty || Object.keys(pendingBindings).length > 0) ? 'dirty'
        : graphPersistence.status === 'saved' ? 'saved' : 'clean'

  // Build file contents map for AI code editor
  const getFileContents = useCallback(() => {
    const contents: Record<string, string> = {}
    for (const tab of openTabs) {
      contents[tab.path] = tab.content
    }
    return contents
  }, [openTabs])

  const handleApplyEdits = useCallback((edits: CodeEdit[]) => {
    for (const edit of edits) {
      setOpenTabs(prev => prev.map(t => {
        if (t.path === edit.file) {
          const newContent = t.content.replace(edit.search, edit.replace)
          if (newContent !== t.content) {
            saveAndRender(t.path, newContent)
            return { ...t, content: newContent, dirty: newContent !== t.originalContent }
          }
        }
        return t
      }))
    }
  }, [saveAndRender])

  return (
    <div className="flex flex-col h-full border-r border-border">
      {error && (
        <div role="alert" className="px-3 py-1.5 text-xs bg-destructive/15 text-destructive">
          {error}
          {errorForkable && onForkRequest && (
            <button type="button" onClick={onForkRequest} className="ml-2 underline font-medium">{t('editor.fork_to_save')}</button>
          )}
          <button type="button" onClick={() => { setError(null); setErrorForkable(false) }} className="ml-2 underline">{t('editor.dismiss')}</button>
        </div>
      )}

      {/* File tree */}
      <div className="flex-none border-b border-border">
        <div className="flex items-center justify-between px-3 py-1.5">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Files</span>
          <Button variant="ghost" size="icon" className="min-h-[44px] min-w-[44px] md:h-6 md:w-6 md:min-h-0 md:min-w-0" onClick={() => { setNewFileName(''); setShowNewFileDialog(true) }} title="New file">
            <Plus className="h-3.5 w-3.5" />
            <span className="sr-only">New file</span>
          </Button>
        </div>
        {loading ? (
          <div className="px-3 py-2 text-xs text-muted-foreground flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" /> Loading...
          </div>
        ) : (
          <ul className="max-h-40 overflow-y-auto text-xs" role="listbox" aria-label="Project files">
            {files.map(f => (
              <li key={f.path} role="option" aria-selected={activeTab === f.path}>
                <div
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e: React.KeyboardEvent<HTMLDivElement>) => e.key === 'Enter' && openFile(f.path)}
                  className={`w-full text-left px-3 py-1 min-h-[44px] md:min-h-0 hover:bg-muted focus-visible:bg-muted focus-visible:outline-none flex items-center gap-1.5 group cursor-pointer ${activeTab === f.path ? 'bg-muted font-medium' : ''}`}
                  onClick={() => openFile(f.path)}
                >
                  <FileCode className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate flex-1">{f.path}</span>
                  <button
                    type="button"
                    className="opacity-100 md:opacity-0 md:group-hover:opacity-100 min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0 flex items-center justify-center text-muted-foreground hover:text-destructive focus-visible:opacity-100"
                    onClick={(e: React.MouseEvent<HTMLButtonElement>) => handleDeleteFile(f.path, e)}
                    title="Delete file"
                  >
                    <X className="h-3 w-3" />
                    <span className="sr-only">Delete {f.path}</span>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Tabs */}
      {openTabs.length > 0 && (
        <div className="flex-none flex items-center border-b border-border overflow-x-auto" role="tablist">
          {openTabs.map(t => (
            <button
              key={t.path}
              type="button"
              role="tab"
              aria-selected={t.path === activeTab}
              className={`flex items-center gap-1 px-3 py-1.5 text-xs border-r border-border whitespace-nowrap ${t.path === activeTab ? 'bg-background text-foreground' : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                }`}
              onClick={() => setActiveTab(t.path)}
            >
              {t.dirty && <span className="w-1.5 h-1.5 rounded-full bg-primary" title="Unsaved changes" />}
              {t.path.split('/').pop()}
              <button
                type="button"
                className="ml-1 min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0 flex items-center justify-center text-muted-foreground hover:text-foreground"
                onClick={(e: React.MouseEvent<HTMLButtonElement>) => closeTab(t.path, e)}
              >
                <X className="h-3 w-3" />
                <span className="sr-only">Close {t.path}</span>
              </button>
            </button>
          ))}
          {saving && <Loader2 className="h-3 w-3 animate-spin ml-2 text-muted-foreground" />}
        </div>
      )}

      {/* AI toggle in tab bar area */}
      {openTabs.length > 0 && (
        <div className="flex-none flex items-center justify-end px-2 py-0.5 border-b border-border">
          <Button
            variant={aiOpen ? 'secondary' : 'ghost'}
            size="sm"
            className="min-h-[44px] md:h-6 md:min-h-0 text-xs md:text-[10px] gap-1"
            onClick={() => setAiOpen(prev => !prev)}
          >
            <Sparkles className="h-3 w-3" />
            AI
          </Button>
        </div>
      )}

      {/* Text / Graph toggle — only meaningful for node-graph documents */}
      {isGraphFile && (
        <div className="flex items-center gap-1 border-b border-border px-2 py-1">
          <Button
            size="sm"
            variant={graphView ? 'ghost' : 'secondary'}
            className="h-7 min-h-[44px] md:min-h-0 px-2 text-xs"
            onClick={() => setGraphView(false)}
            aria-pressed={!graphView}
          >
            Text
          </Button>
          <Button
            size="sm"
            variant={graphView ? 'secondary' : 'ghost'}
            className="h-7 min-h-[44px] md:min-h-0 px-2 text-xs"
            onClick={() => setGraphView(true)}
            aria-pressed={graphView}
          >
            Graph
          </Button>
        </div>
      )}

      {/* Editor */}
      <div className={showCanvas ? 'flex-1 min-h-[200px] overflow-hidden' : 'flex-1 min-h-[200px]'}>
        {showCanvas ? (
          <Suspense fallback={<div className="flex h-full items-center justify-center text-xs text-muted-foreground">Loading graph view…</div>}>
            <GraphEditor
              content={activeContent}
              fileName={(activeTab ?? 'graph.graph.json').split('/').pop() ?? 'graph.graph.json'}
              onDocumentChange={handleGraphChange}
              manifestParameters={manifestParameters}
              partIds={partIds}
              bindings={draftBindings}
              bindable={bindable}
              onBindingsChange={handleGraphBindingsChange}
              bindBlockedReason={bindBlocked}
              saveBlockedReason={graphSaveBlocked}
              saveStatus={graphSaveStatus}
              saveError={graphPersistence.error}
              onSave={handleSave}
              onForkRequest={onForkRequest}
              selectedId={graphSelection}
              onSelect={setGraphSelection}
            />
          </Suspense>
        ) : activeTab ? (
          <Editor
            language={isGraphFile ? 'json' : SCAD_LANGUAGE_ID}
            value={activeContent}
            onChange={handleContentChange}
            onMount={handleEditorMount}
            theme={theme === 'dark' ? 'vs-dark' : 'light'}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              tabSize: 2,
              automaticLayout: true,
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            Select a file to edit
          </div>
        )}
      </div>

      {activeTab && isGraphFile && (
        <GraphIssues content={activeContent} onSelectNode={showCanvas ? setGraphSelection : undefined} />
      )}

      {/* AI Code Editor panel */}
      {aiOpen && (
        <div className="flex-none h-56 border-t border-border">
          <Suspense fallback={<div className="flex items-center justify-center h-full text-xs text-muted-foreground">Loading AI...</div>}>
            <AiChatPanel
              mode="code-editor"
              projectSlug={slug}
              manifest={manifest}
              fileContents={getFileContents()}
              onApplyEdits={handleApplyEdits}
            />
          </Suspense>
        </div>
      )}

      {/* New file dialog */}
      <AlertDialog open={showNewFileDialog} onOpenChange={setShowNewFileDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>New SCAD File</AlertDialogTitle>
            <AlertDialogDescription>
              Enter a name for the new file. It will be created with a .scad extension.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Input
            value={newFileName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewFileName(e.target.value)}
            placeholder="e.g. part.scad"
            onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => { if (e.key === 'Enter') handleNewFileConfirm() }}
            autoFocus
          />
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setShowNewFileDialog(false); setNewFileName('') }}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleNewFileConfirm} disabled={!newFileName.trim()}>Create</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
