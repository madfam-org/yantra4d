import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react'
import Editor from '@monaco-editor/react'
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
import { useTheme } from '../../contexts/ThemeProvider'
import { listFiles, readFile, createFile, deleteFile } from '../../services/domain/editorService'
import { registerScadLanguage, SCAD_LANGUAGE_ID } from '../../lib/scad-language'
import { useEditorRender } from '../../hooks/useEditorRender'

/**
 * Monaco-based SCAD code editor with file tree, tabs, and auto-render.
 */
export default function ScadEditor({ slug, handleGenerate, manifest }) {
  const { theme } = useTheme()
  const [files, setFiles] = useState([])
  const [openTabs, setOpenTabs] = useState([]) // array of { path, content, dirty }
  const [activeTab, setActiveTab] = useState(null) // path string
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [aiOpen, setAiOpen] = useState(false)
  const [showNewFileDialog, setShowNewFileDialog] = useState(false)
  const [newFileName, setNewFileName] = useState('')
  const editorRef = useRef(null)
  const monacoRef = useRef(null)

  const { saveAndRender, saveImmediate } = useEditorRender({ slug, handleGenerate })

  // Load file list
  useEffect(() => {
    let cancelled = false
    listFiles(slug)
      .then(f => { if (!cancelled) { setFiles(f); setError(null); setLoading(false) } })
      .catch(e => { if (!cancelled) { setError(e.message); setLoading(false) } })
    return () => { cancelled = true }
  }, [slug])

  const handleEditorMount = useCallback((editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco
    registerScadLanguage(monaco)
  }, [])

  const openFile = useCallback(async (path) => {
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
      setError(e.message)
    }
  }, [slug, openTabs])

  const closeTab = useCallback((path, e) => {
    if (e) e.stopPropagation()
    setOpenTabs(prev => prev.filter(t => t.path !== path))
    if (activeTab === path) {
      const remaining = openTabs.filter(t => t.path !== path)
      setActiveTab(remaining.length > 0 ? remaining[remaining.length - 1].path : null)
    }
  }, [activeTab, openTabs])

  const handleContentChange = useCallback((value) => {
    if (!activeTab) return
    setOpenTabs(prev => prev.map(t =>
      t.path === activeTab
        ? { ...t, content: value, dirty: value !== t.originalContent }
        : t
    ))
    saveAndRender(activeTab, value)
  }, [activeTab, saveAndRender])

  const handleSave = useCallback(async () => {
    const tab = openTabs.find(t => t.path === activeTab)
    if (!tab || !tab.dirty) return
    setSaving(true)
    try {
      await saveImmediate(tab.path, tab.content)
      setOpenTabs(prev => prev.map(t =>
        t.path === activeTab ? { ...t, originalContent: t.content, dirty: false } : t
      ))
    } catch (e) {
      setError(e.message)
    }
    setSaving(false)
  }, [activeTab, openTabs, saveImmediate])

  // Ctrl+S handler
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleSave])

  const handleNewFile = useCallback(async (name) => {
    if (!name || !name.endsWith('.scad')) return
    try {
      await createFile(slug, name)
      const updated = await listFiles(slug)
      setFiles(updated)
      openFile(name)
    } catch (e) {
      setError(e.message)
    }
  }, [slug, openFile])

  const handleNewFileConfirm = useCallback(() => {
    const name = newFileName.trim()
    if (!name) return
    const finalName = name.endsWith('.scad') ? name : `${name}.scad`
    setShowNewFileDialog(false)
    setNewFileName('')
    handleNewFile(finalName)
  }, [newFileName, handleNewFile])

  const handleDeleteFile = useCallback(async (path, e) => {
    if (e) e.stopPropagation()
    if (!confirm(`Delete ${path}?`)) return
    try {
      await deleteFile(slug, path)
      closeTab(path)
      const updated = await listFiles(slug)
      setFiles(updated)
    } catch (err) {
      setError(err.message)
    }
  }, [slug, closeTab])

  const activeContent = openTabs.find(t => t.path === activeTab)?.content || ''

  // Build file contents map for AI code editor
  const getFileContents = useCallback(() => {
    const contents = {}
    for (const tab of openTabs) {
      contents[tab.path] = tab.content
    }
    return contents
  }, [openTabs])

  const handleApplyEdits = useCallback((edits) => {
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
        <div className="px-3 py-1.5 text-xs bg-destructive/15 text-destructive">
          {error}
          <button type="button" onClick={() => setError(null)} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* File tree */}
      <div className="flex-none border-b border-border">
        <div className="flex items-center justify-between px-3 py-1.5">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Files</span>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => { setNewFileName(''); setShowNewFileDialog(true) }} title="New file">
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
                  onKeyDown={e => e.key === 'Enter' && openFile(f.path)}
                  className={`w-full text-left px-3 py-1 hover:bg-muted focus-visible:bg-muted focus-visible:outline-none flex items-center gap-1.5 group cursor-pointer ${activeTab === f.path ? 'bg-muted font-medium' : ''}`}
                  onClick={() => openFile(f.path)}
                >
                  <FileCode className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate flex-1">{f.path}</span>
                  <button
                    type="button"
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive focus-visible:opacity-100"
                    onClick={(e) => handleDeleteFile(f.path, e)}
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
                className="ml-1 text-muted-foreground hover:text-foreground"
                onClick={(e) => closeTab(t.path, e)}
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
            className="h-6 text-[10px] gap-1"
            onClick={() => setAiOpen(prev => !prev)}
          >
            <Sparkles className="h-3 w-3" />
            AI
          </Button>
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 min-h-0">
        {activeTab ? (
          <Editor
            language={SCAD_LANGUAGE_ID}
            value={activeContent}
            onChange={handleContentChange}
            onMount={handleEditorMount}
            theme={theme === 'dark' ? 'vs-dark' : 'light'}
            options={{
              minimap: { enabled: false },
              fontSize: 13,
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
            onChange={e => setNewFileName(e.target.value)}
            placeholder="e.g. part.scad"
            onKeyDown={e => { if (e.key === 'Enter') handleNewFileConfirm() }}
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
