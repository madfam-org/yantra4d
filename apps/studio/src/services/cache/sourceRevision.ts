/**
 * Per-project source revision for the client render caches.
 *
 * The render caches key on (project, mode, params, format, server revision).
 * None of those change when a cartridge's SOURCE is edited and saved — a graph
 * save at unchanged parameters — so without this the next preview would be the
 * pre-edit parts, served from cache without a request reaching the API.
 *
 * A save bumps the project's counter; every cache key reads it at call time,
 * so an edit makes every earlier entry for that project unreachable. It lives
 * for the page session only: across a reload, the server's render revision
 * (`X-Render-Revision`) already carries a digest of a user cartridge's sources.
 */
const revisions = new Map<string, number>()

/** The current source revision of `project` (0 until its first save). */
export function sourceRevision(project: string | null | undefined): number {
  return revisions.get(project ?? '') ?? 0
}

/** Record that `project`'s sources changed; returns the new revision. */
export function bumpSourceRevision(project: string | null | undefined): number {
  const next = sourceRevision(project) + 1
  revisions.set(project ?? '', next)
  return next
}
