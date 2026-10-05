/**
 * Client-side model for graph cartridge documents (.graph.json).
 *
 * Ported from sim4d's engine-core GraphManager (MPL-2.0, madfam-org/sim4d
 * @8780dd85) and relicensed into this AGPL-3.0 repo — MADFAM holds the whole
 * copyright. Two things were deliberately not carried over:
 *
 *   1. Sim4d stored connectivity twice — an `edges[]` array *and* per-node
 *      `inputs` — and kept them in sync by hand on every mutation. Yantra4D's
 *      format stores connectivity once, in `inputs`, and the UI derives edges
 *      from it. One representation cannot disagree with itself.
 *   2. Its `fromJSON` was a bare `JSON.parse` with no validation, so a
 *      malformed document failed later and elsewhere. Here, parsing validates
 *      against the same rules the server transpiler enforces, and says why.
 *
 * The server remains the authority: this model exists so the editor can reject
 * a bad edit immediately instead of round-tripping to a render that will fail.
 */
import catalog from '../../config/graph-node-catalog.json'
import { buildScope, checkExpression, expressionIdentifiers, requiredVersion, versionAtLeast11 } from './graphExpressions'
import { formatLike } from './graphFormat'

/**
 * Socket types come from the catalog, not from this file: today `solid` and
 * `profile`, and whatever the engine adds next. Connections are checked by
 * equality, so a new socket type needs no change here.
 */
export type SocketType = string
/** `float`, `count`, `selector`, `axis`, `plane` today; unknown kinds are edited as JSON. */
export type ParamKind = string

export interface ParamSpec {
  kind: ParamKind
  default: unknown
  bindable: boolean
  /** G-EXPR: the param accepts an `{"expr": "..."}` value. Absent means no. */
  expr?: boolean
}

export interface NodeTypeSpec {
  output: SocketType
  inputs: Record<string, SocketType>
  params: Record<string, ParamSpec>
}

/** A param value driven by a safeFormula expression (G-EXPR). */
export interface ExpressionValue {
  expr: string
}

export type ParamValue = number | string | boolean | ExpressionValue | unknown[] | Record<string, unknown>

export interface NodePosition {
  x: number
  y: number
}

export interface GraphNode {
  id: string
  type: string
  params?: Record<string, ParamValue>
  inputs?: Record<string, string>
  meta?: Record<string, unknown>
}

/** A manifest parameter an expression may read (graph version 1.1). */
export interface DeclaredParameter {
  default: number | string | boolean
  /** String option → number, for select parameters whose options are not numeric. */
  map?: Record<string, number>
}

/** A named intermediate value (graph version 1.1), evaluated in list order. */
export interface DerivedValue {
  id: string
  expr: string
}

export interface GraphDoc {
  version: string
  units?: string
  meta?: Record<string, unknown>
  parameters?: Record<string, DeclaredParameter>
  derived?: DerivedValue[]
  nodes: GraphNode[]
  outputs: Record<string, string>
}

const rawCatalog = catalog as unknown as {
  nodes: Record<string, NodeTypeSpec>
  limits: {
    max_nodes: number
    max_outputs: number
    max_pattern_count: number
    max_parameters?: number
    max_derived?: number
    max_map_entries?: number
    max_polyline_points?: number
    max_revolve_extent_mm?: number
  }
  planes: string[]
  expression?: { dialect?: string; max_length?: number; max_tokens?: number }
}

export const NODE_TYPES = rawCatalog.nodes
/**
 * The engine's limits as the catalog states them. The Wave D limits fall back to
 * the engine's own constants (graph_engine.py MAX_GRAPH_PARAMETERS, MAX_DERIVED,
 * MAX_MAP_ENTRIES, MAX_POLYLINE_POINTS, MAX_REVOLVE_EXTENT) for a catalog
 * generated before they were exported.
 */
