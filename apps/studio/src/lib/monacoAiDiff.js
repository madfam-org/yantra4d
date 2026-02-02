/**
 * Monaco inline diff decorations for AI code edits.
 */

/**
 * Highlight pending edits in the editor with inline decorations.
 * @param {object} editor - Monaco editor instance
 * @param {object} monaco - Monaco namespace
 * @param {Array<{file: string, search: string, replace: string}>} edits
 * @returns {string[]} decoration IDs
 */
export function highlightEdits(editor, monaco, edits) {
  const model = editor.getModel()
  if (!model) return []

  const decorations = []

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
 * @param {object} editor - Monaco editor instance
 * @param {{search: string, replace: string}} edit
 */
export function acceptEdit(editor, edit) {
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
 * @param {object} editor - Monaco editor instance
 * @param {string[]} decorationIds
 */
export function rejectEdit(editor, decorationIds) {
  editor.deltaDecorations(decorationIds, [])
}
