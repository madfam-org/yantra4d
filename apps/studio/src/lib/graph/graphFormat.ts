/**
 * Layout-preserving JSON writer for graph documents.
 *
 * A graph document is edited as a parsed object and written back as text. A
 * plain `JSON.stringify(doc, null, 2)` throws away the source's layout: the
 * commons writes one node per line and spells numbers as authored (`14.0`), so
 * a one-parameter edit came back as a rewrite of the whole file. Reviewing a
 * fork's change, or proposing it back to the commons, then means reading the
 * entire document.
 *
 * `formatLike(value, source)` writes `value` reusing `source`'s text wherever
 * the value did not change:
 *  - an unchanged value (deep-equal, numbers compared by value) is copied from
 *    the source verbatim, so `14.0` stays `14.0`;
 *  - a changed object or array keeps its own brackets, the whitespace between
 *    its members and each member's `"key": ` text, and recurses into members;
 *  - array items that are objects with a string `id` (nodes, derived values)
 *    are matched by id, so inserting or removing one leaves the others' text
 *    alone; other arrays match by position;
 *  - a new value is written in the style of its neighbours: on one line where
 *    they are on one line, indented where they are indented.
 *
 * So an unchanged document is returned byte-identical, and an edit changes
 * only the lines it touches. Text that is not valid JSON (the buffer is being
 * typed) falls back to the plain two-space format.
 */

type Json = null | boolean | number | string | Json[] | { [key: string]: Json }

interface Span {
  start: number
  end: number
  value: Json
}

interface Member {
  /** Whitespace between the previous delimiter (`{`, `[` or `,`) and this member. */
  before: string
  /** Whitespace between this member and the next delimiter (`,`, `}` or `]`). */
  after: string
  /** Object members only: the key, and the text from the key to the value (`"key": `). */
  key?: string
  keyText?: string
  node: Node
}

type Node =
  | (Span & { kind: 'scalar' })
  | (Span & { kind: 'object' | 'array'; members: Member[]; /** whitespace inside an empty container */ inner: string })

const WS = /[ \t\n\r]/

class Scanner {
  pos = 0
  constructor(readonly text: string) {}

  ws(): string {
    const from = this.pos
    while (this.pos < this.text.length && WS.test(this.text[this.pos])) this.pos++
    return this.text.slice(from, this.pos)
  }

  fail(what: string): never {
    throw new SyntaxError(`${what} at offset ${this.pos}`)
  }

  string(): number {
    const from = this.pos
    if (this.text[this.pos] !== '"') this.fail('Expected a string')
    this.pos++
    while (this.pos < this.text.length) {
      const ch = this.text[this.pos]
      if (ch === '\\') this.pos += 2
      else if (ch === '"') return ++this.pos - from
      else this.pos++
    }
    return this.fail('Unterminated string')
  }

  value(): Node {
    const start = this.pos
    const ch = this.text[this.pos]
    if (ch === '{' || ch === '[') return this.container(ch === '{' ? 'object' : 'array')
    if (ch === '"') this.string()
    else {
      const m = /^(?:-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)/.exec(this.text.slice(this.pos))
      if (!m) this.fail('Unexpected token')
      this.pos += m[0].length
    }
    return { kind: 'scalar', start, end: this.pos, value: JSON.parse(this.text.slice(start, this.pos)) as Json }
  }

