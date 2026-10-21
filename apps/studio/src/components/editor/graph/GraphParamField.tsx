import { useState } from 'react'
import { useLanguage } from '../../../contexts/system/LanguageProvider'
import { AXES, LIMITS, PLANES, isExpressionValue, literalProblem, wholeValueExpressible } from '../../../lib/graph/graphDocument'
import type { GraphIssue, ParamSpec, ParamValue } from '../../../lib/graph/graphDocument'
import type { ExpressionCheck, ManifestParameterLike } from '../../../lib/graph/graphExpressions'

export type ParamMode = 'literal' | 'bound' | 'expr'

export interface GraphParamFieldProps {
  nodeId: string
  name: string
  spec: ParamSpec
  /** Stored value, or undefined when the node uses the catalog default. */
  value: ParamValue | undefined
  boundTo: string | null
  bindable: ManifestParameterLike[]
  /** Why binding is unavailable here (not a fork, …), or null when it is. */
  bindBlockedReason: string | null
  /** Evaluate an expression against the graph's declarations. */
  checkExpression: (expr: string) => ExpressionCheck
  /** Manifest parameter ids, to offer declaring an undeclared one. */
  manifestIds: string[]
  issue?: GraphIssue
  onLiteral: (value: ParamValue) => void
  onReset: () => void
  onBind: (pid: string | null) => void
  onExpression: (expr: string) => void
  onDeclare: (id: string) => void
}

const fieldClass =
  'w-full rounded border border-border bg-background px-1.5 py-0.5 text-[11px] font-mono min-h-[32px] md:min-h-0 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring'

function display(value: unknown): string {
  if (value === undefined || value === null) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

/**
 * A text box that keeps what the author is typing ("-", "1.") while the
 * stored value only changes once the text parses. It re-syncs when the stored
 * value changes from outside (undo, text view, reset) — adjusted during render,
 * not in an effect.
 */
function useDraft(value: unknown) {
  const [draft, setDraft] = useState(display(value))
  const [seen, setSeen] = useState(value)
  if (seen !== value) {
    setSeen(value)
    setDraft(display(value))
  }
  return [draft, setDraft] as const
}

function LiteralInput({ nodeId, name, spec, value, onLiteral }: {
  nodeId: string
  name: string
  spec: ParamSpec
  value: unknown
  onLiteral: (value: ParamValue) => void
}) {
  const { t } = useLanguage()
  const [draft, setDraft] = useDraft(value)
  const [jsonError, setJsonError] = useState<string | null>(null)
  const id = `graph-param-${nodeId}-${name}`
  const label = t('graph.param_value', { name })

  if (spec.kind === 'condition') {
    return (
      <select id={id} aria-label={label} className={fieldClass} value={String(value === true)}
        onChange={(e) => onLiteral(e.target.value === 'true')}>
        <option value="true">true</option>
        <option value="false">false</option>
      </select>
    )
  }

  if (spec.kind === 'points') {
    return <PointsInput nodeId={nodeId} name={name} spec={spec} value={value} onLiteral={onLiteral} />
  }

  if (spec.kind === 'plane' || spec.kind === 'axis') {
    const choices = spec.kind === 'plane' ? PLANES : AXES
    return (
      <select id={id} aria-label={label} className={fieldClass} value={display(value)} onChange={(e) => onLiteral(e.target.value)}>
        {choices.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
    )
  }

  if (spec.kind === 'float' || spec.kind === 'count') {
    return (
      <input
        id={id}
        aria-label={label}
        type="number"
        inputMode="decimal"
        step={spec.kind === 'count' ? 1 : 'any'}
        className={fieldClass}
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value)
          const parsed = Number(e.target.value)
          if (e.target.value.trim() !== '' && Number.isFinite(parsed)) {
            onLiteral(spec.kind === 'count' ? Math.trunc(parsed) : parsed)
          }
        }}
      />
    )
  }

  if (spec.kind === 'selector') {
    return (
      <input
        id={id}
        aria-label={label}
        type="text"
        className={fieldClass}
        value={draft}
        placeholder={t('graph.selector_all_edges')}
        onChange={(e) => { setDraft(e.target.value); onLiteral(e.target.value) }}
      />
    )
  }

  // A kind this editor does not know yet (the engine grows faster than the UI):
  // edit it as JSON, committed only when it parses.
  return (
    <div>
      <textarea
        id={id}
        aria-label={label}
        className={`${fieldClass} min-h-[48px]`}
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value)
          try {
            onLiteral(JSON.parse(e.target.value) as ParamValue)
            setJsonError(null)
          } catch (err) {
            setJsonError((err as Error).message)
          }
        }}
      />
      {jsonError && <div className="text-[10px] text-destructive">{t('graph.json_invalid')}</div>}
    </div>
  )
}