export const LIMITS = {
  max_parameters: 128,
  max_derived: 256,
  max_map_entries: 64,
  max_polyline_points: 256,
  max_revolve_extent_mm: 1000,
  ...rawCatalog.limits,
} as Required<typeof rawCatalog.limits>
export const PLANES = rawCatalog.planes
export const AXES = ['x', 'y', 'z']
/** The two in-plane axes of each workplane — a revolve axis must be one of them. */
export const PLANE_AXES: Record<string, string[]> = { XY: ['x', 'y'], XZ: ['x', 'z'], YZ: ['y', 'z'] }

/**
 * Kinds whose whole value may be `{"expr": ...}` when the catalog says `expr`.
 * A `points` value is always a list; its catalog `expr` means each coordinate
 * may be an expression, never the list itself.
 */
export function wholeValueExpressible(spec: ParamSpec | undefined): boolean {
  return spec?.expr === true && spec.kind !== 'points'
}
/** Expression limits from the catalog when it declares them, else safeFormula's own. */
export const EXPRESSION_LIMITS = {
  max_length: rawCatalog.expression?.max_length ?? 256,
  max_tokens: rawCatalog.expression?.max_tokens ?? 128,
}

const ID_RE = /^[A-Za-z][A-Za-z0-9_]*$/
const VERSION_RE = /^1\.\d+(\.\d+)?$/

/**
 * A validation problem, addressed to whoever is editing the graph. `socket`,
 * `param` and `derivedId` say where on the node it is, so the editor can put
 * the marker on the exact row.
 */
export interface GraphIssue {
  message: string
  nodeId?: string
  socket?: string
  param?: string
  derivedId?: string
}

export function isExpressionValue(value: unknown): value is ExpressionValue {
  return (
    typeof value === 'object' && value !== null && !Array.isArray(value) &&
    Object.keys(value).length === 1 && typeof (value as ExpressionValue).expr === 'string'
  )
}

/** The catalog spec of one param, or undefined. */
export function paramSpec(type: string, name: string): ParamSpec | undefined {
  return NODE_TYPES[type]?.params[name]
}

/** Whether the catalog lets this param take an expression. */
export function isExpressible(type: string, name: string): boolean {
  return wholeValueExpressible(paramSpec(type, name))
}

export function nodeTypeNames(): string[] {
  return Object.keys(NODE_TYPES).sort()
}

/** Node types grouped for a palette: producers of profiles vs solids. */
export function nodeTypesByOutput(output: SocketType): string[] {
  return nodeTypeNames().filter((t) => NODE_TYPES[t].output === output)
}

export function emptyGraph(): GraphDoc {
  return { version: '1.0.0', units: 'mm', nodes: [], outputs: {} }
}

/** Default params for a node type, straight from the server's own defaults. */
export function defaultParams(type: string): Record<string, ParamValue> {
  const spec = NODE_TYPES[type]
  if (!spec) return {}
  const params: Record<string, ParamValue> = {}
  for (const [name, def] of Object.entries(spec.params)) params[name] = structuredCloneValue(def.default) as ParamValue
  return params
}

function structuredCloneValue(value: unknown): unknown {
  return typeof value === 'object' && value !== null ? JSON.parse(JSON.stringify(value)) : value
}

/**
 * Check one literal value against its param kind — the same checks the
 * server's `_literal` makes before it emits a number. Returns why it is
 * wrong, or null. Unknown kinds are the engine's business, not ours.
 */
