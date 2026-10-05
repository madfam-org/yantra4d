/**
 * What to tell the author when the code editor could not save a file.
 *
 * The server refuses writes to a cartridge the caller may not write
 * (`read_only_cartridge`: a commons cartridge; `not_cartridge_owner`: another
 * account's fork or import), answers 409 on a conflict, and 5xx when it failed
 * itself. Each gets a sentence in the user's language; a 5xx never shows the
 * server's own text, which can carry internal detail. Anything else (a 400 from
 * the transpiler, say) shows the server's message, which says what to fix.
 */
type Translate = (key: string, params?: Record<string, string | number>) => string

export interface SaveFailure {
  message: string
  /** True when forking is how the author gets a copy they can save. */
  forkable: boolean
}

export function editorSaveFailure(error: unknown, t: Translate): SaveFailure {
  const e = (error ?? {}) as { status?: unknown; code?: unknown; message?: unknown }
  const status = typeof e.status === 'number' ? e.status : null
  const code = typeof e.code === 'string' ? e.code : null
  if (code === 'read_only_cartridge') return { message: t('editor.save_refused_read_only'), forkable: true }
  if (code === 'not_cartridge_owner') return { message: t('editor.save_refused_not_owner'), forkable: true }
  if (status === 409) return { message: t('editor.save_conflict'), forkable: false }
  if (status !== null && status >= 500) return { message: t('editor.save_server_error'), forkable: false }
  const text = typeof e.message === 'string' && e.message ? e.message : null
  return { message: text ? t('editor.save_failed_reason', { reason: text }) : t('editor.save_failed'), forkable: false }
}
