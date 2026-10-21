import { useState } from 'react'
import { ArrowDown, ArrowUp, X } from 'lucide-react'
import { useLanguage } from '../../../contexts/system/LanguageProvider'
import { LIMITS } from '../../../lib/graph/graphDocument'
import type { GraphDoc, GraphIssue } from '../../../lib/graph/graphDocument'
import {
  addDerived,
  checkExpression,
  moveDerived,
  needsMap,
  removeDerived,
  setDerivedExpr,
  setParameterMap,
  undeclareParameter,
} from '../../../lib/graph/graphExpressions'
import type { ManifestParameterLike } from '../../../lib/graph/graphExpressions'

interface GraphDeclarationsProps {
  doc: GraphDoc
  manifestParameters: ManifestParameterLike[]
  scope: Record<string, number | boolean>
  issues: GraphIssue[]
  onDocChange: (doc: GraphDoc) => void
}

const inputClass =
  'rounded border border-border bg-background px-1.5 py-0.5 text-[11px] font-mono min-h-[32px] md:min-h-0 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring'

/**
 * The option → number map of a select parameter. The numbers are the author's
 * to enter — the editor never guesses what "NEMA17" means as a number.
 */
function MapEditor({ id, options, map, onChange }: {
  id: string
  options: string[]
  map: Record<string, number>
  onChange: (map: Record<string, number> | null) => void
}) {
  const { t } = useLanguage()
  return (
    <div className="ml-3 mt-0.5 space-y-0.5" aria-label={t('graph.map_for', { id })}>
      {options.map((option) => (
        <label key={option} className="flex items-center gap-1.5">
          <span className="font-mono w-24 truncate">{option}</span>
          <span aria-hidden="true">→</span>
          <input
            type="number"
            step="any"
            className={`${inputClass} w-20`}
            aria-label={t('graph.map_value', { id, option })}
            value={map[option] ?? ''}
            onChange={(e) => {
              const next = { ...map }
              const parsed = Number(e.target.value)
              if (e.target.value.trim() === '' || !Number.isFinite(parsed)) delete next[option]
              else next[option] = parsed
              onChange(Object.keys(next).length > 0 ? next : null)
            }}
          />
        </label>
      ))}
    </div>
  )
}

/**
 * The graph's declarations (version 1.1): the manifest parameters its
 * expressions read, and its ordered derived values. Each derived value may
 * read declared parameters and the derived values above it, so the order is
 * part of the meaning and can be changed here.
 */
