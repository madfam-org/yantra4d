/**
 * Monaco inline diff decorations for AI code edits.
 */

interface MonacoPosition {
  lineNumber: number
  column: number
}

interface MonacoRange {
  startLineNumber: number
  startColumn: number
  endLineNumber: number
  endColumn: number
}

interface MonacoModel {
  getValue(): string
  getPositionAt(offset: number): MonacoPosition
  getWordUntilPosition(position: MonacoPosition): { startColumn: number; endColumn: number }
}

interface MonacoEditor {
  getModel(): MonacoModel | null
  deltaDecorations(oldDecorations: string[], newDecorations: MonacoDecoration[]): string[]
  executeEdits(source: string, edits: MonacoEditOperation[]): void
}

interface MonacoDecoration {
  range: MonacoRange
  options: {
    inlineClassName?: string
    stickiness?: number
  }
}

interface MonacoEditOperation {
  range: MonacoRange
  text: string
}

interface MonacoNamespace {
  Range: new (startLine: number, startCol: number, endLine: number, endCol: number) => MonacoRange
  editor: {
    TrackedRangeStickiness: {
      NeverGrowsWhenTypingAtEdges: number
    }
  }
}

interface CodeEdit {
  file: string
  search: string
  replace: string
}

/**
 * Highlight pending edits in the editor with inline decorations.
 */
export function highlightEdits(editor: MonacoEditor, monaco: MonacoNamespace, edits: CodeEdit[]): string[] {
  const model = editor.getModel()
  if (!model) return []

  const decorations: MonacoDecoration[] = []

  for (const edit of edits) {
    const content = model.getValue()
    const idx = content.indexOf(edit.search)
    if (idx === -1) continue

    const startPos = model.getPositionAt(idx)
    const endPos = model.getPositionAt(idx + edit.search.length)

    // Red strikethrough for old text
    decorations.push({
      range: new monaco.Range(startPos.lineNumber, startPos.column, endPos.lineNumber, endPos.column),
      options: {
        inlineClassName: 'ai-edit-remove',
        stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
      },
    })
  }

  return editor.deltaDecorations([], decorations)
}

/**
 * Apply a single search/replace edit to the editor.
 */
export function acceptEdit(editor: MonacoEditor, edit: { search: string; replace: string }): void {
  const model = editor.getModel()
  if (!model) return

  const content = model.getValue()
  const idx = content.indexOf(edit.search)
  if (idx === -1) return

  const startPos = model.getPositionAt(idx)
  const endPos = model.getPositionAt(idx + edit.search.length)

  editor.executeEdits('ai-edit', [{
    range: {
      startLineNumber: startPos.lineNumber,
      startColumn: startPos.column,
      endLineNumber: endPos.lineNumber,
      endColumn: endPos.column,
    },
    text: edit.replace,
  }])
}

/**
 * Remove decorations without changing text.
 */
export function rejectEdit(editor: MonacoEditor, decorationIds: string[]): void {
  editor.deltaDecorations(decorationIds, [])
}
