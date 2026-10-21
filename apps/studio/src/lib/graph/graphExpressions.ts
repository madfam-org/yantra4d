/**
 * G-EXPR on the client: expressions in node params, the parameters a graph
 * declares, and its ordered derived values.
 *
 * The engine evaluates expressions at transpile time with the same safeFormula
 * dialect the manifest constraints use (`../safeFormula.ts`), so the editor
 * evaluates them with that very function. Identifiers are manifest parameter
 * ids, and a graph must declare every id it reads in its top-level
 * `parameters` object; `derived` entries may read declared parameters and
 * EARLIER derived ids, and a node expression may read both.
 *
 * Values follow safeFormula's rules: numbers and booleans are used as they
 * are, a numeric string is parsed ("608" → 608), and anything else needs the
 * declaration's `map` (option → number), which the author supplies. The editor
 * never invents those numbers.
 *
 * This module imports only types from graphDocument, so graphDocument can call
 * into it without an import cycle.
 */
import { evaluateSafeFormula } from '../safeFormula'
import type { DeclaredParameter, DerivedValue, GraphDoc, GraphIssue } from './graphDocument'

export const GRAPH_VERSION_WITH_DECLARATIONS = '1.1.0'

const IDENT_RE = /^[A-Za-z][A-Za-z0-9_]*$/
// Names the generated script already uses, and Python keywords: the engine
// refuses both as parameter or derived ids (graph_engine.py _identifier_rules).
const RESERVED = new Set([
  'cq', 'math', 'result', 'assembly', 'part', 'show_object', 'target_part',
  'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class',
  'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global',
  'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
  'return', 'try', 'while', 'with', 'yield',
])
// A map key / option value the engine accepts (graph_engine.py _OPTION_RE).
const OPTION_RE = /^[A-Za-z0-9_. -]{0,64}$/
const DECLARATION_KEYS = new Set(['default', 'map'])

/** Why `id` cannot name a parameter or derived value, or null. */
export function identifierProblem(id: unknown): string | null {
  if (typeof id !== 'string' || !IDENT_RE.test(id)) return 'is not a plain identifier'
  if (RESERVED.has(id)) return 'is a reserved name'
  return null
}
// The same scan safeFormula's tokenizer makes: a number is consumed before an
// identifier can start, so `2abc` is the number 2 followed by `abc`.
const TOKEN_RE = /(\d+(?:\.\d*)?|\.\d+)|([A-Za-z_$][A-Za-z0-9_$]*)/g

/** Every distinct identifier an expression reads, in first-use order. */
export function expressionIdentifiers(source: string): string[] {
  const seen: string[] = []
  for (const match of source.matchAll(TOKEN_RE)) {
    const ident = match[2]
    if (ident && !seen.includes(ident)) seen.push(ident)
  }
  return seen
}

/** A manifest parameter, reduced to what declaring and binding need. */
export interface ManifestParameterLike {
  id: string
  type?: string
  default?: unknown
  options?: Array<{ value: unknown }>
  binding?: string | string[]
}

/**
 * The number (or boolean) a declared parameter contributes to the scope, or
 * undefined when it has none — which is what safeFormula reports as
 * "Missing numeric parameter" when the expression reads it.
 */
export function declaredValue(
  decl: DeclaredParameter,
  manifestDefault?: unknown,
): number | boolean | undefined {
  const raw = manifestDefault !== undefined ? manifestDefault : decl.default
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : undefined
  if (typeof raw === 'boolean') return raw
  if (typeof raw === 'string') {
    if (decl.map && Object.prototype.hasOwnProperty.call(decl.map, raw)) return decl.map[raw]
    if (raw.trim() !== '') {
      const parsed = Number(raw)
      if (Number.isFinite(parsed)) return parsed
    }
  }
  return undefined
}

/**
 * Why a declaration would be refused, or null: the engine accepts a number, a
 * boolean, or an option value that is numeric text or a key of `map`; map keys
 * are option values and map values finite numbers.
 */