  container(kind: 'object' | 'array'): Node {
    const start = this.pos
    const close = kind === 'object' ? '}' : ']'
    this.pos++
    const members: Member[] = []
    let inner = ''
    const lead = this.ws()
    if (this.text[this.pos] === close) {
      inner = lead
    } else {
      let before = lead
      for (;;) {
        let key: string | undefined
        let keyText: string | undefined
        if (kind === 'object') {
          const keyStart = this.pos
          this.string()
          key = JSON.parse(this.text.slice(keyStart, this.pos)) as string
          this.ws()
          if (this.text[this.pos] !== ':') this.fail('Expected ":"')
          this.pos++
          this.ws()
          keyText = this.text.slice(keyStart, this.pos)
        }
        const node = this.value()
        const after = this.ws()
        members.push({ before, after, key, keyText, node })
        if (this.text[this.pos] === ',') {
          this.pos++
          before = this.ws()
          continue
        }
        if (this.text[this.pos] === close) break
        this.fail(`Expected "," or "${close}"`)
      }
    }
    this.pos++
    const value: Json = kind === 'object'
      ? Object.fromEntries(members.map((m) => [m.key as string, m.node.value]))
      : members.map((m) => m.node.value)
    return { kind, start, end: this.pos, value, members, inner }
  }
}

/** Parse `text` into a tree that remembers where every value came from. */
function parseSpans(text: string): Node {
  const s = new Scanner(text)
  s.ws()
  const root = s.value()
  s.ws()
  if (s.pos !== text.length) s.fail('Unexpected trailing text')
  return root
}

function isObject(v: unknown): v is Record<string, Json> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true
  if (Array.isArray(a)) {
    return Array.isArray(b) && a.length === b.length && a.every((x, i) => deepEqual(x, b[i]))
  }
  if (isObject(a) && isObject(b)) {
    const ka = Object.keys(a).filter((k) => a[k] !== undefined)
    const kb = Object.keys(b).filter((k) => b[k] !== undefined)
    // Key order is part of the text: a reordered object is written fresh.
    return ka.length === kb.length && ka.every((k, i) => k === kb[i] && deepEqual(a[k], b[k]))
  }
  return false
}

