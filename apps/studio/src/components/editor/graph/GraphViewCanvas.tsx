import { useCallback, useMemo, useState } from 'react'
import { Background, Controls, MiniMap, ReactFlow, ReactFlowProvider, applyNodeChanges } from '@xyflow/react'
import type { Edge, NodeChange, NodeMouseHandler } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useLanguage } from '../../../contexts/system/LanguageProvider'
import { useTheme } from '../../../contexts/system/ThemeProvider'
import { NODE_TYPES } from '../../../lib/graph/graphDocument'
import type { GraphDoc } from '../../../lib/graph/graphDocument'
import { bindingKey } from '../../../lib/graph/graphBindings'
import type { BindingMap } from '../../../lib/graph/graphBindings'
import { layoutNodes } from '../../../lib/graph/graphLayout'
import { partsByNode } from '../../../lib/graph/graphReadOnly'
import GraphNodeCard, { OUTPUT_HANDLE } from './GraphNodeCard'
import type { GraphFlowNode } from './GraphNodeCard'

export interface GraphViewCanvasProps {
  doc: GraphDoc
  bindings: BindingMap
  selectedId: string | null
  onSelect: (nodeId: string | null) => void
  /** Nodes driven by the parameter the visitor is hovering or changing. */
  highlighted: Set<string>
}

const nodeTypes = { graphNode: GraphNodeCard }

/**
 * The graph as boxes and wires, read-only: the editor's node cards and layout,
 * with pan, zoom and a minimap, and nothing that changes the document (no
 * palette, no connecting, no dragging, no delete key, no save).
 */
function GraphViewCanvasInner({ doc, bindings, selectedId, onSelect, highlighted }: GraphViewCanvasProps) {
  const { t } = useLanguage()
  const { theme } = useTheme()

  const derivedNodes = useMemo<GraphFlowNode[]>(() => {
    const positions = layoutNodes(doc.nodes)
    const parts = partsByNode(doc)
    return doc.nodes.map((node) => ({
      id: node.id,
      type: 'graphNode',
      position: positions.get(node.id) ?? { x: 0, y: 0 },
      selected: node.id === selectedId,
      draggable: false,
      connectable: false,
      deletable: false,
      data: {
        node,
        spec: NODE_TYPES[node.type],
        issues: [],
        parts: parts.get(node.id) ?? [],
        boundParams: Object.keys(NODE_TYPES[node.type]?.params ?? {}).filter((param) =>
          Object.values(bindings).some((targets) => targets.includes(bindingKey(node.id, param))),
        ),
        highlighted: highlighted.has(node.id),
      },
    }))
  }, [doc, bindings, selectedId, highlighted])

  // React Flow measures every node after it mounts and hides a node it has not
  // measured. New node objects (a hover mark, a selection) would drop those
  // measurements and blank the canvas for a frame on every slider move, so the
  // last measurements are carried onto each new set, as the editor does. Only
  // measurement changes are applied: nothing the visitor does moves, removes
  // or reselects a node through React Flow.
  const [nodes, setNodes] = useState<GraphFlowNode[]>(derivedNodes)
  const [nodesSource, setNodesSource] = useState(derivedNodes)
  if (nodesSource !== derivedNodes) {
    setNodesSource(derivedNodes)
    setNodes((current) => {
      const measured = new Map(current.map((n) => [n.id, n]))
      return derivedNodes.map((n) => {
        const prev = measured.get(n.id)
        return prev?.measured ? { ...n, measured: prev.measured, width: prev.width, height: prev.height } : n
      })
    })
  }
  const onNodesChange = useCallback((changes: NodeChange<GraphFlowNode>[]) => {
    const dimensions = changes.filter((c) => c.type === 'dimensions')
    if (dimensions.length > 0) setNodes((current) => applyNodeChanges(dimensions, current))
  }, [])

  const edges = useMemo<Edge[]>(() => {
    const ids = new Set(doc.nodes.map((n) => n.id))
    return doc.nodes.flatMap((node) =>
      Object.entries(node.inputs ?? {})
        .filter(([, ref]) => ids.has(ref))
        .map(([socket, ref]) => ({
          id: `${ref}->${node.id}.${socket}`,
          source: ref,
          sourceHandle: OUTPUT_HANDLE,
          target: node.id,
          targetHandle: socket,
          deletable: false,
          style: { strokeWidth: highlighted.has(node.id) && highlighted.has(ref) ? 2.5 : 1.5 },
        })),
    )
  }, [doc, highlighted])

  const onNodeClick = useCallback<NodeMouseHandler<GraphFlowNode>>((_e, node) => {
    onSelect(node.id === selectedId ? null : node.id)
  }, [onSelect, selectedId])

  return (
    <div className="relative h-full min-h-[160px]" data-testid="graph-view-canvas" aria-label={t('inside.canvas_label')} role="group">
      <ReactFlow<GraphFlowNode>
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onNodeClick={onNodeClick}
        onPaneClick={() => onSelect(null)}
        nodesDraggable={false}
        nodesConnectable={false}
        edgesFocusable={false}
        elementsSelectable
        deleteKeyCode={null}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        colorMode={theme === 'dark' || theme === 'light' ? theme : 'system'}
        proOptions={{ hideAttribution: false }}
      >
        <Background gap={16} size={1} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable className="!bg-card" style={{ width: 120, height: 80 }} />
      </ReactFlow>
    </div>
  )
}

export default function GraphViewCanvas(props: GraphViewCanvasProps) {
  return (
    <ReactFlowProvider>
      <GraphViewCanvasInner {...props} />
    </ReactFlowProvider>
  )
}
