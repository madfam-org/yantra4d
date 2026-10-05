import { describe, it, expect } from 'vitest'
import { editorSaveFailure } from './editorSaveMessage'

const t = (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key)

describe('editorSaveFailure', () => {
  it('names a refused write and offers the fork', () => {
    expect(editorSaveFailure({ status: 403, code: 'read_only_cartridge', message: 'x' }, t))
      .toEqual({ message: 'editor.save_refused_read_only', forkable: true })
    expect(editorSaveFailure({ status: 403, code: 'not_cartridge_owner', message: 'x' }, t))
      .toEqual({ message: 'editor.save_refused_not_owner', forkable: true })
  })

  it('says conflict on 409 and never shows a 5xx body', () => {
    expect(editorSaveFailure({ status: 409, code: 'slug_in_use', message: 'x' }, t)).toEqual({ message: 'editor.save_conflict', forkable: false })
    expect(editorSaveFailure({ status: 503, code: null, message: 'Failed to write file: /app/x' }, t))
      .toEqual({ message: 'editor.save_server_error', forkable: false })
  })

  it('passes a validation reason through, and copes with anything thrown', () => {
    expect(editorSaveFailure({ status: 400, code: 'x', message: 'bad node' }, t).message).toBe('editor.save_failed_reason:{"reason":"bad node"}')
    expect(editorSaveFailure(new Error('offline'), t).message).toBe('editor.save_failed_reason:{"reason":"offline"}')
    expect(editorSaveFailure(undefined, t)).toEqual({ message: 'editor.save_failed', forkable: false })
  })
})
