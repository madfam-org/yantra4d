import { useMemo } from 'react'
import { validateGraph, topologicalOrder, NODE_TYPES } from '../../lib/graph/graphDocument'
import type { GraphDoc } from '../../lib/graph/graphDocument'

interface GraphIssuesProps {
  /** Current editor buffer for a .graph.json file. */
  content: string
}

/**
 * Live validation for a graph document being edited.
 *
 * The server refuses to save a graph the transpiler would reject, but that
 * answer only arrives on the save round-trip. This runs the same rules against
 * the buffer as the author types, so a dangling input or a cycle is visible
 * immediately — and when the document is valid, it shows the evaluation order
 * the transpiler will emit, which is the thing a node graph otherwise hides.
 */
export default function GraphIssues({ content }: GraphIssuesProps) {
  const result = useMemo(() => {
    const trimmed = content.trim()
    if (!trimmed) return { kind: 'empty' as const }

    let parsed: unknown
    try {
      parsed = JSON.parse(trimmed)
    } catch (err) {
      return { kind: 'unparseable' as const, message: (err as Error).message }
    }

    const issues = validateGraph(parsed)
    if (issues.length > 0) return { kind: 'invalid' as const, issues }

    const doc = parsed as GraphDoc
    return {
      kind: 'valid' as const,
      order: topologicalOrder(doc.nodes) ?? [],
      nodes: doc.nodes,
      outputs: doc.outputs,
    }
  }, [content])

  if (result.kind === 'empty') return null

  if (result.kind === 'unparseable') {
    return (
      <div className="border-t border-border bg-destructive/5 px-3 py-2 text-xs" role="status">
        <span className="font-medium text-destructive">Not valid JSON</span>
        <span className="ml-2 text-muted-foreground">{result.message}</span>
      </div>
    )
  }

  if (result.kind === 'invalid') {
    return (
      <div className="border-t border-border bg-destructive/5 px-3 py-2 text-xs" role="status">
        <div className="font-medium text-destructive mb-1">
          {result.issues.length} problem{result.issues.length === 1 ? '' : 's'} — this will not save
        </div>
        <ul className="space-y-0.5 max-h-32 overflow-y-auto">
          {result.issues.map((issue, i) => (
            <li key={`${issue.nodeId ?? ''}-${i}`} className="text-muted-foreground">
              {issue.nodeId && <span className="font-mono text-foreground">{issue.nodeId}: </span>}
              {issue.message}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  const parts = Object.entries(result.outputs)
  return (
    <div className="border-t border-border bg-secondary/30 px-3 py-2 text-xs" role="status">
      <div className="font-medium text-foreground mb-1">
        Valid · {result.nodes.length} node{result.nodes.length === 1 ? '' : 's'} ·{' '}
        {parts.length} part{parts.length === 1 ? '' : 's'}
      </div>
      <div className="text-muted-foreground">
        <span className="uppercase tracking-wide text-[10px] mr-1">Order</span>
        <span className="font-mono">
          {result.order
            .map((id) => {
              const node = result.nodes.find((n) => n.id === id)
              const kind = node ? NODE_TYPES[node.type]?.output : undefined
              return kind === 'profile' ? `${id}*` : id
            })
            .join(' → ')}
        </span>
      </div>
      {result.order.some((id) => {
        const node = result.nodes.find((n) => n.id === id)
        return node && NODE_TYPES[node.type]?.output === 'profile'
      }) && (
        <div className="text-muted-foreground mt-0.5 text-[10px]">* profile — consumed by extrude</div>
      )}
    </div>
  )
}
