import { describe, it, expect } from 'vitest'
import en from '../locales/en.json'
import es from '../locales/es.json'
import pt from '../locales/pt.json'
import fr from '../locales/fr.json'
import de from '../locales/de.json'
import zh from '../locales/zh.json'

// Every Studio locale carries the prerendered-preview and engine-gate copy,
// with the same {placeholders} as English (LanguageProvider fills them).
const LOCALES = { en, es, pt, fr, de, zh }
const KEYS = {
  'preview.prerendered_label': [],
  'preview.prerendered_pin': ['{pin}'],
  'preview.params_changed': [],
  'tier.engine_cadquery': [],
  'tier.engine_graph': [],
  'tier.free_alternatives_title': [],
  'tier.free_alt_preview': [],
  'tier.free_alt_openscad_guest': ['{renders}'],
  'tier.free_alt_openscad': ['{renders}'],
  'tier.engine_gated_log': ['{engine}'],
}

describe('prerendered preview + engine gate i18n', () => {
  for (const [lang, strings] of Object.entries(LOCALES)) {
    it(`${lang} has every key, translated, with its placeholders`, () => {
      for (const [key, placeholders] of Object.entries(KEYS)) {
        expect(typeof strings[key], `${lang} ${key}`).toBe('string')
        expect(strings[key].trim(), `${lang} ${key}`).not.toBe('')
        for (const ph of placeholders) expect(strings[key], `${lang} ${key}`).toContain(ph)
      }
    })
  }

  it('says "por defecto" in Spanish, as the label the coordinator specified', () => {
    expect(es['preview.prerendered_label']).toBe('Vista prerenderizada de la configuración por defecto')
  })
})