export function literalProblem(kind: ParamKind, value: unknown): string | null {
  switch (kind) {
    case 'float':
      if (typeof value !== 'number' || !Number.isFinite(value)) return 'needs a finite number'
      return null
    case 'count':
      if (typeof value !== 'number' || !Number.isInteger(value)) return 'needs a whole number'
      if (value < 1 || value > LIMITS.max_pattern_count) return `must be between 1 and ${LIMITS.max_pattern_count}`
      return null
    case 'selector':
      if (typeof value !== 'string') return 'needs an edge selector string'
      if (value.length > 120) return 'selector is longer than 120 characters'
      return null
    case 'axis':
      return AXES.includes(value as string) ? null : `must be one of ${AXES.join(', ')}`
    case 'plane':
      return PLANES.includes(value as string) ? null : `must be one of ${PLANES.join(', ')}`
    case 'condition':
      return typeof value === 'boolean' ? null : 'needs true or false (or an expression)'
    case 'points': {
      const max = LIMITS.max_polyline_points
      if (!Array.isArray(value) || value.length < 3 || value.length > max) return `needs 3 to ${max} [x, y] points`
      for (const [i, point] of value.entries()) {
        if (!Array.isArray(point) || point.length !== 2) return `point ${i + 1} must be an [x, y] pair`
        for (const coord of point) {
          if (isExpressionValue(coord)) continue
          if (typeof coord !== 'number' || !Number.isFinite(coord)) return `point ${i + 1} needs finite numbers`
        }
      }
      return null
    }
    default:
      return null
  }
}

/**
 * Validate a document against the rules the server transpiler enforces.
 * Returns every problem found rather than throwing on the first, so an editor
 * can show them all at once.
 */
