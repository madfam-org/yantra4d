/**
 * The truth lane for copy.
 *
 * On 2026-08-13 the landing said "21 Projects" against a commons of 326, and
 * on 2026-09-19 it said "324 cartridges" against 502 and "317 export STEP"
 * against 493. Numbers typed into locale strings drift; numbers bound from
 * generated data cannot. This test makes typing a figure a build failure:
 * every digit-bearing token in a locale string must be a `{placeholder}` or an
 * allow-listed technical token with a written reason
 * (`src/locales/figure-allowlist.json`). Standards, dimensions and file
 * formats are allowed; counts, prices, percentages and multipliers about the
 * product are not.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, join } from 'node:path'

const LOCALES_DIR = resolve(__dirname, '..', 'locales')
const allowlist = JSON.parse(readFileSync(join(LOCALES_DIR, 'figure-allowlist.json'), 'utf8')) as {
  tokens: Record<string, string>
  patterns: Array<{ regex: string; reason: string }>
}
const allowedTokens = new Set(Object.keys(allowlist.tokens))
const allowedPatterns = allowlist.patterns.map((p) => new RegExp(p.regex))

function* strings(value: unknown, path: string[] = []): Generator<[string, string]> {
  if (typeof value === 'string') yield [path.join('.'), value]
  else if (Array.isArray(value)) for (const [i, v] of value.entries()) yield* strings(v, [...path, String(i)])
  else if (value && typeof value === 'object') for (const [k, v] of Object.entries(value)) yield* strings(v, [...path, k])
}

/**
 * Whitespace-delimited tokens carrying a digit, with sentence punctuation
 * trimmed. A trailing straight quote right after a digit is an inch mark
 * (`6"`, `4.5"`) and stays part of the token.
 */
export function digitTokens(text: string): string[] {
  return (text.match(/\S*\d\S*/g) ?? [])
    .map((t) => t.replace(/^[(["“']+/, '').replace(/[)\].,;:!?”']+$/, ''))
    .map((t) => (/\d"$/.test(t) ? t : t.replace(/"+$/, '')))
    .filter(Boolean)
}

const localeFiles = readdirSync(LOCALES_DIR).filter((f) => /^[a-z]{2}\.json$/.test(f))

describe('locale figures are bound, not typed', () => {
  it('finds the locale files', () => {
    expect(localeFiles.length).toBeGreaterThanOrEqual(2)
  })

  it.each(localeFiles)('%s carries no unexplained figure', (file) => {
    const data = JSON.parse(readFileSync(join(LOCALES_DIR, file), 'utf8'))
    const offenders: string[] = []
    for (const [path, text] of strings(data)) {
      for (const token of digitTokens(text)) {
        if (allowedTokens.has(token)) continue
        if (allowedPatterns.some((re) => re.test(token))) continue
        offenders.push(`${path}: "${token}" in "${text.slice(0, 80)}"`)
      }
    }
    expect(offenders, `Bind these to COMMONS_STATS / TIER_FACTS or explain them in figure-allowlist.json:\n${offenders.join('\n')}`).toEqual([])
  })

  it('every allow-listed token has a reason', () => {
    for (const [token, reason] of Object.entries(allowlist.tokens)) {
      expect(typeof reason === 'string' && reason.trim().length > 3, `no reason for ${token}`).toBe(true)
    }
  })

  it('the pricing and export copy carry placeholders for their figures', () => {
    for (const file of localeFiles) {
      const data = JSON.parse(readFileSync(join(LOCALES_DIR, file), 'utf8'))
      expect(data.pricing.free.f1).toContain('{cartridges}')
      expect(data.pricing.free.f3).toContain('{guestRenders}')
      expect(data.pricing.essentials.f1).toContain('{essentialsRenders}')
      expect(data.pricing.pro.f1).toContain('{proRenders}')
      expect(data.forMakers.export.desc).toContain('{stepCapable}')
    }
  })
})

describe('generated figures exist for every placeholder the copy uses', () => {
  it('COMMONS_STATS and TIER_FACTS cover the placeholders', async () => {
    const mod = await import('../data/projects')
    const stats = mod.COMMONS_STATS as Record<string, unknown>
    const tiers = mod.TIER_FACTS as Record<string, unknown>
    for (const file of localeFiles) {
      const data = JSON.parse(readFileSync(join(LOCALES_DIR, file), 'utf8'))
      for (const [path, text] of strings(data)) {
        for (const m of text.matchAll(/\{([a-zA-Z]+)\}/g)) {
          const key = m[1]
          // Gallery UI templates are filled at runtime by the island.
          if (path.startsWith('galleryUi.')) continue
          expect(key in stats || key in tiers, `${path} uses {${key}} which no generated figure provides`).toBe(true)
        }
      }
    }
  })
})
