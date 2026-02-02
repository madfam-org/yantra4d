import { describe, it, expect, vi } from 'vitest'
import { highlightEdits, acceptEdit, rejectEdit } from './monacoAiDiff'

function createMockEditor(content) {
  const model = {
    getValue: () => content,
    getPositionAt: (offset) => {
      const lines = content.substring(0, offset).split('\n')
      return { lineNumber: lines.length, column: lines[lines.length - 1].length + 1 }
    },
  }
  return {
    getModel: () => model,
    deltaDecorations: vi.fn(() => ['dec-1', 'dec-2']),
    executeEdits: vi.fn(),
  }
}

function createMockMonaco() {
  return {
    Range: class {
      constructor(sl, sc, el, ec) {
        this.startLineNumber = sl
        this.startColumn = sc
        this.endLineNumber = el
        this.endColumn = ec
      }
    },
    editor: {
      TrackedRangeStickiness: { NeverGrowsWhenTypingAtEdges: 1 },
    },
  }
}

describe('highlightEdits', () => {
  it('creates decorations for matching edits', () => {
    const editor = createMockEditor('cube(10);\nsphere(5);')
    const monaco = createMockMonaco()
    const ids = highlightEdits(editor, monaco, [
      { file: 'x.scad', search: 'sphere(5);', replace: 'sphere(10);' },
    ])
    expect(editor.deltaDecorations).toHaveBeenCalledWith([], expect.any(Array))
    expect(ids).toEqual(['dec-1', 'dec-2'])
  })

  it('skips edits with no match in content', () => {
    const editor = createMockEditor('cube(10);')
    const monaco = createMockMonaco()
    highlightEdits(editor, monaco, [
      { file: 'x.scad', search: 'not_found', replace: 'y' },
    ])
    expect(editor.deltaDecorations).toHaveBeenCalledWith([], [])
  })

  it('returns empty when no model', () => {
    const editor = { getModel: () => null }
    const ids = highlightEdits(editor, {}, [])
    expect(ids).toEqual([])
  })
})

describe('acceptEdit', () => {
  it('calls executeEdits with replacement', () => {
    const editor = createMockEditor('cube(10);')
    acceptEdit(editor, { search: 'cube(10);', replace: 'cube(20);' })
    expect(editor.executeEdits).toHaveBeenCalledWith('ai-edit', [
      expect.objectContaining({ text: 'cube(20);' }),
    ])
  })

  it('does nothing if search not found', () => {
    const editor = createMockEditor('cube(10);')
    acceptEdit(editor, { search: 'not_found', replace: 'y' })
    expect(editor.executeEdits).not.toHaveBeenCalled()
  })
})

describe('rejectEdit', () => {
  it('removes decorations', () => {
    const editor = { deltaDecorations: vi.fn() }
    rejectEdit(editor, ['dec-1'])
    expect(editor.deltaDecorations).toHaveBeenCalledWith(['dec-1'], [])
  })
})
