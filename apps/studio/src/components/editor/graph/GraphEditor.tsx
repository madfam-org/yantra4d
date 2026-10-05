import { useCallback, useMemo, useState } from 'react'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  applyNodeChanges,
  useReactFlow,
} from '@xyflow/react'
import type { Connection, Edge, EdgeChange, NodeChange, OnNodeDrag } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Download, GitFork, ListTree, Loader2, Save, Shapes, Variable } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLanguage } from '../../../contexts/system/LanguageProvider'
import { useTheme } from '../../../contexts/system/ThemeProvider'
import {
  NODE_TYPES,
  addNode,
  connect,
  connectionProblem,
  disconnect,
  removeNode,
  serializeGraph,
  setNodePosition,
  validateGraph,
} from '../../../lib/graph/graphDocument'
import type { GraphDoc, GraphIssue, NodePosition } from '../../../lib/graph/graphDocument'
import { bindingChanges, bindingConflicts, bindingKey, dropNodeBindings } from '../../../lib/graph/graphBindings'
import type { BindingMap } from '../../../lib/graph/graphBindings'
import { buildScope, checkExpression } from '../../../lib/graph/graphExpressions'
import type { ManifestParameterLike } from '../../../lib/graph/graphExpressions'
import { layoutNodes, nextFreePosition } from '../../../lib/graph/graphLayout'
import GraphNodeCard, { OUTPUT_HANDLE } from './GraphNodeCard'
import type { GraphFlowNode } from './GraphNodeCard'
import GraphPalette, { PALETTE_DRAG_TYPE } from './GraphPalette'
import GraphInspector from './GraphInspector'
import GraphDeclarations from './GraphDeclarations'

export type GraphSaveStatus = 'clean' | 'dirty' | 'saving' | 'saved' | 'error'

export interface GraphEditorProps {
  /** The .graph.json buffer. The editor is a view of it: every edit is emitted as new text. */
  content: string
  fileName: string
  /**
   * `layoutOnly` is true when only node positions changed — no geometry, so no
   * render. `bindings` is set when the same edit also changed the manifest
   * bindings (removing a bound node), so both are saved together.
   */
  onDocumentChange: (content: string, opts: { layoutOnly: boolean; bindings?: BindingMap }) => void
  manifestParameters: ManifestParameterLike[]
  partIds: string[]
  bindings: BindingMap
  bindable: ManifestParameterLike[]
  onBindingsChange: (map: BindingMap) => void
  /** Why bindings cannot be edited here, or null. */
  bindBlockedReason: string | null
  /** Why this project cannot be saved to (a commons cartridge…), or null. */
  saveBlockedReason: string | null
  saveStatus: GraphSaveStatus
  saveError?: string | null
  onSave: () => void
  onForkRequest?: () => void
  /** Selected node id, owned by the caller so the issue list can select a node. */
  selectedId: string | null
  onSelect: (nodeId: string | null) => void
}

const nodeTypes = { graphNode: GraphNodeCard }

function parse(content: string): { doc: GraphDoc | null; error: string | null } {
  try {
    const parsed = JSON.parse(content)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      return { doc: null, error: 'not-object' }
    }
    const doc = parsed as GraphDoc
    if (!Array.isArray(doc.nodes)) doc.nodes = []
    if (typeof doc.outputs !== 'object' || doc.outputs === null || Array.isArray(doc.outputs)) doc.outputs = {}
    if (!doc.nodes.every((n) => typeof n === 'object' && n !== null && typeof n.id === 'string')) {
      return { doc: null, error: 'bad-nodes' }
    }
    return { doc, error: null }
  } catch (err) {
    return { doc: null, error: (err as Error).message }
  }
}

function edgeId(source: string, target: string, socket: string) {
  return `${source}->${target}.${socket}`
}

