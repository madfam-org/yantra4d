import { describe, it, expect } from 'vitest'
import { getTranslations, getLangFromUrl } from './i18n'
import type { Locale } from './i18n'

describe('i18n', () => {
  describe('getTranslations', () => {
    it('returns English translations for "en"', () => {
      const t = getTranslations('en')
      expect(t).toBeDefined()
      expect(t.nav).toBeDefined()
      expect(typeof t.nav.gallery).toBe('string')
    })

    it('returns Spanish translations for "es"', () => {
      const t = getTranslations('es')
      expect(t).toBeDefined()
      expect(t.nav).toBeDefined()
    })

    it('defaults to Spanish for unknown locale', () => {
      const t = getTranslations('xx' as Locale)
      const es = getTranslations('es')
      expect(t).toEqual(es)
    })

    it('Spanish and English have the same top-level keys', () => {
      const en = getTranslations('en')
      const es = getTranslations('es')
      expect(Object.keys(en).sort()).toEqual(Object.keys(es).sort())
    })

    it('translations contain required navigation keys', () => {
      const t = getTranslations('en')
      expect(t.nav.gallery).toBeDefined()
      expect(t.nav.forMakers).toBeDefined()
      expect(t.nav.forCreators).toBeDefined()
    })
  })

  describe('getLangFromUrl', () => {
    it('returns "en" for English paths', () => {
      expect(getLangFromUrl(new URL('https://4d.madfam.io/en/'))).toBe('en')
      expect(getLangFromUrl(new URL('https://4d.madfam.io/en/concepts/'))).toBe('en')
    })

    it('returns "es" for Spanish paths', () => {
      expect(getLangFromUrl(new URL('https://4d.madfam.io/es/'))).toBe('es')
    })

    it('returns "es" as default for root path', () => {
      expect(getLangFromUrl(new URL('https://4d.madfam.io/'))).toBe('es')
    })

    it('returns "es" for unknown language prefixes', () => {
      expect(getLangFromUrl(new URL('https://4d.madfam.io/fr/'))).toBe('es')
    })
  })
})