/** One-line JSON in the commons' spacing: `{"a": 1, "b": [1, 2]}`. */
function inline(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map((v) => inline(v === undefined ? null : v)).join(', ')}]`
  if (isObject(value)) {
    const entries = Object.entries(value).filter(([, v]) => v !== undefined)
    return `{${entries.map(([k, v]) => `${JSON.stringify(k)}: ${inline(v)}`).join(', ')}}`
  }
  return JSON.stringify(value) ?? 'null'
}

interface Style {
  /** Write new containers on one line. */
  oneLine: boolean
  /** Indentation of the line the value starts on. */
  indent: string
  /** One level of indentation in this document. */
  unit: string
}

function fresh(value: unknown, style: Style): string {
  if (style.oneLine || (!Array.isArray(value) && !isObject(value))) return inline(value)
  return JSON.stringify(value, null, style.unit).replace(/\n/g, `\n${style.indent}`)
}

/** The indentation at the end of a whitespace run (the last line's leading blanks). */
function indentOf(ws: string): string | null {
  const nl = ws.lastIndexOf('\n')
  return nl === -1 ? null : ws.slice(nl + 1)
}

/** Keep a number's spelling when only its value changed: `14.0` → `15.0`, not `15`. */
function numberLike(value: number, source: string, old: Node | undefined): string {
  const text = JSON.stringify(value)
  if (old?.kind === 'scalar' && typeof old.value === 'number' && Number.isInteger(value)
    && /^-?\d+\.0+$/.test(source.slice(old.start, old.end)) && /^-?\d+$/.test(text)) {
    return `${text}.${source.slice(old.start, old.end).split('.')[1]}`
  }
  return text
}

function write(value: unknown, old: Node | undefined, source: string, style: Style): string {
  if (old && deepEqual(value, old.value)) return source.slice(old.start, old.end)
  if (typeof value === 'number') return numberLike(value, source, old)
  const container = Array.isArray(value) ? 'array' : isObject(value) ? 'object' : null
  if (!old || container === null || old.kind !== container || old.members.length === 0) return fresh(value, style)

  const members = old.members
  const open = container === 'object' ? '{' : '['
  const close = container === 'object' ? '}' : ']'
  const multiLine = members.some((m) => m.before.includes('\n'))
  const childIndent = indentOf(members[members.length > 1 ? 1 : 0].before) ?? style.indent
  const between = members.length > 1 ? members[0].after : ''
  const closing = members[members.length - 1].after

  // Pair each new member with the source member it continues, if any.
  type Pair = { key?: string; value: unknown; old?: Member; origIndex: number }
  let pairs: Pair[]
  if (container === 'object') {
    const byKey = new Map(members.map((m, i) => [m.key as string, i]))
    pairs = Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => {
        const i = byKey.get(k)
        return { key: k, value: v, old: i === undefined ? undefined : members[i], origIndex: i ?? -1 }
      })
  } else {
    const ids = members.map((m) => (isObject(m.node.value) && typeof m.node.value.id === 'string' ? m.node.value.id : null))
    const byId = ids.every((id) => id !== null) ? new Map(ids.map((id, i) => [id as string, i])) : null
    pairs = (value as unknown[]).map((v, i) => {
      const id = isObject(v) && typeof v.id === 'string' ? v.id : null
      const j = byId ? (id === null ? undefined : byId.get(id)) : (i < members.length ? i : undefined)
      return { value: v === undefined ? null : v, old: j === undefined ? undefined : members[j], origIndex: j ?? -1 }
    })
  }
  if (pairs.length === 0) return `${open}${old.inner || ''}${close}`

  // A new member looks like a neighbour: same key spacing, same one-line-or-not.
  const keySep = /:\s*$/.exec(members.find((m) => m.keyText)?.keyText ?? '": ')?.[0] ?? ': '
  const styleFor = (v: unknown, neighbour: Member | undefined): Style => {
    const kind = (x: unknown) => (Array.isArray(x) ? 'array' : isObject(x) ? 'object' : 'scalar')
    const like = members.find((m) => kind(m.node.value) === kind(v) && kind(v) !== 'scalar') ?? neighbour
    const sample = like ? source.slice(like.node.start, like.node.end) : ''
    return {
      oneLine: like ? !sample.includes('\n') : !multiLine,
      indent: multiLine ? childIndent : style.indent,
      unit: style.unit,
    }
  }

  const parts: string[] = []
  pairs.forEach((pair, i) => {
    const neighbour = pair.old ?? members[Math.min(i, members.length - 1)]
    const before = pair.old && pair.origIndex === i
      ? pair.old.before
      : i === 0 ? members[0].before : (members[1] ?? members[0]).before
    const childStyle = pair.old
      ? { oneLine: !source.slice(pair.old.node.start, pair.old.node.end).includes('\n'), indent: childIndent, unit: style.unit }
      : styleFor(pair.value, neighbour)
    const keyText = container === 'object'
      ? (pair.old?.keyText ?? `${JSON.stringify(pair.key)}${keySep}`)
      : ''
    const body = write(pair.value, pair.old?.node, source, childStyle)
    const after = i === pairs.length - 1 ? closing : between
    parts.push(`${before}${keyText}${body}${after}`)
  })
  return `${open}${parts.join(',')}${close}`
}

/** The indentation unit a document uses (two spaces when it cannot tell). */
function detectUnit(source: string): string {
  const m = /\n([ \t]+)\S/.exec(source)
  return m ? m[1] : '  '
}

/**
 * Write `value` as JSON text, keeping `source`'s layout and number spelling
 * wherever the value is unchanged. Without a usable source, two-space JSON.
 */
export function formatLike(value: unknown, source: string | null | undefined): string {
  if (typeof source !== 'string' || source.trim() === '') return `${JSON.stringify(value, null, 2)}\n`
  let root: Node
  try {
    root = parseSpans(source)
  } catch {
    return `${JSON.stringify(value, null, 2)}\n`
  }
  if (deepEqual(value, root.value)) return source
  const lead = source.slice(0, root.start)
  const trail = source.slice(root.end)
  return `${lead}${write(value, root, source, { oneLine: false, indent: '', unit: detectUnit(source) })}${trail}`
}