export function validateGraph(doc: unknown): GraphIssue[] {
  const issues: GraphIssue[] = []
  const push = (message: string, nodeId?: string) => issues.push({ message, nodeId })

  if (typeof doc !== 'object' || doc === null || Array.isArray(doc)) {
    return [{ message: 'Document must be a JSON object.' }]
  }
  const g = doc as Partial<GraphDoc>

  if (typeof g.version !== 'string' || !VERSION_RE.test(g.version)) {
    push(`Version must look like 1.x (got ${JSON.stringify(g.version ?? null)}).`)
  }
  if (g.units !== undefined && g.units !== 'mm') {
    push(`Only millimetre units are supported (got ${JSON.stringify(g.units)}).`)
  }
  if (!Array.isArray(g.nodes) || g.nodes.length === 0) {
    return [...issues, { message: 'A graph needs at least one node.' }]
  }
  if (g.nodes.length > LIMITS.max_nodes) {
    push(`Too many nodes: ${g.nodes.length} (limit ${LIMITS.max_nodes}).`)
  }

  const byId = new Map<string, GraphNode>()
  for (const node of g.nodes) {
    if (typeof node?.id !== 'string' || !ID_RE.test(node.id)) {
      push(`Node id ${JSON.stringify(node?.id ?? null)} must start with a letter and use only letters, digits and underscores.`)
      continue
    }
    if (byId.has(node.id)) {
      push(`Duplicate node id "${node.id}".`, node.id)
      continue
    }
    const spec = NODE_TYPES[node.type]
    if (!spec) {
      push(`Unknown node type ${JSON.stringify(node.type)}.`, node.id)
      continue
    }
    for (const name of Object.keys(node.params ?? {})) {
      if (!(name in spec.params)) issues.push({ message: `"${node.type}" has no parameter "${name}".`, nodeId: node.id, param: name })
    }
    const sockets = Object.keys(spec.inputs)
    const given = Object.keys(node.inputs ?? {})
    for (const socket of sockets) {
      if (!given.includes(socket)) issues.push({ message: `Missing input "${socket}".`, nodeId: node.id, socket })
    }
    for (const socket of given) {
      if (!sockets.includes(socket)) issues.push({ message: `"${node.type}" has no input "${socket}".`, nodeId: node.id, socket })
    }
    for (const [name, value] of Object.entries(node.params ?? {})) {
      const def = spec.params[name]
      if (!def) continue
      if (isExpressionValue(value)) {
        if (!wholeValueExpressible(def)) {
          const where = def.kind === 'points' && def.expr === true ? ' as a whole — put expressions on its coordinates' : ''
          issues.push({ message: `"${name}" does not accept an expression${where}.`, nodeId: node.id, param: name })
        }
        continue
      }
      if (def.kind === 'points' && def.expr !== true && Array.isArray(value) &&
        value.some((p) => Array.isArray(p) && p.some(isExpressionValue))) {
        issues.push({ message: `"${name}" does not accept expressions in its coordinates.`, nodeId: node.id, param: name })
        continue
      }
      const problem = literalProblem(def.kind, value)
      if (problem) issues.push({ message: `"${name}" ${problem}.`, nodeId: node.id, param: name })
    }
    byId.set(node.id, node)
  }

  // Reference targets and socket types (needs every id known first).
  const profileConsumers = new Map<string, string>()
  for (const node of byId.values()) {
    const spec = NODE_TYPES[node.type]
    for (const [socket, ref] of Object.entries(node.inputs ?? {})) {
      if (!spec?.inputs[socket]) continue
      if (ref === node.id) {
        issues.push({ message: `Input "${socket}" connects the node to itself.`, nodeId: node.id, socket })
        continue
      }
      const source = byId.get(ref)
      if (!source) {
        issues.push({ message: `Input "${socket}" points at unknown node "${ref}".`, nodeId: node.id, socket })
        continue
      }
      const produced = NODE_TYPES[source.type]?.output
      if (produced && produced !== spec.inputs[socket]) {
        issues.push({
          message: `Input "${socket}" needs a ${spec.inputs[socket]}, but "${ref}" produces a ${produced}.`,
          nodeId: node.id,
          socket,
        })
        continue
      }
      if (produced === 'profile') {
        const consumer = profileConsumers.get(ref)
        if (consumer === undefined) profileConsumers.set(ref, node.id)
        else if (consumer !== node.id) {
          issues.push({
            message: `Profile "${ref}" already feeds "${consumer}"; a profile can feed one node — duplicate the profile node.`,
            nodeId: node.id,
            socket,
          })
        }
      }
      const axisProblem = revolveAxisProblem(node, source)
      if (axisProblem) issues.push({ message: axisProblem, nodeId: node.id, param: 'axis' })
    }
    const extentProblem = revolveExtentProblem(node, byId)
    if (extentProblem) issues.push({ message: extentProblem, nodeId: node.id })
    const angleProblem = revolveAngleProblem(node)
    if (angleProblem) issues.push({ message: angleProblem, nodeId: node.id, param: 'angle' })
  }

  // G-EXPR: declarations, derived values and every expression-valued param.
  if (requiredVersion(g) === '1.1' && !versionAtLeast11(g.version)) {
    push('A graph that declares parameters or derived values must be version 1.1.')
  }
  if (g.parameters && typeof g.parameters === 'object' && Object.keys(g.parameters).length > LIMITS.max_parameters) {
    push(`Too many declared parameters: ${Object.keys(g.parameters).length} (limit ${LIMITS.max_parameters}).`)
  }
  if (Array.isArray(g.derived) && g.derived.length > LIMITS.max_derived) {
    push(`Too many derived values: ${g.derived.length} (limit ${LIMITS.max_derived}).`)
  }
  for (const [pid, decl] of Object.entries(g.parameters ?? {})) {
    const entries = decl && typeof decl === 'object' && decl.map ? Object.keys(decl.map).length : 0
    if (entries > LIMITS.max_map_entries) push(`Declared parameter "${pid}" maps ${entries} options (limit ${LIMITS.max_map_entries}).`)
  }
  const { scope, issues: scopeIssues } = buildScope(g)
  issues.push(...scopeIssues)
  const declared = g.parameters ?? {}
  // Names some expression reads — a derived value's or a node param's. The
  // engine refuses a declaration nothing reads (G-DEADPARAM).
  const read = new Set<string>()
  for (const entry of Array.isArray(g.derived) ? g.derived : []) {
    if (typeof entry?.expr === 'string') for (const id of expressionIdentifiers(entry.expr)) read.add(id)
  }
  const derivedIds = (Array.isArray(g.derived) ? g.derived : []).map((d) => d?.id).filter((d): d is string => typeof d === 'string')
  for (const node of byId.values()) {
    const spec = NODE_TYPES[node.type]
    for (const [name, value] of Object.entries(node.params ?? {})) {
      const def = spec?.params[name]
      if (!def || def.expr !== true) continue
      const expressions: Array<{ expr: string; label: string; numeric: boolean }> = []
      if (isExpressionValue(value) && def.kind !== 'points') {
        expressions.push({ expr: value.expr, label: `"${name}"`, numeric: def.kind !== 'condition' })
      } else if (def.kind === 'points' && Array.isArray(value)) {
        value.forEach((point, i) => {
          if (!Array.isArray(point)) return
          point.forEach((coord, axis) => {
            if (isExpressionValue(coord)) expressions.push({ expr: coord.expr, label: `"${name}" point ${i + 1} ${axis === 0 ? 'x' : 'y'}`, numeric: true })
          })
        })
      }
      for (const { expr, label, numeric } of expressions) {
        for (const id of expressionIdentifiers(expr)) read.add(id)
        const problem = expressionProblem(expr, declared, scope, derivedIds, numeric)
        if (problem) issues.push({ message: `${label}: ${problem}.`, nodeId: node.id, param: name })
      }
    }
  }

  for (const id of Object.keys(declared)) {
    if (!read.has(id)) push(`Declared parameter "${id}" is never read by any expression.`)
  }
  for (const entry of Array.isArray(g.derived) ? g.derived : []) {
    if (typeof entry?.id === 'string' && !read.has(entry.id)) {
      issues.push({ message: `Derived value "${entry.id}" is never read by any expression.`, derivedId: entry.id })
    }
  }

  for (const cycle of findCycles(Array.from(byId.values()))) {
    push(`These nodes feed each other in a loop: ${cycle.join(' → ')}.`)
  }

  const outputs = g.outputs
  if (typeof outputs !== 'object' || outputs === null || Array.isArray(outputs) || Object.keys(outputs).length === 0) {
    push('A graph needs at least one output part.')
  } else {
    if (Object.keys(outputs).length > LIMITS.max_outputs) {
      push(`Too many outputs: ${Object.keys(outputs).length} (limit ${LIMITS.max_outputs}).`)
    }
    for (const [partId, ref] of Object.entries(outputs)) {
      const source = byId.get(ref)
      if (!source) {
        push(`Output "${partId}" points at unknown node "${ref}".`)
      } else if (NODE_TYPES[source.type]?.output !== 'solid') {
        push(`Output "${partId}" is a profile — extrude it into a solid first.`)
      }
    }
  }

  return issues
}

