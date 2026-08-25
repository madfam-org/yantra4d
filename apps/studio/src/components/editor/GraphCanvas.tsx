import { useMemo } from 'react'
import { ReactFlow, Background, Controls, MiniMap } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  validateGraph,
  dependencyDepth,
  NODE_TYPES,
} from '../../lib/graph/graphDocument'
import type { GraphDoc, GraphNode } from '../../lib/graph/graphDocument'

interface GraphCanvasProps {
  /** Current editor buffer for a .graph.json file. */
  content: string
}

const COLUMN_WIDTH = 210
const ROW_HEIGHT = 92

/** Lay nodes out left-to-right by dependency depth: sources first, part last. */
function layout(nodes: GraphNode[]) {
  const depth = dependencyDepth(nodes)
  if (!depth) return null
  const perColumn = new Map<number, number>()
  return nodes.map((node) => {
    const column = depth.get(node.id) ?? 0
    const row = perColumn.get(column) ?? 0
    perColumn.set(column, row + 1)
    return { node, x: column * COLUMN_WIDTH, y: row * ROW_HEIGHT }
  })
}

/**
 * Renders a graph document as a graph.
 *
 * Read-only for now: positions are derived from dependency depth rather than
 * stored, so nothing here can change the document and there is no save path to
 * get wrong. Editing arrives with the palette and drag-to-connect, both of
 * which will go through the model's `connect()` — it already refuses socket
 * type mismatches and cycles.
 */
export default function GraphCanvas({ content }: GraphCanvasProps) {
  const graph = useMemo(() => {
    try {
      const parsed = JSON.parse(content)
      if (validateGraph(parsed).length > 0) return null
      return parsed as GraphDoc
    } catch {
      return null
    }
  }, [content])

  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] }
    const placed = layout(graph.nodes)
    if (!placed) return { nodes: [], edges: [] }

    const outputFor = new Map<string, string[]>()
    for (const [partId, ref] of Object.entries(graph.outputs)) {
      outputFor.set(ref, [...(outputFor.get(ref) ?? []), partId])
    }

    const flowNodes = placed.map(({ node, x, y }) => {
      const isProfile = NODE_TYPES[node.type]?.output === 'profile'
      const parts = outputFor.get(node.id)
      return {
        id: node.id,
        position: { x, y },
        data: {
          label: (
            <div className="text-left leading-tight">
              <div className="font-mono text-[11px] font-semibold">{node.id}</div>
              <div className="text-[10px] opacity-70">{node.type}</div>
              {parts && (
                <div className="text-[10px] mt-0.5 font-medium">▸ {parts.join(', ')}</div>
              )}
            </div>
          ),
        },
        // Profiles read as dashed and cool; solids as solid and warm, so the
        // one thing that changes what may connect to what is visible at a glance.
        style: {
          borderRadius: 6,
          padding: '6px 10px',
          fontSize: 11,
          border: isProfile ? '1.5px dashed #6d5ae6' : '1.5px solid #0e7c66',
          background: isProfile ? 'rgba(109,90,230,0.08)' : 'rgba(14,124,102,0.08)',
          width: COLUMN_WIDTH - 50,
        },
      }
    })

    const flowEdges = graph.nodes.flatMap((node) =>
      Object.entries(node.inputs ?? {}).map(([socket, ref]) => ({
        id: `${ref}->${node.id}.${socket}`,
        source: ref,
        target: node.id,
        label: socket,
        labelStyle: { fontSize: 9 },
        style: { strokeWidth: 1.5 },
        animated: false,
      })),
    )

    return { nodes: flowNodes, edges: flowEdges }
  }, [graph])

  if (!graph) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-xs text-muted-foreground">
        The graph view appears once the document is valid. Problems are listed below the editor.
      </div>
    )
  }

  return (
    <div className="h-full w-full" data-testid="graph-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: false }}
      >
        <Background gap={16} size={1} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable className="!bg-card" />
      </ReactFlow>
    </div>
  )
}
