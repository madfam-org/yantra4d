/**
 * Manifest bindings for graph node params.
 *
 * A graph node param is driven at render time by a manifest parameter whose
 * `binding` names it ("nodeId.param", or a list of them). The binding lives in
 * the manifest, not in the graph, so the editor keeps a working copy of the
 * map, lets the author change it, and saves the difference through
 * `PUT /api/projects/<slug>/manifest/bindings` — a fork-only route the server
 * validates against the graph on disk.
 */
import type { ManifestParameterLike } from './graphExpressions'
import { isExpressionValue } from './graphDocument'
import type { GraphDoc, GraphIssue } from './graphDocument'

/** Manifest parameter id → the node params it drives ("nodeId.param"). */
export type BindingMap = Record<string, string[]>

export function bindingKey(nodeId: string, param: string): string {
  return `${nodeId}.${param}`
}

/** The binding map a manifest declares today. */
export function bindingsFromManifest(parameters: ManifestParameterLike[] | undefined): BindingMap {
  const map: BindingMap = {}
  for (const p of parameters ?? []) {
    if (!p?.id || !p.binding) continue
    const targets = Array.isArray(p.binding) ? p.binding : [p.binding]
    const valid = targets.filter((t): t is string => typeof t === 'string')
    if (valid.length > 0) map[p.id] = valid
  }
  return map
}

/** Which manifest parameter drives `nodeId.param`, if any. */
export function boundParameter(map: BindingMap, nodeId: string, param: string): string | null {
  const key = bindingKey(nodeId, param)
  for (const [pid, targets] of Object.entries(map)) {
    if (targets.includes(key)) return pid
  }
  return null
}

/** Drive `nodeId.param` from `pid` (or from nothing, with null). One driver per node param. */
export function setBinding(map: BindingMap, nodeId: string, param: string, pid: string | null): BindingMap {
  const key = bindingKey(nodeId, param)
  const next: BindingMap = {}
  for (const [id, targets] of Object.entries(map)) {
    const kept = targets.filter((t) => t !== key)
    if (kept.length > 0) next[id] = kept
  }
  if (pid) next[pid] = [...(next[pid] ?? []), key]
  return next
}

/** Drop every target on a node that no longer exists. */
export function dropNodeBindings(map: BindingMap, nodeId: string): BindingMap {
  const next: BindingMap = {}
  for (const [id, targets] of Object.entries(map)) {
    const kept = targets.filter((t) => !t.startsWith(`${nodeId}.`))
    if (kept.length > 0) next[id] = kept
  }
  return next
}

/**
 * The request body that turns `before` into `after`: changed parameters get
 * their new binding (a string when there is one target, so a hand-written
 * manifest keeps its shape), removed ones get null. Empty when nothing changed.
 */
export function bindingChanges(before: BindingMap, after: BindingMap): Record<string, string | string[] | null> {
  const changes: Record<string, string | string[] | null> = {}
  const ids = new Set([...Object.keys(before), ...Object.keys(after)])
  for (const id of ids) {
    const a = before[id] ?? []
    const b = after[id] ?? []
    if (a.length === b.length && a.every((t, i) => t === b[i])) continue
    changes[id] = b.length === 0 ? null : b.length === 1 ? b[0] : b
  }
  return changes
}

/**
 * Manifest parameters that can drive a numeric node param: sliders, and
 * selects whose every option is a number. The engine reads the value with
 * `float()`/`int()`, so text, checkboxes and named options cannot bind.
 */
export function bindableParameters(parameters: ManifestParameterLike[] | undefined): ManifestParameterLike[] {
  return (parameters ?? []).filter((p) => {
    if (p.type === 'slider') return true
    if (p.type !== 'select') return false
    const values = (p.options ?? []).map((o) => o.value)
    return values.length > 0 && values.every((v) => typeof v === 'number' || (typeof v === 'string' && v.trim() !== '' && Number.isFinite(Number(v))))
  })
}

/**
 * A node param takes an expression or a manifest binding, never both — the
 * engine refuses the pair. Returns one issue per such param.
 */
export function bindingConflicts(doc: GraphDoc, map: BindingMap): GraphIssue[] {
  const issues: GraphIssue[] = []
  for (const [pid, targets] of Object.entries(map)) {
    for (const target of targets) {
      const [nodeId, param] = target.split('.')
      const node = doc.nodes.find((n) => n.id === nodeId)
      if (node && isExpressionValue(node.params?.[param])) {
        issues.push({
          message: `"${param}" is bound to manifest parameter "${pid}" and also carries an expression; use one or the other.`,
          nodeId,
          param,
        })
      }
    }
  }
  return issues
}
