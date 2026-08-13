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

export type SocketType = 'solid' | 'profile'
export type ParamKind = 'float' | 'count' | 'selector' | 'axis' | 'plane'

export interface NodeTypeSpec {
  output: SocketType
  inputs: Record<string, SocketType>
  params: Record<string, { kind: ParamKind; default: number | string; bindable: boolean }>
}

export interface GraphNode {
  id: string
  type: string
  params?: Record<string, number | string>
  inputs?: Record<string, string>
  meta?: Record<string, unknown>
}

export interface GraphDoc {
  version: string
  units?: string
  meta?: Record<string, unknown>
  nodes: GraphNode[]
  outputs: Record<string, string>
}

export const NODE_TYPES = catalog.nodes as unknown as Record<string, NodeTypeSpec>
export const LIMITS = catalog.limits as { max_nodes: number; max_outputs: number; max_pattern_count: number }
export const PLANES = catalog.planes as string[]

const ID_RE = /^[A-Za-z][A-Za-z0-9_]*$/
const VERSION_RE = /^1\.\d+(\.\d+)?$/

/** A validation problem, addressed to whoever is editing the graph. */
export interface GraphIssue {
  message: string
  nodeId?: string
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
export function defaultParams(type: string): Record<string, number | string> {
  const spec = NODE_TYPES[type]
  if (!spec) return {}
  const params: Record<string, number | string> = {}
  for (const [name, def] of Object.entries(spec.params)) params[name] = def.default
  return params
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
      if (!(name in spec.params)) push(`"${node.type}" has no parameter "${name}".`, node.id)
    }
    const sockets = Object.keys(spec.inputs)
    const given = Object.keys(node.inputs ?? {})
    for (const socket of sockets) {
      if (!given.includes(socket)) push(`Missing input "${socket}".`, node.id)
    }
    for (const socket of given) {
      if (!sockets.includes(socket)) push(`"${node.type}" has no input "${socket}".`, node.id)
    }
    byId.set(node.id, node)
  }

  // Reference targets and socket types (needs every id known first).
  for (const node of byId.values()) {
    const spec = NODE_TYPES[node.type]
    for (const [socket, ref] of Object.entries(node.inputs ?? {})) {
      if (!spec?.inputs[socket]) continue
      if (ref === node.id) {
        push(`Input "${socket}" connects the node to itself.`, node.id)
        continue
      }
      const source = byId.get(ref)
      if (!source) {
        push(`Input "${socket}" points at unknown node "${ref}".`, node.id)
        continue
      }
      const produced = NODE_TYPES[source.type]?.output
      if (produced && produced !== spec.inputs[socket]) {
        push(`Input "${socket}" needs a ${spec.inputs[socket]}, but "${ref}" produces a ${produced}.`, node.id)
      }
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

export function setNodeParam(doc: GraphDoc, nodeId: string, name: string, value: number | string): GraphDoc {
  return {
    ...doc,
    nodes: doc.nodes.map((n) =>
      n.id === nodeId ? { ...n, params: { ...(n.params ?? {}), [name]: value } } : n,
    ),
  }
}

/** Connect source → target.socket, refusing a connection that would loop. */
export function connect(doc: GraphDoc, targetId: string, socket: string, sourceId: string): GraphDoc {
  const target = doc.nodes.find((n) => n.id === targetId)
  if (!target) throw new Error(`Unknown node "${targetId}"`)
  const spec = NODE_TYPES[target.type]
  if (!spec?.inputs[socket]) throw new Error(`"${target.type}" has no input "${socket}"`)
  const source = doc.nodes.find((n) => n.id === sourceId)
  if (!source) throw new Error(`Unknown node "${sourceId}"`)
  const produced = NODE_TYPES[source.type]?.output
  if (produced !== spec.inputs[socket]) {
    throw new Error(`Input "${socket}" needs a ${spec.inputs[socket]}, but "${sourceId}" produces a ${produced}`)
  }
  if (wouldCycle(doc.nodes, sourceId, targetId)) {
    throw new Error(`Connecting "${sourceId}" to "${targetId}" would create a loop`)
  }
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

export function serializeGraph(doc: GraphDoc): string {
  return `${JSON.stringify(doc, null, 2)}\n`
}