/** Every dependency cycle, each as the node ids involved. */
export function findCycles(nodes: GraphNode[]): string[][] {
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const state = new Map<string, 'visiting' | 'done'>()
  const cycles: string[][] = []
  const seen = new Set<string>()

  // Iterative depth-first search: a deeply chained graph must not blow the stack.
  for (const start of byId.keys()) {
    if (state.get(start)) continue
    const path: string[] = []
    const stack: Array<{ id: string; deps: string[]; i: number }> = [
      { id: start, deps: dependenciesOf(byId.get(start)!), i: 0 },
    ]
    state.set(start, 'visiting')
    path.push(start)

    while (stack.length > 0) {
      const frame = stack[stack.length - 1]
      if (frame.i >= frame.deps.length) {
        state.set(frame.id, 'done')
        stack.pop()
        path.pop()
        continue
      }
      const next = frame.deps[frame.i++]
      if (!byId.has(next)) continue
      if (state.get(next) === 'visiting') {
        const cycle = path.slice(path.indexOf(next))
        const key = [...cycle].sort().join(',')
        if (!seen.has(key)) {
          seen.add(key)
          cycles.push(cycle)
        }
        continue
      }
      if (state.get(next) === 'done') continue
      state.set(next, 'visiting')
      path.push(next)
      stack.push({ id: next, deps: dependenciesOf(byId.get(next)!), i: 0 })
    }
  }
  return cycles
}

function dependenciesOf(node: GraphNode): string[] {
  return Object.values(node.inputs ?? {})
}