type Coordinate = number | { expr: string }

function coordText(c: unknown): string {
  return isExpressionValue(c) ? c.expr : display(c)
}

/**
 * A polyline's points, one row per [x, y]. A coordinate that reads as a number
 * is a literal; anything else is an expression — offered only when the catalog
 * marks the points param expressible, which is how the engine reads it too.
 */
function PointsInput({ nodeId, name, spec, value, onLiteral }: {
  nodeId: string
  name: string
  spec: ParamSpec
  value: unknown
  onLiteral: (value: ParamValue) => void
}) {
  const { t } = useLanguage()
  const points: Coordinate[][] = Array.isArray(value)
    ? value.map((p) => (Array.isArray(p) ? [p[0] as Coordinate, p[1] as Coordinate] : [0, 0]))
    : []
  const max = LIMITS.max_polyline_points
  const commit = (next: Coordinate[][]) => onLiteral(next as unknown as ParamValue)
  const parse = (text: string): Coordinate | null => {
    const n = Number(text)
    if (text.trim() !== '' && Number.isFinite(n)) return n
    return spec.expr === true && text.trim() !== '' ? { expr: text } : null
  }

  return (
    <div className="space-y-0.5" data-testid={`graph-points-${nodeId}-${name}`}>
      {points.map((point, i) => (
        <div key={i} className="flex items-center gap-1">
          <span className="w-5 text-[10px] text-muted-foreground">{i + 1}</span>
          {[0, 1].map((axis) => (
            <CoordinateInput
              key={axis}
              label={t('graph.point_coordinate', { n: i + 1, axis: axis === 0 ? 'x' : 'y' })}
              value={coordText(point[axis])}
              onCommit={(text) => {
                const parsed = parse(text)
                if (parsed === null) return
                commit(points.map((p, j) => (j === i ? (axis === 0 ? [parsed, p[1]] : [p[0], parsed]) : p)))
              }}
            />
          ))}
          <button type="button" className="text-[10px] text-muted-foreground disabled:opacity-30"
            aria-label={t('graph.point_remove', { n: i + 1 })} disabled={points.length <= 3}
            onClick={() => commit(points.filter((_, j) => j !== i))}>×</button>
        </div>
      ))}
      <button type="button" className="text-[10px] underline disabled:opacity-30" disabled={points.length >= max}
        onClick={() => commit([...points, [0, 0]])}>
        {t('graph.point_add')}
      </button>
    </div>
  )
}

function CoordinateInput({ label, value, onCommit }: { label: string; value: string; onCommit: (text: string) => void }) {
  const [draft, setDraft] = useDraft(value)
  return (
    <input
      aria-label={label}
      type="text"
      spellCheck={false}
      className={`${fieldClass} flex-1`}
      value={draft}
      onChange={(e) => { setDraft(e.target.value); onCommit(e.target.value) }}
    />
  )
}

function ExpressionInput({ nodeId, name, value, checkExpression, manifestIds, onExpression, onDeclare }: {
  nodeId: string
  name: string
  value: string
  checkExpression: (expr: string) => ExpressionCheck
  manifestIds: string[]
  onExpression: (expr: string) => void
  onDeclare: (id: string) => void
}) {
  const { t } = useLanguage()
  const [draft, setDraft] = useDraft(value)
  const check = checkExpression(draft)
  const declarable = check.undeclared.filter((id) => manifestIds.includes(id))
  const unknown = check.undeclared.filter((id) => !manifestIds.includes(id))

  return (
    <div className="space-y-0.5">
      <input
        aria-label={t('graph.param_expression', { name })}
        data-testid={`graph-expr-${nodeId}-${name}`}
        type="text"
        spellCheck={false}
        className={fieldClass}
        value={draft}
        placeholder="width / 2 - wall"
        onChange={(e) => { setDraft(e.target.value); onExpression(e.target.value) }}
      />
      {check.error ? (
        <div className="text-[10px] text-destructive">{check.error}</div>
      ) : (
        <div className="text-[10px] text-muted-foreground">= {String(check.value)}</div>
      )}
      {declarable.map((id) => (
        <button key={id} type="button" className="mr-1 text-[10px] underline" onClick={() => onDeclare(id)}>
          {t('graph.declare_parameter', { id })}
        </button>
      ))}
      {unknown.length > 0 && (
        <div className="text-[10px] text-destructive">{t('graph.not_a_manifest_parameter', { ids: unknown.join(', ') })}</div>
      )}
    </div>
  )
}

