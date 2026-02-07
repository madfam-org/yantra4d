/**
 * Shared project slug validation and sanitization utilities.
 */

const SLUG_RE = /^[a-z0-9][a-z0-9_-]{1,48}[a-z0-9]$/

/**
 * Validate a project slug. Returns error string or null if valid.
 */
export function validateSlug(slug) {
  if (!slug) return 'Slug is required'
  if (!SLUG_RE.test(slug)) return 'Must be 3-50 lowercase alphanumeric characters, hyphens, or underscores'
  return null
}

/**
 * Sanitize a string into a valid slug.
 */
export function sanitizeSlug(input) {
  return input
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 50)
}