/**
 * Node ids in dependency order — every node after the ones it consumes.
 * Returns null when the graph contains a cycle.
 */
export function topologicalOrder(nodes: GraphNode[]): string[] | null {
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const emitted = new Set<string>()
  const order: string[] = []
  let remaining = nodes.slice()

  while (remaining.length > 0) {
    const ready = remaining.filter((n) =>
      dependenciesOf(n).every((dep) => !byId.has(dep) || emitted.has(dep)),
    )
    if (ready.length === 0) return null
    for (const node of ready) {
      emitted.add(node.id)
      order.push(node.id)
    }
    remaining = remaining.filter((n) => !emitted.has(n.id))
  }
  return order
}

/**
 * Depth of each node — 0 for nodes with no inputs, otherwise one past the
 * deepest thing it consumes. Laying a graph out by depth puts sources on the
 * left and the final solid on the right, which is how these graphs read.
 * Returns null when the graph contains a cycle, since depth is then undefined.
 */
export function dependencyDepth(nodes: GraphNode[]): Map<string, number> | null {
  const order = topologicalOrder(nodes)
  if (!order) return null
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const depth = new Map<string, number>()
  for (const id of order) {
    const deps = dependenciesOf(byId.get(id)!).filter((d) => byId.has(d))
    depth.set(id, deps.length === 0 ? 0 : Math.max(...deps.map((d) => depth.get(d) ?? 0)) + 1)
  }
  return depth
}

/** Ids of every node downstream of the given one, including itself. */
export function downstreamOf(nodes: GraphNode[], nodeId: string): Set<string> {
  const dirty = new Set<string>([nodeId])
  let grew = true
  while (grew) {
    grew = false
    for (const node of nodes) {
      if (dirty.has(node.id)) continue
      if (dependenciesOf(node).some((dep) => dirty.has(dep))) {
        dirty.add(node.id)
        grew = true
      }
    }
  }
  return dirty
}

/** Would connecting source → target create a cycle? */
export function wouldCycle(nodes: GraphNode[], sourceId: string, targetId: string): boolean {
  if (sourceId === targetId) return true
  return downstreamOf(nodes, targetId).has(sourceId)
}

/** A node id not already used, derived from the type name. */
export function uniqueNodeId(nodes: GraphNode[], type: string): string {
  const base = type.replace(/[^A-Za-z0-9_]/g, '_')
  const used = new Set(nodes.map((n) => n.id))
  for (let i = 1; ; i += 1) {
    const candidate = `${base}_${i}`
    if (!used.has(candidate)) return candidate
  }
}

// ── Immutable edits ───────────────────────────────────────────────────────────
// Each returns a new document; React state updates stay predictable and undo
// is a matter of keeping previous values.

export function addNode(doc: GraphDoc, type: string, id?: string): GraphDoc {
  if (!NODE_TYPES[type]) throw new Error(`Unknown node type "${type}"`)
  const nodeId = id ?? uniqueNodeId(doc.nodes, type)
  const node: GraphNode = { id: nodeId, type, params: defaultParams(type) }
  if (Object.keys(NODE_TYPES[type].inputs).length > 0) node.inputs = {}
  return { ...doc, nodes: [...doc.nodes, node] }
}

/** Remove a node, and every reference to it from inputs and outputs. */
export function removeNode(doc: GraphDoc, nodeId: string): GraphDoc {
  const nodes = doc.nodes
    .filter((n) => n.id !== nodeId)
    .map((n) => {
      if (!n.inputs) return n
      const kept = Object.entries(n.inputs).filter(([, ref]) => ref !== nodeId)
      if (kept.length === Object.keys(n.inputs).length) return n
      return { ...n, inputs: Object.fromEntries(kept) }
    })
  const outputs = Object.fromEntries(Object.entries(doc.outputs).filter(([, ref]) => ref !== nodeId))
  return { ...doc, nodes, outputs }
}

