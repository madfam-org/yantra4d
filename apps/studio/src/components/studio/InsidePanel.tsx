import { useMemo, useState } from 'react'
import { ListTree, Loader2, RotateCcw, Workflow } from 'lucide-react'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Button } from '@/components/ui/button'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import GraphViewCanvas from '../editor/graph/GraphViewCanvas'
import { NODE_TYPES, topologicalOrder } from '../../lib/graph/graphDocument'
import type { GraphDoc, GraphNode } from '../../lib/graph/graphDocument'
import type { BindingMap } from '../../lib/graph/graphBindings'
import {
  formatValue,
  nodesDrivenBy,
  paramRows,
  partsByNode,
  readGraph,
  socketRows,
} from '../../lib/graph/graphReadOnly'
import type { ParamRow } from '../../lib/graph/graphReadOnly'
import type { ModeGraphState } from '../../hooks/project/useModeGraph'

export type InsideLayout = 'canvas' | 'list'

export interface InsidePanelProps {
  state: ModeGraphState
  onRetry: () => void
  bindings: BindingMap
  /** Current manifest parameter values, so a bound input shows what drives it now. */
  values: Record<string, unknown>
  /** A manifest parameter's label in the visitor's language. */
  labelOf: (parameterId: string) => string
  /** The parameter the visitor is hovering or changing, or null. */
  activeParamId: string | null
}

const RAIL = 'h-9 rounded-md bg-muted p-1'
const RAIL_ITEM = 'h-7 min-w-0 rounded-sm px-2.5 text-xs font-medium text-muted-foreground hover:bg-transparent hover:text-foreground data-[state=on]:bg-background data-[state=on]:text-foreground data-[state=on]:shadow-sm'

/**
 * "Inside": a cartridge's node graph, read-only, beside the 3D view. The
 * canvas and an ordered list show the same nodes (the canvas is never the only
 * way to read the graph); selecting one shows what drives each of its inputs.
 * Nodes driven by the parameter the visitor is hovering or changing are marked.
 */
export default function InsidePanel({ state, onRetry, bindings, values, labelOf, activeParamId }: InsidePanelProps) {
  const { t } = useLanguage()
  const [layout, setLayout] = useState<InsideLayout>('canvas')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const content = state.status === 'ready' ? state.graph.content : null
  const doc = useMemo(() => (content === null ? null : readGraph(content)), [content])
  const highlighted = useMemo(
    () => (doc && activeParamId ? nodesDrivenBy(doc, bindings, activeParamId) : new Set<string>()),
    [doc, bindings, activeParamId],
  )
  const selected = doc?.nodes.find((n) => n.id === selectedId) ?? null

  return (
    <section className="flex h-full min-h-0 flex-col bg-background" aria-labelledby="inside-title" data-testid="inside-panel">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border px-3 py-2">
        <div className="min-w-0 flex-1">
          <h2 id="inside-title" className="text-sm font-semibold leading-5">{t('inside.title')}</h2>
          {state.status === 'ready' && doc && (
            <p className="text-xs text-muted-foreground" data-testid="inside-summary">
              {t(doc.nodes.length === 1 ? 'inside.node_count_one' : 'inside.node_count', { count: doc.nodes.length })}
              {' · '}
              {state.graph.role === 'twin' && state.graph.script
                ? t('inside.role_twin', { script: state.graph.script })
                : t('inside.role_source')}
              {' · '}
              {t('inside.read_only')}
            </p>
          )}
        </div>
        {doc && (
          <ToggleGroup
            type="single"
            value={layout}
            onValueChange={(v: string) => { if (v) setLayout(v as InsideLayout) }}
            className={RAIL}
            aria-label={t('inside.layout')}
          >
            <ToggleGroupItem value="canvas" className={RAIL_ITEM}>
              <Workflow aria-hidden="true" className="!size-3.5" /> {t('inside.layout_canvas')}
            </ToggleGroupItem>
            <ToggleGroupItem value="list" className={RAIL_ITEM}>
              <ListTree aria-hidden="true" className="!size-3.5" /> {t('inside.layout_list')}
            </ToggleGroupItem>
          </ToggleGroup>
        )}
      </header>

      {doc && (
        <p className="min-h-[28px] border-b border-border px-3 py-1.5 text-xs" role="status" aria-live="polite" data-testid="inside-link">
          {activeParamId ? (
            highlighted.size > 0
              ? t(highlighted.size === 1 ? 'inside.drives_one' : 'inside.drives', { label: labelOf(activeParamId), count: highlighted.size })
              : <span className="text-muted-foreground">{t('inside.drives_none', { label: labelOf(activeParamId) })}</span>
          ) : (
            <span className="text-muted-foreground">{t('inside.link_hint')}</span>
          )}
        </p>
      )}

      <div className="relative min-h-0 flex-1">
        {state.status === 'loading' || state.status === 'idle' ? (
          <div className="flex h-full items-center justify-center gap-2 text-xs text-muted-foreground" role="status">
            <Loader2 className="h-3.5 w-3.5 motion-safe:animate-spin" aria-hidden="true" />
            {t('inside.loading')}
          </div>
        ) : state.status === 'error' ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center" role="alert">
            <p className="max-w-[40ch] text-sm">{t('inside.error')}</p>
            <Button size="sm" variant="outline" className="h-10 gap-1.5" onClick={onRetry}>
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> {t('inside.retry')}
            </Button>
          </div>
        ) : !doc ? (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm" role="status">
            {t('inside.unreadable')}
          </div>
        ) : layout === 'canvas' ? (
          <GraphViewCanvas
            doc={doc}
            bindings={bindings}
            selectedId={selectedId}
            onSelect={setSelectedId}
            highlighted={highlighted}
          />
        ) : (
          <NodeList doc={doc} selectedId={selectedId} onSelect={setSelectedId} highlighted={highlighted} />
        )}
      </div>

      {doc && (
        <div className="max-h-[42%] shrink-0 overflow-y-auto border-t border-border" data-testid="inside-details">
          {selected ? (
            <NodeDetails
              doc={doc}
              node={selected}
              bindings={bindings}
              values={values}
              labelOf={labelOf}
              activeParamId={activeParamId}
              onSelect={setSelectedId}
            />
          ) : (
            <p className="px-3 py-2 text-xs text-muted-foreground">{t('inside.select_hint')}</p>
          )}
        </div>
      )}
    </section>
  )
}

