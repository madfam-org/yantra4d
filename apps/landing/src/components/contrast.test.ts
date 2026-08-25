/**
 * WCAG contrast regression lock for accent-coloured text on the landing.
 *
 * Background: the dark theme's `--primary` is accent blue (221 83% 53%). It
 * measures 3.83:1 against `--background`/`--card` and as little as 3.60:1 on
 * the tinted surfaces the landing paints (bg-primary/10, bg-secondary/30).
 * That clears the 3.0:1 floor for non-text and large text, but NOT the 4.5:1
 * floor for small text. An audit found 11 instances of small accent text
 * below the floor, including OpenSCAD sample numerals coloured `text-accent`
 * — a *surface* token — which measured 1.34:1 and were effectively invisible.
 *
 * Two layers of protection live here:
 *   1. Token math, computed from packages/tokens/colors.css at run time, so
 *      moving a token value fails the suite rather than silently regressing.
 *   2. Class assertions on the specific elements that were fixed, so an edit
 *      cannot quietly reintroduce `text-primary` on small copy.
 */
import { describe, it, expect, beforeAll } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const COMPONENTS_DIR = resolve(__dirname, '.')
const TOKENS = resolve(__dirname, '../../../../packages/tokens/colors.css')

function loadTemplate(filename: string): string {
  const src = readFileSync(resolve(COMPONENTS_DIR, filename), 'utf-8')
  const parts = src.split('---')
  return parts.length >= 3 ? parts.slice(2).join('---') : src
}

/**
 * Every `class="..."` value in a template. Assertions about styling must run
 * against these rather than the raw source, because the contrast fixes are
 * accompanied by comments that quote the offending class names on purpose.
 */
function classAttrs(html: string): string[] {
  return [...html.matchAll(/class="([^"]*)"/g)].map((m) => m[1])
}

// ─── Token parsing + colour maths ───────────────────────────────────────────

type HSL = [number, number, number]