export default function GraphDeclarations({ doc, manifestParameters, scope, issues, onDocChange }: GraphDeclarationsProps) {
  const { t } = useLanguage()
  const [newId, setNewId] = useState('')
  const [newExpr, setNewExpr] = useState('')
  const [addError, setAddError] = useState<string | null>(null)
  const declared = doc.parameters ?? {}
  const derived = doc.derived ?? []
  const byId = new Map(manifestParameters.map((p) => [p.id, p]))

  const add = () => {
    try {
      onDocChange(addDerived(doc, newId.trim(), newExpr.trim()))
      setNewId('')
      setNewExpr('')
      setAddError(null)
    } catch (err) {
      setAddError((err as Error).message)
    }
  }

  return (
    <div className="text-xs px-3 py-1.5 space-y-2" data-testid="graph-declarations">
      <section aria-label={t('graph.declared_parameters')}>
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">{t('graph.declared_parameters')}</div>
        {Object.keys(declared).length === 0 && (
          <div className="text-muted-foreground text-[11px]">{t('graph.no_declared_parameters')}</div>
        )}
        {Object.entries(declared).map(([id, decl]) => {
          const manifestParam = byId.get(id)
          const options = (manifestParam?.options ?? []).map((o) => String(o.value))
          const showMap = manifestParam ? needsMap(manifestParam) : !!decl.map
          return (
            <div key={id} className="py-0.5" data-testid={`graph-declared-${id}`}>
              <div className="flex items-center gap-1.5">
                <span className="font-mono">{id}</span>
                <span className="text-muted-foreground">= {id in scope ? String(scope[id]) : '—'}</span>
                <button
                  type="button"
                  className="ml-auto text-muted-foreground hover:text-destructive"
                  onClick={() => onDocChange(undeclareParameter(doc, id))}
                  aria-label={t('graph.undeclare', { id })}
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
              {!manifestParam && (
                <div className="text-[10px] text-amber-600 dark:text-amber-400" role="status">
                  {t('graph.declared_missing_from_manifest', { id })}
                </div>
              )}
              {showMap && options.length > LIMITS.max_map_entries && (
                <div className="text-[10px] text-destructive">{t('graph.limit_reached', { limit: LIMITS.max_map_entries })}</div>
              )}
              {showMap && !(id in scope) && (
                <div className="text-[10px] text-destructive">{t('graph.map_required', { id })}</div>
              )}
              {showMap && (
                <MapEditor
                  id={id}
                  options={options.length > 0 ? options : Object.keys(decl.map ?? {})}
                  map={decl.map ?? {}}
                  onChange={(map) => onDocChange(setParameterMap(doc, id, map))}
                />
              )}
            </div>
          )
        })}
      </section>

      <section aria-label={t('graph.derived_values')}>
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">{t('graph.derived_values')}</div>
        <ol className="space-y-1">
          {derived.map((entry, index) => {
            const earlier = derived.slice(0, index).map((d) => d.id)
            const check = checkExpression(entry.expr, declared, scope, earlier)
            const issue = issues.find((i) => i.derivedId === entry.id)
            return (
              <li key={entry.id} className="space-y-0.5" data-testid={`graph-derived-${entry.id}`}>
                <div className="flex items-center gap-1">
                  <span className="font-mono w-20 truncate">{entry.id}</span>
                  <input
                    className={`${inputClass} flex-1`}
                    aria-label={t('graph.derived_expr', { id: entry.id })}
                    value={entry.expr}
                    spellCheck={false}
                    onChange={(e) => onDocChange(setDerivedExpr(doc, entry.id, e.target.value))}
                  />
                  <button type="button" aria-label={t('graph.move_up', { id: entry.id })} disabled={index === 0}
                    className="disabled:opacity-30" onClick={() => onDocChange(moveDerived(doc, entry.id, -1))}>
                    <ArrowUp className="h-3 w-3" />
                  </button>
                  <button type="button" aria-label={t('graph.move_down', { id: entry.id })} disabled={index === derived.length - 1}
                    className="disabled:opacity-30" onClick={() => onDocChange(moveDerived(doc, entry.id, 1))}>
                    <ArrowDown className="h-3 w-3" />
                  </button>
                  <button type="button" aria-label={t('graph.remove_derived', { id: entry.id })}
                    className="text-muted-foreground hover:text-destructive" onClick={() => onDocChange(removeDerived(doc, entry.id))}>
                    <X className="h-3 w-3" />
                  </button>
                </div>
                {issue || check.error ? (
                  <div className="text-[10px] text-destructive">{issue?.message ?? check.error}</div>
                ) : (
                  <div className="text-[10px] text-muted-foreground">= {String(check.value)}</div>
                )}
              </li>
            )
          })}
        </ol>
        <div className="flex items-center gap-1 mt-1">
          <input className={`${inputClass} w-20`} aria-label={t('graph.derived_new_id')} placeholder="seat_r"
            value={newId} onChange={(e) => setNewId(e.target.value)} />
          <input className={`${inputClass} flex-1`} aria-label={t('graph.derived_new_expr')} placeholder="b_od / 2"
            value={newExpr} onChange={(e) => setNewExpr(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') add() }} />
          <button type="button" className="rounded border border-border px-1.5 py-0.5 hover:bg-muted disabled:opacity-50 min-h-[32px] md:min-h-0"
            disabled={!newId.trim() || !newExpr.trim() || derived.length >= LIMITS.max_derived} onClick={add}>
            {t('graph.add_derived')}
          </button>
        </div>
        {addError && <div className="text-[10px] text-destructive">{addError}</div>}
        {derived.length >= LIMITS.max_derived && (
          <div className="text-[10px] text-muted-foreground">{t('graph.limit_reached', { limit: LIMITS.max_derived })}</div>
        )}
      </section>
    </div>
  )
}