interface NodeListProps {
  doc: GraphDoc
  selectedId: string | null
  onSelect: (id: string | null) => void
  highlighted: Set<string>
}

/** The same nodes as the canvas, in build order: the keyboard and screen-reader reading of the graph. */
function NodeList({ doc, selectedId, onSelect, highlighted }: NodeListProps) {
  const { t } = useLanguage()
  const order = topologicalOrder(doc.nodes) ?? doc.nodes.map((n) => n.id)
  const byId = new Map(doc.nodes.map((n) => [n.id, n]))
  const parts = partsByNode(doc)
  return (
    <ol className="h-full overflow-y-auto p-2" aria-label={t('inside.list_label')} data-testid="inside-node-list">
      {order.map((id, index) => {
        const node = byId.get(id)
        if (!node) return null
        const isSelected = id === selectedId
        const isDriven = highlighted.has(id)
        const produces = parts.get(id) ?? []
        return (
          <li key={id}>
            <button
              type="button"
              aria-pressed={isSelected}
              data-highlighted={isDriven ? 'true' : 'false'}
              onClick={() => onSelect(isSelected ? null : id)}
              className={[
                'flex min-h-[44px] w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-xs transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isSelected ? 'bg-accent text-accent-foreground' : 'hover:bg-muted',
                isDriven ? 'ring-2 ring-primary' : '',
              ].join(' ')}
            >
              <span className="w-5 shrink-0 text-right font-mono tabular-nums text-muted-foreground">{index + 1}</span>
              <span className="min-w-0 flex-1">
                <span className="font-mono font-semibold">{id}</span>
                <span className="ml-2 text-muted-foreground">{node.type}</span>
              </span>
              {produces.length > 0 && (
                <span className="shrink-0 text-muted-foreground">{t('inside.produces', { parts: produces.join(', ') })}</span>
              )}
            </button>
          </li>
        )
      })}
    </ol>
  )
}

interface NodeDetailsProps {
  doc: GraphDoc
  node: GraphNode
  bindings: BindingMap
  values: Record<string, unknown>
  labelOf: (parameterId: string) => string
  activeParamId: string | null
  onSelect: (id: string | null) => void
}