export function declarationProblem(decl: DeclaredParameter): string | null {
  if (decl.map !== undefined) {
    if (typeof decl.map !== 'object' || decl.map === null || Object.keys(decl.map).length === 0) {
      return "has an empty or malformed 'map'"
    }
    for (const [option, number] of Object.entries(decl.map)) {
      if (!OPTION_RE.test(option)) return `maps ${JSON.stringify(option)}, which is not a plain option value`
      if (typeof number !== 'number' || !Number.isFinite(number)) return `maps ${JSON.stringify(option)} to something that is not a number`
    }
  }
  const d = decl.default
  if (typeof d === 'boolean') return null
  if (typeof d === 'number') return Number.isFinite(d) ? null : 'has a default that is not finite'
  if (typeof d === 'string' && OPTION_RE.test(d)) {
    const numeric = d.trim() !== '' && Number.isFinite(Number(d))
    if (numeric || (decl.map && d in decl.map)) return null
    return `has the default ${JSON.stringify(d)}, which is neither numeric nor in its map`
  }
  return 'has a default that is not a number, a boolean or an option value'
}

/** A select parameter whose options are not all numeric needs a map to be read. */
export function needsMap(param: ManifestParameterLike): boolean {
  if (param.type !== 'select') return false
  const values = (param.options ?? []).map((o) => o.value)
  return values.some((v) => !(typeof v === 'number' || (typeof v === 'string' && v.trim() !== '' && Number.isFinite(Number(v)))))
}

export interface ScopeResult {
  scope: Record<string, number | boolean>
  issues: GraphIssue[]
}

/**
 * Evaluate the graph's declarations into a scope. Manifest defaults, when
 * given, stand in for the declared fallbacks — that is what a render sees.
 */
export function buildScope(doc: Partial<GraphDoc>, manifestDefaults: Record<string, unknown> = {}): ScopeResult {
  const scope: Record<string, number | boolean> = {}
  const issues: GraphIssue[] = []
  const declared = doc.parameters ?? {}

  for (const [id, decl] of Object.entries(declared)) {
    const idProblem = identifierProblem(id)
    if (idProblem) {
      issues.push({ message: `Declared parameter "${id}" ${idProblem}.` })
      continue
    }
    if (typeof decl !== 'object' || decl === null || !('default' in decl)) {
      issues.push({ message: `Declared parameter "${id}" needs a default.` })
      continue
    }
    const unknownKeys = Object.keys(decl).filter((k) => !DECLARATION_KEYS.has(k))
    if (unknownKeys.length > 0) {
      issues.push({ message: `Declared parameter "${id}" has unknown keys: ${unknownKeys.join(', ')}.` })
    }
    const declProblem = declarationProblem(decl)
    if (declProblem) {
      issues.push({ message: `Declared parameter "${id}" ${declProblem}.` })
      continue
    }
    const value = declaredValue(decl, manifestDefaults[id])
    if (value !== undefined) scope[id] = value
  }

  const derived = Array.isArray(doc.derived) ? doc.derived : []
  const seen = new Set<string>()
  for (const entry of derived) {
    const id = (entry as DerivedValue)?.id
    const idProblem = identifierProblem(id)
    if (idProblem) {
      issues.push({ message: `Derived value id ${JSON.stringify(id ?? null)} ${idProblem}.` })
      continue
    }
    const keys = Object.keys(entry as object)
    if (keys.length !== 2 || !keys.includes('expr')) {
      issues.push({ message: `Derived value "${id}" must have exactly "id" and "expr".`, derivedId: id })
      continue
    }
    if (seen.has(id) || id in declared) {
      issues.push({ message: `Derived value "${id}" is defined twice.`, derivedId: id })
      continue
    }
    seen.add(id)
    const check = checkExpression(entry.expr, declared, scope, [...seen].filter((d) => d !== id))
    if (check.error) {
      issues.push({ message: `Derived value "${id}": ${check.error}`, derivedId: id })
      continue
    }
    scope[id] = check.value as number | boolean
  }
  return { scope, issues }
}

export interface ExpressionCheck {
  value?: number | boolean
  error?: string
  /** Identifiers that are neither declared parameters nor (earlier) derived ids. */
  undeclared: string[]
}

/**
 * Validate one expression against what it may read: the declared parameters
 * and the derived ids listed in `derivedIds`. Evaluates it with `scope`.
 */
