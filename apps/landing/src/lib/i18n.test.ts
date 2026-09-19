import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { join, resolve } from 'node:path'
import {
  PLANNED_LOCALES,
  SUPPORTED_LOCALES,
  getTranslations,
  getLangFromUrl,
  isSupportedLocale,
  localizedPath,
} from './i18n'
import type { Locale } from './i18n'

const LOCALES_DIR = resolve(__dirname, '..', 'locales')

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
      expect(getLangFromUrl(new URL('https://yantra4d.com/en/'))).toBe('en')
      expect(getLangFromUrl(new URL('https://yantra4d.com/en/concepts/'))).toBe('en')
    })

    it('returns "es" for Spanish paths', () => {
      expect(getLangFromUrl(new URL('https://yantra4d.com/es/'))).toBe('es')
    })

    it('returns "es" as default for root path', () => {
      expect(getLangFromUrl(new URL('https://yantra4d.com/'))).toBe('es')
    })

    it('returns "es" for unknown language prefixes', () => {
      expect(getLangFromUrl(new URL('https://yantra4d.com/fr/'))).toBe('es')
    })
  })

  describe('locale roster (RFC 0039 G-P scaffolding)', () => {
    it('serves es and en, and knows fr and pt are planned, not served', () => {
      expect([...SUPPORTED_LOCALES]).toEqual(['es', 'en'])
      expect([...PLANNED_LOCALES]).toEqual(['fr', 'pt'])
      expect(isSupportedLocale('en')).toBe(true)
      expect(isSupportedLocale('fr')).toBe(false)
      expect(isSupportedLocale(undefined)).toBe(false)
    })

    it('maps a path into another locale, Spanish unprefixed', () => {
      expect(localizedPath('/en/concepts/commons/', 'es')).toBe('/concepts/commons/')
      expect(localizedPath('/concepts/commons/', 'en')).toBe('/en/concepts/commons/')
      expect(localizedPath('/en/', 'es')).toBe('/')
      expect(localizedPath('/', 'en')).toBe('/en/')
      expect(localizedPath('/fr/x', 'en')).toBe('/en/x')
    })

    it('every locale file on disk has exactly the same key tree (deep parity)', () => {
      const files = readdirSync(LOCALES_DIR).filter((f) => /^[a-z]{2}\.json$/.test(f))
      expect(files.length).toBeGreaterThanOrEqual(2)
      const leaves = (value: unknown, prefix = ''): string[] =>
        value && typeof value === 'object' && !Array.isArray(value)
          ? Object.entries(value as Record<string, unknown>).flatMap(([k, v]) => leaves(v, prefix ? `${prefix}.${k}` : k))
          : [prefix]
      const trees = files.map((f) => ({ f, keys: leaves(JSON.parse(readFileSync(join(LOCALES_DIR, f), 'utf8'))).sort() }))
      for (const { f, keys } of trees.slice(1)) {
        expect(keys, `${f} diverges from ${trees[0].f}`).toEqual(trees[0].keys)
      }
    })
  })

  describe('pricing section strings', () => {
    // The #pricing anchor is the destination of every upsell CTA in the
    // studio; its copy must exist in both locales and state the tier facts.
    it('exists in both locales with matching keys', () => {
      const en = getTranslations('en') as Record<string, unknown>
      const es = getTranslations('es') as Record<string, unknown>
      expect(en.pricing).toBeDefined()
      expect(es.pricing).toBeDefined()
      expect(Object.keys(en.pricing as object).sort()).toEqual(
        Object.keys(es.pricing as object).sort()
      )
    })

    it('pro pricing carries the product price copy', () => {
      const en = getTranslations('en') as { pricing: { pro: { price: string } } }
      expect(en.pricing.pro.price).toContain('$9')
    })
  })

  describe('"why hyperobjects" copy', () => {
    // The word is the product's central claim; the landing must carry the
    // explanation in both locales or half the audience gets an unglossed term.
    it('exists in both locales with matching keys', () => {
      const en = getTranslations('en')
      const es = getTranslations('es')
      expect(Object.keys(en.hyperCommons).sort()).toEqual(
        Object.keys(es.hyperCommons).sort()
      )
      for (const key of ['whyHeading', 'whyBody', 'whyLink', 'whyLinkTarget'] as const) {
        expect(typeof en.hyperCommons[key]).toBe('string')
        expect(typeof es.hyperCommons[key]).toBe('string')
      }
    })

    it('keeps both halves of the borrowed word', () => {
      const en = getTranslations('en')
      const es = getTranslations('es')
      expect(en.hyperCommons.whyBody).toContain('Timothy Morton')
      expect(es.hyperCommons.whyBody).toContain('Timothy Morton')
      expect(en.hyperCommons.whyBody).toContain('hypertext')
      expect(es.hyperCommons.whyBody).toContain('hipertexto')
    })

    it('is not left in English on the Spanish side', () => {
      const es = getTranslations('es')
      expect(es.hyperCommons.whyHeading).not.toBe('Why hyperobjects')
      expect(es.hyperCommons.whyBody).not.toContain('on your desk')
    })
  })
})