/** One node param: a literal, a manifest binding, or (when the catalog allows) an expression. */
export default function GraphParamField(props: GraphParamFieldProps) {
  const { t } = useLanguage()
  const { nodeId, name, spec, value, boundTo, bindable, bindBlockedReason, issue } = props
  const effective = value === undefined ? spec.default : value
  const mode: ParamMode = isExpressionValue(value) ? 'expr' : boundTo ? 'bound' : 'literal'
  const canExpress = wholeValueExpressible(spec)
  const canBind = spec.bindable

  const switchMode = (next: ParamMode) => {
    if (next === mode) return
    if (mode === 'bound') props.onBind(null)
    if (next === 'literal') {
      if (isExpressionValue(value)) {
        const check = props.checkExpression(value.expr)
        if (check.value !== undefined && literalProblem(spec.kind, check.value) === null) props.onLiteral(check.value)
        else props.onReset()
      }
    } else if (next === 'expr') {
      props.onExpression(display(isExpressionValue(effective) ? effective.expr : effective))
    } else if (next === 'bound') {
      if (isExpressionValue(value)) props.onReset()
      const first = bindable[0]?.id ?? null
      if (first) props.onBind(first)
    }
  }

  const literalHint = mode === 'literal' && !isExpressionValue(effective) ? literalProblem(spec.kind, effective) : null

  return (
    <div className="py-1 border-b border-border/50 last:border-b-0" data-testid={`graph-param-row-${nodeId}-${name}`}>
      <div className="flex items-center gap-1.5 mb-0.5">
        <span className={`font-mono text-[11px] ${issue ? 'text-destructive font-semibold' : ''}`}>{name}</span>
        <span className="text-[10px] text-muted-foreground">{spec.kind}</span>
        {(canBind || canExpress) && (
          <select
            aria-label={t('graph.param_mode', { name })}
            className="ml-auto rounded border border-border bg-background px-1 text-[10px] min-h-[28px] md:min-h-0"
            value={mode}
            onChange={(e) => switchMode(e.target.value as ParamMode)}
          >
            <option value="literal">{t('graph.mode_literal')}</option>
            {canBind && (
              <option value="bound" disabled={!!bindBlockedReason || bindable.length === 0}>
                {t('graph.mode_bound')}
              </option>
            )}
            {canExpress && <option value="expr">{t('graph.mode_expr')}</option>}
          </select>
        )}
        {value !== undefined && mode === 'literal' && (
          <button type="button" className="text-[10px] underline text-muted-foreground" onClick={props.onReset}>
            {t('graph.reset_default')}
          </button>
        )}
      </div>

      {mode === 'literal' && (
        <LiteralInput nodeId={nodeId} name={name} spec={spec} value={effective} onLiteral={props.onLiteral} />
      )}

      {mode === 'bound' && (
        <div className="space-y-0.5">
          <select
            aria-label={t('graph.param_binding', { name })}
            className={fieldClass}
            value={boundTo ?? ''}
            disabled={!!bindBlockedReason}
            onChange={(e) => props.onBind(e.target.value || null)}
          >
            {bindable.map((p) => <option key={p.id} value={p.id}>{p.id}</option>)}
          </select>
          <div className="text-[10px] text-muted-foreground">
            {t('graph.bound_default', { value: display(effective) })}
          </div>
        </div>
      )}

      {mode === 'expr' && isExpressionValue(value) && (
        <ExpressionInput
          nodeId={nodeId}
          name={name}
          value={value.expr}
          checkExpression={props.checkExpression}
          manifestIds={props.manifestIds}
          onExpression={props.onExpression}
          onDeclare={props.onDeclare}
        />
      )}

      {issue && <div className="text-[10px] text-destructive" role="alert">{issue.message}</div>}
      {!issue && literalHint && <div className="text-[10px] text-destructive">{literalHint}</div>}
    </div>
  )
}
