import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { facetValueLabel } from './facetLabels'
import en from '../locales/en.json'
import es from '../locales/es.json'
import pt from '../locales/pt.json'
import fr from '../locales/fr.json'
import de from '../locales/de.json'
import zh from '../locales/zh.json'

const LOCALES: Record<string, Record<string, string>> = { en, es, pt, fr, de, zh }
const tFor = (locale: Record<string, string>) => (key: string) => locale[key] ?? key

// The vocabularies the manifest schema allows; the catalog facets carry exactly
// these codes (domain, geometry_type, difficulty, engine).
const schema = JSON.parse(
  readFileSync(join(__dirname, '..', '..', '..', '..', 'packages', 'schemas', 'project-manifest.schema.json'), 'utf8'),
)
const VOCAB: Record<string, string[]> = {
  domain: schema.properties.hyperobject.properties.domain.enum,
  geometry_type: schema.properties.hyperobject.properties.cdg_interfaces.items.properties.geometry_type.enum,
  difficulty: schema.properties.project.properties.difficulty.enum,
  engine: schema.properties.modes.items.properties.engine.enum,
}

describe('facetValueLabel', () => {
  it('localizes coded facet values', () => {
    const t = tFor(es)
    expect(facetValueLabel('domain', 'household', t)).toBe('Hogar')
    expect(facetValueLabel('geometry_type', 'bolt_pattern', t)).toBe('Patrón de pernos')
    expect(facetValueLabel('difficulty', 'intermediate', t)).toBe('Intermedio')
    expect(facetValueLabel('engine', 'cadquery', t)).toBe('CadQuery')
    expect(facetValueLabel('material', 'tolerance_by_material', t)).toBe('Adapta tolerancias al material')
  })

  it('shows author-written standards as written', () => {
    expect(facetValueLabel('standard', 'ISO 7045 M3', tFor(es))).toBe('ISO 7045 M3')
  })

  it('falls back to the code, never the raw key, for a value with no translation', () => {
    expect(facetValueLabel('domain', 'aerospace', tFor(es))).toBe('aerospace')
    expect(facetValueLabel('geometry_type', '', tFor(es))).toBe('')
  })

  const KEY_FAMILY: Record<string, string> = {
    domain: 'projects.filter.domain.',
    geometry_type: 'projects.filter.geometry.',
    difficulty: 'projects.filter.difficulty.',
    engine: 'projects.filter.engine.',
  }
  for (const [facet, values] of Object.entries(VOCAB)) {
    it(`has a key for every schema ${facet} value in all six locales`, () => {
      expect(values.length).toBeGreaterThan(0)
      for (const [lang, locale] of Object.entries(LOCALES)) {
        const missing = values.filter((v) => !locale[`${KEY_FAMILY[facet]}${v}`])
        expect(missing, `${lang} ${facet}`).toEqual([])
      }
    })
  }
})
