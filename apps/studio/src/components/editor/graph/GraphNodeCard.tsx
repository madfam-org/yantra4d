import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import type { NodeProps, Node } from '@xyflow/react'
import { useLanguage } from '../../../contexts/system/LanguageProvider'
import type { GraphIssue, GraphNode, NodeTypeSpec } from '../../../lib/graph/graphDocument'

export const OUTPUT_HANDLE = 'out'

export interface GraphNodeData extends Record<string, unknown> {
  node: GraphNode
  spec: NodeTypeSpec | undefined
  issues: GraphIssue[]
  parts: string[]
  boundParams: string[]
}

export type GraphFlowNode = Node<GraphNodeData, 'graphNode'>

/**
 * One node on the canvas: a target handle per input socket (left), one
 * output handle (right), and the problems the validator attached to it.
 * Profiles are dashed and cool, solids solid and warm — the socket type is the
 * one thing that decides what may connect to what, so it is visible.
 */
function GraphNodeCard({ data, selected }: NodeProps<GraphFlowNode>) {
  const { t } = useLanguage()
  const { node, spec, issues, parts, boundParams } = data
  const output = spec?.output ?? 'solid'
  const isProfile = output !== 'solid'
  const sockets = Object.entries(spec?.inputs ?? {})
  const nodeIssues = issues.filter((i) => !i.socket)
  const hasIssue = issues.length > 0

  return (
    <div
      data-testid={`graph-node-${node.id}`}
      data-has-issue={hasIssue ? 'true' : 'false'}
      className={[
        'rounded-md border-[1.5px] px-2.5 py-1.5 text-[11px] leading-tight min-w-[150px] bg-card',
        isProfile ? 'border-dashed border-[#6d5ae6] bg-[rgba(109,90,230,0.08)]' : 'border-solid border-[#0e7c66] bg-[rgba(14,124,102,0.08)]',
        hasIssue ? 'ring-2 ring-destructive/70' : '',
        selected ? 'outline outline-2 outline-primary' : '',
      ].join(' ')}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono font-semibold">{node.id}</span>
        <span className="text-[10px] opacity-70">{node.type}</span>
      </div>

      {sockets.length > 0 && (
        <ul className="mt-1 space-y-1">
          {sockets.map(([socket, type]) => {
            const socketIssue = issues.find((i) => i.socket === socket)
            return (
              <li key={socket} className="relative pl-2 text-[10px]" data-testid={`graph-socket-${node.id}-${socket}`}>
                <Handle
                  type="target"
                  id={socket}
                  position={Position.Left}
                  className={socketIssue ? '!bg-destructive' : type === 'solid' ? '!bg-[#0e7c66]' : '!bg-[#6d5ae6]'}
                  style={{ left: -11, top: '50%' }}
                  aria-label={t('graph.socket_handle', { socket, type })}
                />
                <span className={socketIssue ? 'text-destructive font-medium' : ''} title={socketIssue?.message}>
                  {socket}
                </span>
                <span className="ml-1 opacity-60">{type}</span>
              </li>
            )
          })}
        </ul>
      )}

      {boundParams.length > 0 && (
        <div className="mt-1 text-[10px] opacity-80">⇠ {boundParams.join(', ')}</div>
      )}
      {parts.length > 0 && (
        <div className="mt-1 text-[10px] font-medium">▸ {parts.join(', ')}</div>
      )}
      {nodeIssues.length > 0 && (
        <div className="mt-1 text-[10px] text-destructive" title={nodeIssues.map((i) => i.message).join('\n')}>
          {t('graph.node_issue_count', { count: nodeIssues.length })}
        </div>
      )}

      <Handle
        type="source"
        id={OUTPUT_HANDLE}
        position={Position.Right}
        className={isProfile ? '!bg-[#6d5ae6]' : '!bg-[#0e7c66]'}
        aria-label={t('graph.output_handle', { type: output })}
      />
    </div>
  )
}

export default memo(GraphNodeCard)
