/**
 * Read-only reading of a graph document, for the public "Inside" view.
 *
 * Two questions the view asks of a graph that the editor never had to:
 *
 *   1. What drives each input of a node? A literal, a manifest parameter bound
 *      to it, or an expression (graph 1.1) reading parameters and derived values.
 *   2. Which nodes does a manifest parameter drive? Through a binding, or
 *      through an expression that reads it directly or via derived values.
 *      This is what links a slider to the boxes it moves.
 *
 * Pure functions over the same model the editor uses (`graphDocument.ts`); no
 * React, no I/O.
 */
import { NODE_TYPES, isExpressionValue } from './graphDocument'
import type { GraphDoc, GraphNode, ParamValue } from './graphDocument'
import { bindingKey } from './graphBindings'
import type { BindingMap } from './graphBindings'
import { expressionIdentifiers } from './graphExpressions'

export type ParamSource =
  | { kind: 'bound'; parameterId: string; value: ParamValue | undefined }
  | { kind: 'expression'; expr: string; reads: string[] }
  | { kind: 'literal'; value: ParamValue }
  | { kind: 'default'; value: unknown }

export interface ParamRow {
  name: string
  source: ParamSource
}

export interface SocketRow {
  socket: string
  type: string
  /** The node wired into this socket, or null when it is unconnected. */
  from: string | null
}

/** Parse a graph document's text for viewing. Never throws; null means unreadable. */
export function readGraph(content: string): GraphDoc | null {
  let parsed: unknown
  try {
    parsed = JSON.parse(content)
  } catch {
    return null
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return null
  const doc = parsed as GraphDoc
  if (!Array.isArray(doc.nodes)) return null
  if (!doc.nodes.every((n) => typeof n === 'object' && n !== null && typeof n.id === 'string' && typeof n.type === 'string')) {
    return null
  }
  if (typeof doc.outputs !== 'object' || doc.outputs === null || Array.isArray(doc.outputs)) doc.outputs = {}
  return doc
}

/** Every expression string inside a param value (a whole value, or coordinates in a list). */
function expressionsIn(value: unknown): string[] {
  if (isExpressionValue(value)) return [value.expr]
  if (Array.isArray(value)) return value.flatMap(expressionsIn)
  return []
}

/**
 * Manifest parameters each derived value reads, transitively. Derived values
 * are evaluated in list order and may only read earlier ones, so one pass in
 * order resolves the whole chain.
 */
function derivedReads(doc: GraphDoc): Map<string, Set<string>> {
  const declared = new Set(Object.keys(doc.parameters ?? {}))
  const reads = new Map<string, Set<string>>()
  for (const d of doc.derived ?? []) {
    if (!d || typeof d.id !== 'string' || typeof d.expr !== 'string') continue
    const out = new Set<string>()
    for (const ident of expressionIdentifiers(d.expr)) {
      if (declared.has(ident)) out.add(ident)
      for (const p of reads.get(ident) ?? []) out.add(p)
    }
    reads.set(d.id, out)
  }
  return reads
}

/** The manifest parameters an expression reads, directly or through derived values. */
function parametersRead(expr: string, doc: GraphDoc, derived: Map<string, Set<string>>): string[] {
  const declared = new Set(Object.keys(doc.parameters ?? {}))
  const out = new Set<string>()
  for (const ident of expressionIdentifiers(expr)) {
    if (declared.has(ident)) out.add(ident)
    for (const p of derived.get(ident) ?? []) out.add(p)
  }
  return [...out]
}

/** What drives each param of a node, in catalog order, then any extra params the node carries. */
export function paramRows(
  doc: GraphDoc,
  node: GraphNode,
  bindings: BindingMap,
  values: Record<string, unknown> = {},
): ParamRow[] {
  const spec = NODE_TYPES[node.type]
  const names = [...Object.keys(spec?.params ?? {})]
  for (const name of Object.keys(node.params ?? {})) if (!names.includes(name)) names.push(name)
  const derived = derivedReads(doc)

  return names.map((name) => {
    const key = bindingKey(node.id, name)
    const boundTo = Object.entries(bindings).find(([, targets]) => targets.includes(key))?.[0]
    if (boundTo) {
      return { name, source: { kind: 'bound', parameterId: boundTo, value: values[boundTo] as ParamValue | undefined } }
    }
    const value = node.params?.[name]
    if (value === undefined) return { name, source: { kind: 'default', value: spec?.params?.[name]?.default } }
    const exprs = expressionsIn(value)
    if (isExpressionValue(value)) {
      return { name, source: { kind: 'expression', expr: value.expr, reads: parametersRead(value.expr, doc, derived) } }
    }
    if (exprs.length > 0) {
      const reads = [...new Set(exprs.flatMap((e) => parametersRead(e, doc, derived)))]
      return { name, source: { kind: 'expression', expr: formatValue(value), reads } }
    }
    return { name, source: { kind: 'literal', value } }
  })
}

/** The node's input sockets and what is wired into each. */
export function socketRows(node: GraphNode): SocketRow[] {
  const spec = NODE_TYPES[node.type]
  return Object.entries(spec?.inputs ?? {}).map(([socket, type]) => ({
    socket,
    type,
    from: node.inputs?.[socket] ?? null,
  }))
}

/**
 * Ids of the nodes a manifest parameter drives: through a binding on one of
 * their params, or through an expression that reads it (directly or via a
 * derived value).
 */
export function nodesDrivenBy(doc: GraphDoc, bindings: BindingMap, parameterId: string): Set<string> {
  const driven = new Set<string>()
  for (const target of bindings[parameterId] ?? []) {
    const dot = target.indexOf('.')
    if (dot > 0) driven.add(target.slice(0, dot))
  }
  if (!(parameterId in (doc.parameters ?? {}))) return driven
  const derived = derivedReads(doc)
  for (const node of doc.nodes) {
    if (driven.has(node.id)) continue
    for (const value of Object.values(node.params ?? {})) {
      if (expressionsIn(value).some((e) => parametersRead(e, doc, derived).includes(parameterId))) {
        driven.add(node.id)
        break
      }
    }
  }
  return driven
}

/** A param value as one line of text: numbers as written, lists and objects as compact JSON. */
export function formatValue(value: unknown): string {
  if (value === undefined) return ''
  if (isExpressionValue(value)) return value.expr
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value, (_k, v) => (isExpressionValue(v) ? v.expr : v))
}

/** Part ids each node produces, keyed by node id. */
export function partsByNode(doc: GraphDoc): Map<string, string[]> {
  const out = new Map<string, string[]>()
  for (const [part, ref] of Object.entries(doc.outputs ?? {})) out.set(ref, [...(out.get(ref) ?? []), part])
  return out
}
