/**
 * Display labels for catalog facet values.
 *
 * The catalog API answers facet values as stable codes (`household`,
 * `bolt_pattern`, `intermediate`, `cadquery`, `tolerance_by_material`), which
 * are also what the filter query sends back, so they must stay codes on the
 * wire. Showing them verbatim put English identifiers in every locale's
 * filter chips. Each coded facet has a key family in the locale files:
 *
 *   domain        -> projects.filter.domain.<value>
 *   geometry_type -> projects.filter.geometry.<value>
 *   difficulty    -> projects.filter.difficulty.<value>
 *   engine        -> projects.filter.engine.<value>
 *   material      -> projects.filter.material.<value>
 *
 * `standard` values are free text the cartridge author wrote (`ISO 7045 M3`,
 * `NEMA 17/23`), not codes, and are shown as written. A code with no key yet
 * (a domain added to the vocabulary before the locales) falls back to the code
 * itself rather than to the raw key string.
 */

export type Translate = (key: string, params?: Record<string, string | number>) => string

const KEY_PREFIX: Record<string, string> = {
  domain: 'projects.filter.domain.',
  geometry_type: 'projects.filter.geometry.',
  difficulty: 'projects.filter.difficulty.',
  engine: 'projects.filter.engine.',
  material: 'projects.filter.material.',
}

export function facetValueLabel(facet: string, value: string, t: Translate): string {
  const prefix = KEY_PREFIX[facet]
  if (!prefix || !value) return value
  const key = `${prefix}${value}`
  const label = t(key)
  return label && label !== key ? label : value
}