export function checkExpression(
  source: unknown,
  declared: Record<string, DeclaredParameter>,
  scope: Record<string, number | boolean>,
  derivedIds: string[],
): ExpressionCheck {
  if (typeof source !== 'string' || source.trim() === '') {
    return { error: 'the expression is empty', undeclared: [] }
  }
  const undeclared = expressionIdentifiers(source).filter((id) => !(id in declared) && !derivedIds.includes(id))
  if (undeclared.length > 0) {
    return { error: `reads ${undeclared.map((u) => `"${u}"`).join(', ')}, which is not declared`, undeclared }
  }
  try {
    const value = evaluateSafeFormula(source, scope)
    return { value, undeclared }
  } catch (err) {
    return { error: (err as Error).message, undeclared }
  }
}

/** Version a document must declare given what it uses. */
export function requiredVersion(doc: Partial<GraphDoc>): '1.0' | '1.1' {
  const usesDeclarations =
    (doc.parameters !== undefined && Object.keys(doc.parameters).length > 0) ||
    (Array.isArray(doc.derived) && doc.derived.length > 0)
  return usesDeclarations ? '1.1' : '1.0'
}

/** Whether `version` (e.g. "1.1.0") is at least 1.1. */
export function versionAtLeast11(version: unknown): boolean {
  if (typeof version !== 'string') return false
  const minor = Number(version.split('.')[1])
  return Number.isFinite(minor) && minor >= 1
}

// ── Immutable edits on the declarations ───────────────────────────────────────

function withDeclarations(doc: GraphDoc, next: Partial<GraphDoc>): GraphDoc {
  const merged: GraphDoc = { ...doc, ...next }
  if (merged.parameters && Object.keys(merged.parameters).length === 0) delete merged.parameters
  if (merged.derived && merged.derived.length === 0) delete merged.derived
  if (requiredVersion(merged) === '1.1' && !versionAtLeast11(merged.version)) {
    merged.version = GRAPH_VERSION_WITH_DECLARATIONS
  }
  return merged
}

/** Declare a manifest parameter so expressions may read it. */
export function declareParameter(doc: GraphDoc, id: string, decl: DeclaredParameter): GraphDoc {
  const problem = identifierProblem(id)
  if (problem) throw new Error(`"${id}" ${problem}`)
  return withDeclarations(doc, { parameters: { ...(doc.parameters ?? {}), [id]: decl } })
}

export function undeclareParameter(doc: GraphDoc, id: string): GraphDoc {
  const { [id]: _removed, ...rest } = doc.parameters ?? {}
  return withDeclarations(doc, { parameters: rest })
}

/** Set (or, with null, clear) a declared parameter's option → number map. */
export function setParameterMap(doc: GraphDoc, id: string, map: Record<string, number> | null): GraphDoc {
  const decl = doc.parameters?.[id]
  if (!decl) throw new Error(`"${id}" is not declared`)
  const next: DeclaredParameter = { default: decl.default }
  if (map && Object.keys(map).length > 0) next.map = map
  return withDeclarations(doc, { parameters: { ...doc.parameters, [id]: next } })
}

export function addDerived(doc: GraphDoc, id: string, expr: string): GraphDoc {
  const problem = identifierProblem(id)
  if (problem) throw new Error(`"${id}" ${problem}`)
  const derived = doc.derived ?? []
  if (derived.some((d) => d.id === id) || (doc.parameters && id in doc.parameters)) {
    throw new Error(`"${id}" is already defined`)
  }
  return withDeclarations(doc, { derived: [...derived, { id, expr }] })
}

export function setDerivedExpr(doc: GraphDoc, id: string, expr: string): GraphDoc {
  return withDeclarations(doc, {
    derived: (doc.derived ?? []).map((d) => (d.id === id ? { ...d, expr } : d)),
  })
}

export function removeDerived(doc: GraphDoc, id: string): GraphDoc {
  return withDeclarations(doc, { derived: (doc.derived ?? []).filter((d) => d.id !== id) })
}

/** Move a derived value one place earlier (-1) or later (+1). Order matters. */
export function moveDerived(doc: GraphDoc, id: string, delta: -1 | 1): GraphDoc {
  const derived = [...(doc.derived ?? [])]
  const from = derived.findIndex((d) => d.id === id)
  const to = from + delta
  if (from < 0 || to < 0 || to >= derived.length) return doc
  const [entry] = derived.splice(from, 1)
  derived.splice(to, 0, entry)
  return withDeclarations(doc, { derived })
}