export function setNodeParam(doc: GraphDoc, nodeId: string, name: string, value: ParamValue): GraphDoc {
  return {
    ...doc,
    nodes: doc.nodes.map((n) =>
      n.id === nodeId ? { ...n, params: { ...(n.params ?? {}), [name]: value } } : n,
    ),
  }
}

/** Revert a param to the catalog default by removing the stored value. */
export function clearNodeParam(doc: GraphDoc, nodeId: string, name: string): GraphDoc {
  return {
    ...doc,
    nodes: doc.nodes.map((n) => {
      if (n.id !== nodeId || !n.params || !(name in n.params)) return n
      const { [name]: _removed, ...rest } = n.params
      return { ...n, params: rest }
    }),
  }
}

/**
 * Where the editor drew a node. Stored in `meta`, which the renderer ignores,
 * so moving a node never changes the geometry or the render cache key.
 */
export function setNodePosition(doc: GraphDoc, nodeId: string, position: NodePosition): GraphDoc {
  const x = Math.round(position.x)
  const y = Math.round(position.y)
  return {
    ...doc,
    nodes: doc.nodes.map((n) => (n.id === nodeId ? { ...n, meta: { ...(n.meta ?? {}), position: { x, y } } } : n)),
  }
}

/** The stored editor position of a node, if it has a valid one. */
export function nodePosition(node: GraphNode): NodePosition | null {
  const pos = node.meta?.position as Partial<NodePosition> | undefined
  if (!pos || typeof pos.x !== 'number' || typeof pos.y !== 'number') return null
  if (!Number.isFinite(pos.x) || !Number.isFinite(pos.y)) return null
  return { x: pos.x, y: pos.y }
}

/**
 * Why source → target.socket may not be connected, or null when it may. The
 * same rules `connect()` enforces, as a question rather than a throw, so a
 * drag can be refused while it is still a drag.
 */
export function connectionProblem(doc: GraphDoc, targetId: string, socket: string, sourceId: string): string | null {
  const target = doc.nodes.find((n) => n.id === targetId)
  if (!target) return `Unknown node "${targetId}"`
  const spec = NODE_TYPES[target.type]
  if (!spec?.inputs[socket]) return `"${target.type}" has no input "${socket}"`
  const source = doc.nodes.find((n) => n.id === sourceId)
  if (!source) return `Unknown node "${sourceId}"`
  const produced = NODE_TYPES[source.type]?.output
  if (produced !== spec.inputs[socket]) {
    return `Input "${socket}" needs a ${spec.inputs[socket]}, but "${sourceId}" produces a ${produced}`
  }
  if (wouldCycle(doc.nodes, sourceId, targetId)) {
    return `Connecting "${sourceId}" to "${targetId}" would create a loop`
  }
  if (produced === 'profile') {
    const other = doc.nodes.find((n) => n.id !== targetId && Object.values(n.inputs ?? {}).includes(sourceId))
    if (other) return `Profile "${sourceId}" already feeds "${other.id}"; a profile can feed one node — duplicate the profile node`
  }
  return null
}

/** Connect source → target.socket, refusing a connection that would loop. */
export function connect(doc: GraphDoc, targetId: string, socket: string, sourceId: string): GraphDoc {
  const problem = connectionProblem(doc, targetId, socket, sourceId)
  if (problem) throw new Error(problem)
  return {
    ...doc,
    nodes: doc.nodes.map((n) =>
      n.id === targetId ? { ...n, inputs: { ...(n.inputs ?? {}), [socket]: sourceId } } : n,
    ),
  }
}

export function disconnect(doc: GraphDoc, targetId: string, socket: string): GraphDoc {
  return {
    ...doc,
    nodes: doc.nodes.map((n) => {
      if (n.id !== targetId || !n.inputs) return n
      const { [socket]: _removed, ...rest } = n.inputs
      return { ...n, inputs: rest }
    }),
  }
}

export function setOutput(doc: GraphDoc, partId: string, nodeId: string): GraphDoc {
  return { ...doc, outputs: { ...doc.outputs, [partId]: nodeId } }
}