/** What drives each input of the selected node, read-only. */
function NodeDetails({ doc, node, bindings, values, labelOf, activeParamId, onSelect }: NodeDetailsProps) {
  const { t } = useLanguage()
  const sockets = socketRows(node)
  const rows = paramRows(doc, node, bindings, values)
  const produces = partsByNode(doc).get(node.id) ?? []
  const known = Boolean(NODE_TYPES[node.type])

  return (
    <div className="space-y-3 px-3 py-2.5 text-xs" data-testid="inside-node-details">
      <div className="flex flex-wrap items-baseline gap-x-2">
        <h3 className="font-mono text-sm font-semibold">{node.id}</h3>
        <span className="text-muted-foreground">{node.type}</span>
        {produces.length > 0 && <span className="ml-auto">{t('inside.produces', { parts: produces.join(', ') })}</span>}
      </div>
      {!known && <p className="text-muted-foreground">{t('inside.unknown_type')}</p>}

      {sockets.length > 0 && (
        <div>
          <h4 className="mb-1 font-medium text-muted-foreground">{t('inside.inputs')}</h4>
          <dl className="grid grid-cols-[minmax(0,auto)_1fr] gap-x-3 gap-y-1">
            {sockets.map((s) => (
              <div key={s.socket} className="contents">
                <dt className="font-mono">{s.socket} <span className="font-sans text-muted-foreground">{s.type}</span></dt>
                <dd>
                  {s.from ? (
                    <button
                      type="button"
                      className="rounded-sm font-mono underline decoration-border underline-offset-2 hover:decoration-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      onClick={() => onSelect(s.from)}
                    >
                      {t('inside.from_node', { node: s.from })}
                    </button>
                  ) : (
                    <span className="text-muted-foreground">{t('inside.unconnected')}</span>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {rows.length > 0 && (
        <div>
          <h4 className="mb-1 font-medium text-muted-foreground">{t('inside.parameters')}</h4>
          <dl className="grid grid-cols-[minmax(0,auto)_1fr] gap-x-3 gap-y-1">
            {rows.map((row) => (
              <ParamLine key={row.name} row={row} labelOf={labelOf} activeParamId={activeParamId} />
            ))}
          </dl>
        </div>
      )}
    </div>
  )
}

function ParamLine({ row, labelOf, activeParamId }: { row: ParamRow; labelOf: (id: string) => string; activeParamId: string | null }) {
  const { t } = useLanguage()
  const { source } = row
  const active = activeParamId !== null && (
    (source.kind === 'bound' && source.parameterId === activeParamId)
    || (source.kind === 'expression' && source.reads.includes(activeParamId))
  )
  return (
    <div className="contents" data-testid={`inside-param-${row.name}`} data-source={source.kind} data-active={active ? 'true' : 'false'}>
      <dt className={`font-mono ${active ? 'font-semibold' : ''}`}>{row.name}</dt>
      <dd className={`min-w-0 break-words ${active ? 'rounded-sm bg-accent px-1 text-accent-foreground' : ''}`}>
        {source.kind === 'bound' && (
          <>
            {t('inside.source_bound', { label: labelOf(source.parameterId) })}
            {source.value !== undefined && <span className="ml-1.5 font-mono tabular-nums">{formatValue(source.value)}</span>}
          </>
        )}
        {source.kind === 'expression' && (
          <>
            <span className="font-mono">{source.expr}</span>
            {source.reads.length > 0 && (
              <span className="ml-1.5 text-muted-foreground">
                {t('inside.source_reads', { labels: source.reads.map(labelOf).join(', ') })}
              </span>
            )}
          </>
        )}
        {source.kind === 'literal' && (
          <>
            <span className="font-mono tabular-nums">{formatValue(source.value)}</span>
            <span className="ml-1.5 text-muted-foreground">{t('inside.source_literal')}</span>
          </>
        )}
        {source.kind === 'default' && (
          <>
            <span className="font-mono tabular-nums">{formatValue(source.value)}</span>
            <span className="ml-1.5 text-muted-foreground">{t('inside.source_default')}</span>
          </>
        )}
      </dd>
    </div>
  )
}