function parseTheme(css: string, selector: string): Record<string, HSL> {
  const start = css.indexOf(`${selector} {`)
  if (start === -1) throw new Error(`selector ${selector} not found in tokens`)
  const open = css.indexOf('{', start)
  const close = css.indexOf('}', open)
  const body = css.slice(open + 1, close)
  const vars: Record<string, HSL> = {}
  for (const m of body.matchAll(
    /--([a-z0-9-]+):\s*([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\s*;/gi
  )) {
    vars[m[1]] = [Number(m[2]), Number(m[3]), Number(m[4])]
  }
  return vars
}

function hslToRgb([h, s, l]: HSL): number[] {
  const S = s / 100
  const L = l / 100
  const c = (1 - Math.abs(2 * L - 1)) * S
  const hp = ((((h % 360) + 360) % 360) / 60)
  const x = c * (1 - Math.abs((hp % 2) - 1))
  let rgb: number[]
  if (hp < 1) rgb = [c, x, 0]
  else if (hp < 2) rgb = [x, c, 0]
  else if (hp < 3) rgb = [0, c, x]
  else if (hp < 4) rgb = [0, x, c]
  else if (hp < 5) rgb = [x, 0, c]
  else rgb = [c, 0, x]
  const m = L - c / 2
  return rgb.map((v) => (v + m) * 255)
}

/** Source-over compositing, e.g. `bg-primary/10` over `bg-background`. */
function composite(fg: number[], alpha: number, bg: number[]): number[] {
  return fg.map((c, i) => c * alpha + bg[i] * (1 - alpha))
}

function relLuminance(rgb: number[]): number {
  const [r, g, b] = rgb.map((v) => {
    const s = v / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast(a: number[], b: number[]): number {
  const la = relLuminance(a)
  const lb = relLuminance(b)
  const [hi, lo] = la > lb ? [la, lb] : [lb, la]
  return (hi + 0.05) / (lo + 0.05)
}

const SMALL_TEXT_FLOOR = 4.5
const LARGE_TEXT_FLOOR = 3.0

describe('token contrast (packages/tokens/colors.css)', () => {
  let themes: Record<'light' | 'dark', Record<string, HSL>>

  beforeAll(() => {
    const css = readFileSync(TOKENS, 'utf-8')
    themes = {
      light: parseTheme(css, ':root'),
      dark: parseTheme(css, '.dark'),
    }
  })

  /** Surfaces the landing actually composes accent text on top of. */
  function surfaces(vars: Record<string, HSL>): Record<string, number[]> {
    const bg = hslToRgb(vars.background)
    return {
      background: bg,
      card: hslToRgb(vars.card),
      'card/50': composite(hslToRgb(vars.card), 0.5, bg),
      'primary/5': composite(hslToRgb(vars.primary), 0.05, bg),
      'primary/10': composite(hslToRgb(vars.primary), 0.1, bg),
      'secondary/30': composite(hslToRgb(vars.secondary), 0.3, bg),
    }
  }

  it('defines --primary-readable in both themes', () => {
    expect(themes.light['primary-readable']).toBeDefined()
    expect(themes.dark['primary-readable']).toBeDefined()
  })

  it('keeps --primary-readable on the brand hue and saturation', () => {
    // The token exists to stay readable *without* abandoning the accent
    // identity — it must remain the same blue as --primary in the dark theme.
    const brand = themes.dark.primary
    for (const theme of ['light', 'dark'] as const) {
      const readable = themes[theme]['primary-readable']
      expect(readable[0]).toBe(brand[0]) // hue
      expect(readable[1]).toBe(brand[1]) // saturation
    }
  })

  it('clears the 4.5:1 small-text floor on every landing surface, both themes', () => {
    for (const theme of ['light', 'dark'] as const) {
      const vars = themes[theme]
      const fg = hslToRgb(vars['primary-readable'])
      for (const [name, surface] of Object.entries(surfaces(vars))) {
        const ratio = contrast(fg, surface)
        expect(
          ratio,
          `--primary-readable on ${name} (${theme}) = ${ratio.toFixed(2)}:1`
        ).toBeGreaterThanOrEqual(SMALL_TEXT_FLOOR)
      }
    }
  })

  it('documents why --primary itself is unfit for small text', () => {
    // This is the finding the audit is locking in. If --primary is ever
    // lightened enough to pass on its own, this test fails loudly and the
    // readable-token indirection can be revisited deliberately.
    const vars = themes.dark
    const fg = hslToRgb(vars.primary)
    const ratio = contrast(fg, surfaces(vars)['card/50'])
    expect(ratio).toBeLessThan(SMALL_TEXT_FLOOR)
    expect(ratio).toBeGreaterThanOrEqual(LARGE_TEXT_FLOOR)
  })

  it('keeps --accent a surface token, never a text colour', () => {
    // `text-accent` on a card measured 1.34:1 dark / 1.10:1 light. This
    // asserts the *reason*: --accent is near-identical to the card it sits
    // on, so it must never be used as a foreground.
    for (const theme of ['light', 'dark'] as const) {
      const vars = themes[theme]
      const ratio = contrast(hslToRgb(vars.accent), hslToRgb(vars.card))
      expect(ratio).toBeLessThan(LARGE_TEXT_FLOOR)
    }
  })
})

describe('accent text never uses text-primary on small copy', () => {
  it('BeforeAfter code sample uses readable tokens, not text-accent', () => {
    const html = loadTemplate('BeforeAfter.astro')
    const pre = html.slice(html.indexOf('<pre'), html.indexOf('</pre>'))
    // --accent is a surface token; as a foreground it is invisible.
    expect(pre).not.toContain('text-accent')
    // Keywords keep the accent identity via the readable variant.
    expect(pre).toContain('text-primary-readable')
    // and no bare text-primary remains on this 14px code.
    expect(pre).not.toMatch(/text-primary(?!-readable|-foreground)/)
  })

  it('Hero badge and studio link use the readable accent', () => {
    const html = loadTemplate('Hero.astro')
    const badge = html.slice(html.indexOf('bg-primary/10'))
    expect(badge.slice(0, 300)).toContain('text-primary-readable')
    expect(html).toContain('hover:text-primary-readable')
    // Scan class attributes only — prose in the explanatory comments above
    // these elements legitimately mentions the old `hover:text-primary`.
    for (const attr of classAttrs(html)) {
      expect(attr).not.toMatch(/hover:text-primary(?!-readable)/)
    }
  })

  it('HowItWorks track labels use the readable accent', () => {
    const html = loadTemplate('HowItWorks.astro')
    // Both 18px bold labels — under the 18.66px large-text threshold.
    const labels = html.match(/text-lg font-semibold text-primary[a-z-]*/g)
    expect(labels).not.toBeNull()
    expect(labels!.length).toBe(2)
    for (const label of labels!) {
      expect(label).toContain('text-primary-readable')
    }
  })

  it('HyperCommons eyebrow, caption and shift heading use the readable accent', () => {
    const html = loadTemplate('HyperCommons.astro')
    for (const anchor of ['Open Commons', 'whatIsCaption2', 'shiftTo']) {
      const i = html.indexOf(anchor)
      expect(i, `anchor ${anchor} not found`).toBeGreaterThan(-1)
      // Walk back to the opening tag of the element carrying the class.
      const tagStart = html.lastIndexOf('<', i)
      const openTag = html.slice(html.lastIndexOf('<', tagStart - 1), i)
      if (/text-primary/.test(openTag)) {
        expect(openTag, `${anchor} keeps a bare text-primary`).toContain(
          'text-primary-readable'
        )
      }
    }
    // Belt and braces, over class attributes only: the small-copy elements
    // must not carry a bare `text-primary`.
    const attrs = classAttrs(html)
    const smallCopy = attrs.filter(
      (a) => /\btext-xs\b/.test(a) || /\btext-lg\b/.test(a)
    )
    for (const a of smallCopy) {
      // The one permitted exception is the decorative ⚡ glyph, which is
      // redundant with the heading beside it (see the `decor` classification
      // in the audit) and so carries no information at any contrast.
      if (a.includes('h-10 w-10') && a.includes('bg-primary/10')) continue
      expect(a, `small-copy class kept a bare text-primary: ${a}`).not.toMatch(
        /\btext-primary\b(?!-)/
      )
    }
  })

  it('leaves the decorative ⚡ glyph on plain --primary, by design', () => {
    // Pinned deliberately: this emoji is purely ornamental and duplicated by
    // the adjacent ".SCAD Paramétrico" heading, so no contrast floor applies.
    // If it ever becomes the sole carrier of meaning, this test should be
    // deleted and the glyph moved to --primary-readable.
    const html = loadTemplate('HyperCommons.astro')
    const glyph = classAttrs(html).find(
      (a) => a.includes('h-10 w-10') && a.includes('bg-primary/10')
    )
    expect(glyph).toBeDefined()
    expect(glyph).toContain('text-primary')
  })

  it('the impact stats keep plain --primary (they qualify as large text)', () => {
    // 20px bold at the mobile breakpoint, 24px above it — both clear the
    // 18.66px-bold large-text threshold, where the 3.0:1 floor applies and
    // --primary passes at 3.83:1. Documented so nobody "fixes" them.
    const html = loadTemplate('HyperCommons.astro')
    const stats = html.match(/text-xl sm:text-2xl font-bold text-primary\b/g)
    expect(stats).not.toBeNull()
    expect(stats!.length).toBe(4)
  })

  it('ProjectGalleryGrid open label uses the readable accent', () => {
    const src = readFileSync(
      resolve(COMPONENTS_DIR, 'ProjectGalleryGrid.tsx'),
      'utf-8'
    )
    expect(src).toContain('text-xs text-primary-readable')
    expect(src).not.toMatch(/text-xs text-primary\b(?!-)/)
  })
})