export function removeOutput(doc: GraphDoc, partId: string): GraphDoc {
  const { [partId]: _removed, ...rest } = doc.outputs
  return { ...doc, outputs: rest }
}

// ── Engine rules the editor mirrors ───────────────────────────────────────────

/** Why an expression cannot stand where it is, or null. */
export function expressionProblem(
  expr: string,
  declared: Record<string, DeclaredParameter>,
  scope: Record<string, number | boolean>,
  derivedIds: string[],
  numeric: boolean,
): string | null {
  if (expr.length > EXPRESSION_LIMITS.max_length) {
    return `the expression is longer than ${EXPRESSION_LIMITS.max_length} characters`
  }
  const check = checkExpression(expr, declared, scope, derivedIds)
  if (check.error) return check.error
  if (numeric && typeof check.value !== 'number') return 'the expression gives a true/false, not a number'
  return null
}

/** A revolve's axis must lie in its profile's plane (both are literals). */
function revolveAxisProblem(node: GraphNode, source: GraphNode): string | null {
  if (node.type !== 'revolve' || NODE_TYPES[source.type]?.output !== 'profile') return null
  const axis = node.params?.axis ?? paramSpec('revolve', 'axis')?.default
  const plane = source.params?.plane ?? paramSpec(source.type, 'plane')?.default ?? 'XY'
  const inPlane = PLANE_AXES[plane as string]
  if (!inPlane || typeof axis !== 'string' || !AXES.includes(axis)) return null
  return inPlane.includes(axis) ? null : `The revolve axis "${axis}" is not in the profile's ${plane} plane.`
}

/** A literal revolve angle must be in (0, 360]; the engine checks expressions at render. */
function revolveAngleProblem(node: GraphNode): string | null {
  if (node.type !== 'revolve') return null
  const angle = node.params?.angle
  if (typeof angle !== 'number') return null
  return angle > 0 && angle <= 360 ? null : '"angle" must be more than 0 and at most 360 degrees.'
}

/**
 * A revolve may reach at most `max_revolve_extent_mm` from the origin. Decidable
 * here only for a literal polyline profile; the engine checks every case at render.
 */
function revolveExtentProblem(node: GraphNode, byId: Map<string, GraphNode>): string | null {
  if (node.type !== 'revolve') return null
  const profile = byId.get(node.inputs?.profile ?? '')
  if (!profile || profile.type !== 'profile_polyline' || !Array.isArray(profile.params?.points)) return null
  let reach = 0
  for (const point of profile.params.points as unknown[]) {
    if (!Array.isArray(point) || typeof point[0] !== 'number' || typeof point[1] !== 'number') return null
    reach = Math.max(reach, Math.hypot(point[0], point[1]))
  }
  const max = LIMITS.max_revolve_extent_mm
  return reach > max ? `The profile reaches ${Math.round(reach)} mm from the origin; a revolve may reach ${max} mm.` : null
}

// ── Serialization ─────────────────────────────────────────────────────────────

/** Parse and validate. Throws with every problem listed, not just the first. */
export function parseGraph(text: string): GraphDoc {
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch (err) {
    throw new Error(`That file is not valid JSON: ${(err as Error).message}`)
  }
  const issues = validateGraph(parsed)
  if (issues.length > 0) {
    throw new Error(
      `This graph has ${issues.length} problem${issues.length === 1 ? '' : 's'}:\n` +
        issues.map((i) => `• ${i.nodeId ? `${i.nodeId}: ` : ''}${i.message}`).join('\n'),
    )
  }
  return parsed as GraphDoc
}

/**
 * The document as text. Given the `source` text it was read from, the source's
 * layout and number spelling are kept wherever the document did not change
 * (graphFormat.ts): an unedited document comes back byte-identical, and an
 * edit changes only the lines it touches. Without one, two-space JSON.
 */
export function serializeGraph(doc: GraphDoc, source?: string | null): string {
  return formatLike(doc, source)
}
