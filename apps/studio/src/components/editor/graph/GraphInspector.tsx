import { useState } from 'react'
import { Trash2, Unplug } from 'lucide-react'
import { useLanguage } from '../../../contexts/system/LanguageProvider'
import {
  LIMITS,
  NODE_TYPES,
  clearNodeParam,
  disconnect,
  removeOutput,
  setNodeParam,
  setOutput,
} from '../../../lib/graph/graphDocument'
import type { GraphDoc, GraphIssue, GraphNode } from '../../../lib/graph/graphDocument'
import { boundParameter, setBinding } from '../../../lib/graph/graphBindings'
import type { BindingMap } from '../../../lib/graph/graphBindings'
import { declareParameter } from '../../../lib/graph/graphExpressions'
import type { ExpressionCheck, ManifestParameterLike } from '../../../lib/graph/graphExpressions'
import GraphParamField from './GraphParamField'

interface GraphInspectorProps {
  doc: GraphDoc
  node: GraphNode
  issues: GraphIssue[]
  bindings: BindingMap
  bindable: ManifestParameterLike[]
  bindBlockedReason: string | null
  manifestParameters: ManifestParameterLike[]
  partIds: string[]
  checkExpression: (expr: string) => ExpressionCheck
  onDocChange: (doc: GraphDoc) => void
  onBindingsChange: (map: BindingMap) => void
  onDelete: (nodeId: string) => void
}

/** Edit the selected node: its params, its connections, the part it outputs, or delete it. */
export default function GraphInspector(props: GraphInspectorProps) {
  const { t } = useLanguage()
  const { doc, node, issues, bindings } = props
  const spec = NODE_TYPES[node.type]
  const outputsHere = Object.entries(doc.outputs).filter(([, ref]) => ref === node.id).map(([part]) => part)
  const [newPart, setNewPart] = useState('')
  const manifestIds = props.manifestParameters.map((p) => p.id)

  if (!spec) {
    return (
      <div className="px-3 py-2 text-xs text-destructive" data-testid="graph-inspector">
        {t('graph.unknown_type', { type: node.type })}
      </div>
    )
  }

  const declare = (id: string) => {
    if (Object.keys(doc.parameters ?? {}).length >= LIMITS.max_parameters) return
    const manifestParam = props.manifestParameters.find((p) => p.id === id)
    const fallback = manifestParam?.default
    const value = typeof fallback === 'number' || typeof fallback === 'boolean' || typeof fallback === 'string' ? fallback : 0
    props.onDocChange(declareParameter(doc, id, { default: value }))
  }

  const addPart = () => {
    const part = newPart.trim()
    if (!part) return
    props.onDocChange(setOutput(doc, part, node.id))
    setNewPart('')
  }

  const partChoices = props.partIds.filter((p) => !outputsHere.includes(p))

  return (
    <div className="text-xs" data-testid="graph-inspector">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border">
        <span className="font-mono font-semibold">{node.id}</span>
        <span className="text-muted-foreground">{node.type} → {spec.output}</span>
        <button
          type="button"
          className="ml-auto inline-flex items-center gap-1 text-destructive hover:underline min-h-[32px] md:min-h-0"
          onClick={() => props.onDelete(node.id)}
          aria-label={t('graph.delete_node', { id: node.id })}
        >
          <Trash2 className="h-3 w-3" /> {t('graph.delete')}
        </button>
      </div>

      {issues.filter((i) => !i.param && !i.socket).map((issue, i) => (
        <div key={i} className="px-3 py-1 text-[11px] text-destructive" role="alert">{issue.message}</div>
      ))}

      {Object.keys(spec.inputs).length > 0 && (
        <section className="px-3 py-1.5 border-b border-border" aria-label={t('graph.inputs')}>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">{t('graph.inputs')}</div>
          {Object.entries(spec.inputs).map(([socket, type]) => {
            const ref = node.inputs?.[socket]
            const issue = issues.find((i) => i.socket === socket)
            return (
              <div key={socket} className="flex items-center gap-1.5 py-0.5">
                <span className={`font-mono ${issue ? 'text-destructive font-semibold' : ''}`}>{socket}</span>
                <span className="text-[10px] text-muted-foreground">{type}</span>
                <span className="ml-auto font-mono">{ref ?? <span className="text-muted-foreground">{t('graph.unconnected')}</span>}</span>
                {ref && (
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-foreground"
                    onClick={() => props.onDocChange(disconnect(doc, node.id, socket))}
                    aria-label={t('graph.disconnect', { socket })}
                  >
                    <Unplug className="h-3 w-3" />
                  </button>
                )}
              </div>
            )
          })}
        </section>
      )}

      {Object.keys(spec.params).length > 0 && (
        <section className="px-3 py-1.5 border-b border-border" aria-label={t('graph.params')}>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">{t('graph.params')}</div>
          {props.bindBlockedReason && (
            <div className="text-[10px] text-muted-foreground mb-1">{props.bindBlockedReason}</div>
          )}
          {Object.entries(spec.params).map(([name, paramSpec]) => (
            <GraphParamField
              key={name}
              nodeId={node.id}
              name={name}
              spec={paramSpec}
              value={node.params?.[name]}
              boundTo={boundParameter(bindings, node.id, name)}
              bindable={props.bindable}
              bindBlockedReason={props.bindBlockedReason}
              checkExpression={props.checkExpression}
              manifestIds={manifestIds}
              issue={issues.find((i) => i.param === name)}
              onLiteral={(value) => props.onDocChange(setNodeParam(doc, node.id, name, value))}
              onReset={() => props.onDocChange(clearNodeParam(doc, node.id, name))}
              onBind={(pid) => props.onBindingsChange(setBinding(bindings, node.id, name, pid))}
              onExpression={(expr) => props.onDocChange(setNodeParam(doc, node.id, name, { expr }))}
              onDeclare={declare}
            />
          ))}
        </section>
      )}

      {spec.output === 'solid' && (
        <section className="px-3 py-1.5" aria-label={t('graph.output_parts')}>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">{t('graph.output_parts')}</div>
          {outputsHere.map((part) => (
            <div key={part} className="flex items-center gap-1.5 py-0.5">
              <span className="font-mono">▸ {part}</span>
              <button
                type="button"
                className="ml-auto text-[10px] underline text-muted-foreground"
                onClick={() => props.onDocChange(removeOutput(doc, part))}
              >
                {t('graph.remove_output')}
              </button>
            </div>
          ))}
          <div className="flex items-center gap-1 mt-0.5">
            <input
              list={`graph-parts-${node.id}`}
              aria-label={t('graph.output_part_id')}
              placeholder={t('graph.output_part_id')}
              className="flex-1 rounded border border-border bg-background px-1.5 py-0.5 text-[11px] font-mono min-h-[32px] md:min-h-0"
              value={newPart}
              onChange={(e) => setNewPart(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') addPart() }}
            />
            <datalist id={`graph-parts-${node.id}`}>
              {partChoices.map((p) => <option key={p} value={p} />)}
            </datalist>
            <button
              type="button"
              className="rounded border border-border px-1.5 py-0.5 text-[11px] hover:bg-muted min-h-[32px] md:min-h-0 disabled:opacity-50"
              onClick={addPart}
              disabled={!newPart.trim()}
            >
              {t('graph.set_output')}
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