function GraphEditorInner(props: GraphEditorProps) {
  const { t } = useLanguage()
  const { theme } = useTheme()
  const { screenToFlowPosition } = useReactFlow()
  const { doc } = useMemo(() => parse(props.content), [props.content])
  const { selectedId, onSelect: setSelectedId } = props
  // The palette starts open on an empty graph (there is nothing else to do) and
  // closed otherwise, so the canvas gets the room in a narrow editor column.
  const [paletteOpen, setPaletteOpen] = useState(() => (parse(props.content).doc?.nodes.length ?? 0) === 0)
  const [declarationsOpen, setDeclarationsOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const issues = useMemo<GraphIssue[]>(
    () => (doc ? [...validateGraph(doc), ...bindingConflicts(doc, props.bindings)] : []),
    [doc, props.bindings],
  )
  const manifestDefaults = useMemo(
    () => Object.fromEntries(props.manifestParameters.map((p) => [p.id, p.default])),
    [props.manifestParameters],
  )
  const scope = useMemo(() => (doc ? buildScope(doc, manifestDefaults).scope : {}), [doc, manifestDefaults])
  const derivedIds = useMemo(() => (doc?.derived ?? []).map((d) => d.id), [doc])
  const checkExpr = useCallback(
    (expr: string) => checkExpression(expr, doc?.parameters ?? {}, scope, derivedIds),
    [doc, scope, derivedIds],
  )

  const emit = useCallback((next: GraphDoc, layoutOnly = false, bindings?: BindingMap) => {
    props.onDocumentChange(serializeGraph(next, props.content), bindings ? { layoutOnly, bindings } : { layoutOnly })
  }, [props])

  // ── Canvas nodes: derived from the document, with React Flow's own changes
  // (measuring, dragging) applied on top until the document changes again.
  const derivedNodes = useMemo<GraphFlowNode[]>(() => {
    if (!doc) return []
    const positions = layoutNodes(doc.nodes)
    const partsFor = new Map<string, string[]>()
    for (const [part, ref] of Object.entries(doc.outputs)) partsFor.set(ref, [...(partsFor.get(ref) ?? []), part])
    return doc.nodes.map((node) => ({
      id: node.id,
      type: 'graphNode',
      position: positions.get(node.id) ?? { x: 0, y: 0 },
      selected: node.id === selectedId,
      data: {
        node,
        spec: NODE_TYPES[node.type],
        issues: issues.filter((i) => i.nodeId === node.id),
        parts: partsFor.get(node.id) ?? [],
        boundParams: Object.keys(NODE_TYPES[node.type]?.params ?? {}).filter((param) =>
          Object.values(props.bindings).some((targets) => targets.includes(bindingKey(node.id, param))),
        ),
      },
    }))
  }, [doc, issues, selectedId, props.bindings])

  const [flowNodes, setFlowNodes] = useState<GraphFlowNode[]>(derivedNodes)
  const [flowSource, setFlowSource] = useState(derivedNodes)
  if (flowSource !== derivedNodes) {
    setFlowSource(derivedNodes)
    setFlowNodes((current) => {
      const measured = new Map(current.map((n) => [n.id, n]))
      return derivedNodes.map((n) => {
        const prev = measured.get(n.id)
        return prev?.measured ? { ...n, measured: prev.measured, width: prev.width, height: prev.height } : n
      })
    })
  }

  const edges = useMemo<Edge[]>(() => {
    if (!doc) return []
    const ids = new Set(doc.nodes.map((n) => n.id))
    return doc.nodes.flatMap((node) =>
      Object.entries(node.inputs ?? {})
        .filter(([, ref]) => ids.has(ref))
        .map(([socket, ref]) => ({
          id: edgeId(ref, node.id, socket),
          source: ref,
          sourceHandle: OUTPUT_HANDLE,
          target: node.id,
          targetHandle: socket,
          data: { socket },
          style: { strokeWidth: 1.5 },
        })),
    )
  }, [doc])

  const onNodesChange = useCallback((changes: NodeChange<GraphFlowNode>[]) => {
    // React Flow reports a click on another node as two changes, in either
    // order: the new node selected and the old one deselected. Fold them.
    let next = selectedId
    for (const change of changes) {
      if (change.type !== 'select') continue
      if (change.selected) next = change.id
      else if (next === change.id) next = null
    }
    if (next !== selectedId) setSelectedId(next)
    setFlowNodes((nodes) => applyNodeChanges(changes.filter((c) => c.type !== 'remove'), nodes))
  }, [selectedId, setSelectedId])

  const onNodeDragStop = useCallback<OnNodeDrag<GraphFlowNode>>((_e, _node, dragged) => {
    if (!doc) return
    let next = doc
    for (const n of dragged) next = setNodePosition(next, n.id, n.position)
    emit(next, true)
  }, [doc, emit])

  const removeNodes = useCallback((ids: string[]) => {
    if (!doc || ids.length === 0) return
    let next = doc
    let map = props.bindings
    for (const id of ids) {
      next = removeNode(next, id)
      map = dropNodeBindings(map, id)
    }
    if (ids.includes(selectedId ?? '')) setSelectedId(null)
    const bindingsChanged = Object.keys(bindingChanges(props.bindings, map)).length > 0
    emit(next, false, bindingsChanged ? map : undefined)
  }, [doc, emit, props, selectedId, setSelectedId])

  const onConnect = useCallback((conn: Connection) => {
    if (!doc || !conn.targetHandle) return
    try {
      emit(connect(doc, conn.target, conn.targetHandle, conn.source))
      setNotice(null)
    } catch (err) {
      setNotice((err as Error).message)
    }
  }, [doc, emit])

  const isValidConnection = useCallback((conn: Connection | Edge) => {
    if (!doc || !conn.targetHandle) return false
    return connectionProblem(doc, conn.target, conn.targetHandle, conn.source) === null
  }, [doc])

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    if (!doc) return
    const removed = changes.filter((c) => c.type === 'remove')
    if (removed.length === 0) return
    let next = doc
    for (const change of removed) {
      const edge = edges.find((e) => e.id === change.id)
      if (edge?.targetHandle) next = disconnect(next, edge.target, edge.targetHandle)
    }
    emit(next)
  }, [doc, edges, emit])

  const add = useCallback((type: string, at?: NodePosition) => {
    if (!doc) return
    let next = addNode(doc, type)
    const created = next.nodes[next.nodes.length - 1]
    const position = at ?? nextFreePosition(layoutNodes(doc.nodes).values())
    next = setNodePosition(next, created.id, position)
    setSelectedId(created.id)
    emit(next)
  }, [doc, emit, setSelectedId])

  const onDrop = useCallback((event: React.DragEvent) => {
    const type = event.dataTransfer.getData(PALETTE_DRAG_TYPE)
    if (!type || !NODE_TYPES[type]) return
    event.preventDefault()
    add(type, screenToFlowPosition({ x: event.clientX, y: event.clientY }))
  }, [add, screenToFlowPosition])

  const exportGraph = useCallback(() => {
    if (!doc) return
    const blob = new Blob([serializeGraph(doc, props.content)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = props.fileName.endsWith('.graph.json') ? props.fileName : `${props.fileName}.graph.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }, [doc, props.content, props.fileName])

  if (!doc) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-xs text-muted-foreground" role="status">
        {t('graph.unparseable')}
      </div>
    )
  }

  const selected = doc.nodes.find((n) => n.id === selectedId) ?? null
  const statusText = {
    clean: t('graph.status_clean'),
    dirty: t('graph.status_dirty'),
    saving: t('graph.status_saving'),
    saved: t('graph.status_saved'),
    error: props.saveError ?? t('graph.status_error'),
  }[props.saveStatus]

  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="graph-editor">
      <div className="flex flex-wrap items-center gap-1 border-b border-border px-2 py-1" role="toolbar" aria-label={t('graph.toolbar')}>
        <Button size="sm" variant={paletteOpen ? 'secondary' : 'ghost'} className="h-7 px-2 text-xs gap-1"
          aria-pressed={paletteOpen} onClick={() => setPaletteOpen((v) => !v)}>
          <Shapes className="h-3 w-3" /> {t('graph.palette')}
        </Button>
        <Button size="sm" variant={declarationsOpen ? 'secondary' : 'ghost'} className="h-7 px-2 text-xs gap-1"
          aria-pressed={declarationsOpen} onClick={() => setDeclarationsOpen((v) => !v)}>
          <Variable className="h-3 w-3" /> {t('graph.declarations')}
        </Button>
        <Button size="sm" variant="ghost" className="h-7 px-2 text-xs gap-1" onClick={exportGraph}>
          <Download className="h-3 w-3" /> {t('graph.export')}
        </Button>
        {props.saveBlockedReason ? (
          props.onForkRequest && (
            <Button size="sm" variant="ghost" className="h-7 px-2 text-xs gap-1" onClick={props.onForkRequest}>
              <GitFork className="h-3 w-3" /> {t('graph.fork_to_save')}
            </Button>
          )
        ) : (
          <Button size="sm" variant="ghost" className="h-7 px-2 text-xs gap-1"
            disabled={props.saveStatus === 'saving' || props.saveStatus === 'clean'} onClick={props.onSave}>
            {props.saveStatus === 'saving' ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
            {t('graph.save')}
          </Button>
        )}
        <span className={`ml-auto text-[10px] ${props.saveStatus === 'error' ? 'text-destructive' : 'text-muted-foreground'}`}
          role="status" data-testid="graph-save-status">
          {props.saveBlockedReason ?? statusText}
        </span>
      </div>

      {paletteOpen && <GraphPalette onAdd={(type) => add(type)} />}
      {declarationsOpen && (
        <div className="max-h-56 overflow-y-auto border-b border-border">
          <GraphDeclarations
            doc={doc}
            manifestParameters={props.manifestParameters}
            scope={scope}
            issues={issues}
            onDocChange={(next) => emit(next)}
          />
        </div>
      )}
      {notice && (
        <div className="flex items-center gap-2 border-b border-border bg-destructive/10 px-3 py-1 text-[11px] text-destructive" role="alert">
          {notice}
          <button type="button" className="ml-auto underline" onClick={() => setNotice(null)}>{t('graph.dismiss')}</button>
        </div>
      )}

      <div className="relative min-h-[160px] flex-1" data-testid="graph-canvas"
        onDragOver={(e) => { if (e.dataTransfer.types.includes(PALETTE_DRAG_TYPE)) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy' } }}
        onDrop={onDrop}>
        {doc.nodes.length === 0 && (
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center px-6 text-center text-xs text-muted-foreground">
            {t('graph.empty')}
          </div>
        )}
        <ReactFlow<GraphFlowNode>
          nodes={flowNodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodesDelete={(deleted) => removeNodes(deleted.map((n) => n.id))}
          onNodeDragStop={onNodeDragStop}
          onConnect={onConnect}
          isValidConnection={isValidConnection}
          onPaneClick={() => setSelectedId(null)}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          // The editor column is narrow; let "fit view" really fit a 20-node graph.
          minZoom={0.2}
          colorMode={theme === 'dark' || theme === 'light' ? theme : 'system'}
          deleteKeyCode={['Backspace', 'Delete']}
          proOptions={{ hideAttribution: false }}
        >
          <Background gap={16} size={1} />
          <Controls showInteractive={false} />
          <MiniMap pannable zoomable className="!bg-card" style={{ width: 120, height: 80 }} />
        </ReactFlow>
      </div>

      {selected ? (
        <div className="max-h-[45%] shrink-0 overflow-y-auto border-t border-border">
          <GraphInspector
            doc={doc}
            node={selected}
            issues={issues.filter((i) => i.nodeId === selected.id)}
            bindings={props.bindings}
            bindable={props.bindable}
            bindBlockedReason={props.bindBlockedReason}
            manifestParameters={props.manifestParameters}
            partIds={props.partIds}
            checkExpression={checkExpr}
            onDocChange={(next) => emit(next)}
            onBindingsChange={props.onBindingsChange}
            onDelete={(id) => removeNodes([id])}
          />
        </div>
      ) : (
        <div className="border-t border-border px-3 py-1.5 text-[11px] text-muted-foreground">
          <ListTree className="inline h-3 w-3 mr-1" />
          {t('graph.select_hint')}
        </div>
      )}
    </div>
  )
}

/**
 * The writable graph editor: palette, drag-to-connect with socket type checks,
 * node params as literals, manifest bindings or expressions, declarations,
 * and save/export. Every edit goes through the immutable model in
 * `lib/graph/graphDocument.ts`, and the validator runs on every edit.
 */
export default function GraphEditor(props: GraphEditorProps) {
  return (
    <ReactFlowProvider>
      <GraphEditorInner {...props} />
    </ReactFlowProvider>
  )
}
