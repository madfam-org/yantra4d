/**
 * Surface check 1 of RFC 0067 G-6 for the Studio: WCAG contrast of the token
 * pairs the configurator is built from (docs/architecture/graph-generated-surfaces.md).
 *
 * The landing already locks its own pairs (apps/landing/src/components/contrast.test.ts).
 * This file does the same for the Studio's controls: text on every surface a
 * control sits on, the primary action, the slider, the focus ring, field
 * boundaries and error text. Values are read from packages/tokens/colors.css at
 * run time, so moving a token re-measures every pair.
 *
 * RECORDED_DEBT lists the pairs measured below their floor on 2026-11-20. It is
 * a ratchet, not a skip: each entry must STILL measure below its floor, so a fix
 * fails this suite until its entry is removed, and any pair that is not listed
 * must clear its floor. Do not add entries to make a new failure pass; fix the
 * token (or add a readable variant, as --primary-readable did for accent text).
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const TOKENS = resolve(__dirname, '../../../../packages/tokens/colors.css')

type HSL = [number, number, number]
type Theme = 'light' | 'dark'

function parseTheme(css: string, selector: string): Record<string, HSL> {
  const start = css.indexOf(`${selector} {`)
  if (start === -1) throw new Error(`selector ${selector} not found in tokens`)
  const open = css.indexOf('{', start)
  const body = css.slice(open + 1, css.indexOf('}', open))
  const vars: Record<string, HSL> = {}
  for (const m of body.matchAll(/--([a-z0-9-]+):\s*([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\s*;/gi)) {
    vars[m[1]] = [Number(m[2]), Number(m[3]), Number(m[4])]
  }
  return vars
}

function hslToRgb([h, s, l]: HSL): number[] {
  const S = s / 100
  const L = l / 100
  const c = (1 - Math.abs(2 * L - 1)) * S
  const hp = (((h % 360) + 360) % 360) / 60
  const x = c * (1 - Math.abs((hp % 2) - 1))
  const table = [[c, x, 0], [x, c, 0], [0, c, x], [0, x, c], [x, 0, c], [c, 0, x]]
  const m = L - c / 2
  return table[Math.min(Math.floor(hp), 5)].map((v) => (v + m) * 255)
}

function relLuminance(rgb: number[]): number {
  const [r, g, b] = rgb.map((v) => {
    const s = v / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast(a: number[], b: number[]): number {
  const [hi, lo] = [relLuminance(a), relLuminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

const TEXT = 4.5 // WCAG 1.4.3, text under 24 px (18.66 px bold)
const NON_TEXT = 3.0 // WCAG 1.4.11, component boundaries, states and focus

interface Pair {
  fg: string
  bg: string
  floor: number
  role: string
}

/** The token pairs a generated configurator surface is composed of. */
const PAIRS: Pair[] = [
  { fg: 'foreground', bg: 'background', floor: TEXT, role: 'labels and values on the page' },
  { fg: 'foreground', bg: 'card', floor: TEXT, role: 'labels in panels' },
  { fg: 'foreground', bg: 'muted', floor: TEXT, role: 'labels on quiet panels and hover fills' },
  { fg: 'muted-foreground', bg: 'background', floor: TEXT, role: 'help text and units' },
  { fg: 'muted-foreground', bg: 'card', floor: TEXT, role: 'help text and units in panels' },
  { fg: 'muted-foreground', bg: 'muted', floor: TEXT, role: 'inactive tabs on the tab rail' },
  { fg: 'primary-foreground', bg: 'primary', floor: TEXT, role: 'Generate and primary buttons' },
  { fg: 'secondary-foreground', bg: 'secondary', floor: TEXT, role: 'secondary buttons' },
  { fg: 'accent-foreground', bg: 'accent', floor: TEXT, role: 'hovered menu items' },
  { fg: 'primary-readable', bg: 'background', floor: TEXT, role: 'accent text and links' },
  { fg: 'primary-readable', bg: 'muted', floor: TEXT, role: 'accent text on quiet panels' },
  { fg: 'destructive-foreground', bg: 'destructive', floor: TEXT, role: 'destructive buttons' },
  { fg: 'destructive', bg: 'background', floor: TEXT, role: 'constraint and error messages' },
  { fg: 'destructive', bg: 'card', floor: TEXT, role: 'constraint and error messages in panels' },
  { fg: 'primary', bg: 'secondary', floor: NON_TEXT, role: 'slider range on its track' },
  { fg: 'primary', bg: 'background', floor: NON_TEXT, role: 'slider thumb ring and selected states' },
  { fg: 'ring', bg: 'background', floor: NON_TEXT, role: 'focus ring' },
  { fg: 'input', bg: 'background', floor: NON_TEXT, role: 'text field boundary' },
]

/** Measured below floor on 2026-11-20 (ratchet: see the header). */
const RECORDED_DEBT: ReadonlyArray<{ theme: Theme; fg: string; bg: string }> = [
  { theme: 'light', fg: 'destructive-foreground', bg: 'destructive' }, // 3.60
  { theme: 'light', fg: 'destructive', bg: 'background' }, // 3.76
  { theme: 'light', fg: 'destructive', bg: 'card' }, // 3.76
  { theme: 'dark', fg: 'destructive', bg: 'background' }, // 1.99
  { theme: 'dark', fg: 'destructive', bg: 'card' }, // 1.99
  { theme: 'dark', fg: 'primary', bg: 'secondary' }, // 2.86
  { theme: 'light', fg: 'input', bg: 'background' }, // 1.27
  { theme: 'dark', fg: 'input', bg: 'background' }, // 1.34
]

const css = readFileSync(TOKENS, 'utf-8')
const themes: Record<Theme, Record<string, HSL>> = {
  light: parseTheme(css, ':root'),
  dark: parseTheme(css, '.dark'),
}

function measure(theme: Theme, p: { fg: string; bg: string }): number {
  const vars = themes[theme]
  for (const token of [p.fg, p.bg]) {
    if (!vars[token]) throw new Error(`--${token} is not defined in the ${theme} theme`)
  }
  return contrast(hslToRgb(vars[p.fg]), hslToRgb(vars[p.bg]))
}

const isDebt = (theme: Theme, p: Pair) =>
  RECORDED_DEBT.some((d) => d.theme === theme && d.fg === p.fg && d.bg === p.bg)

describe('Studio token contrast (RFC 0067 G-6, check 1)', () => {
  for (const theme of ['light', 'dark'] as const) {
    describe(theme, () => {
      for (const pair of PAIRS) {
        const ratio = () => measure(theme, pair)
        if (isDebt(theme, pair)) {
          it(`${pair.fg} on ${pair.bg} (${pair.role}) is recorded debt and still below ${pair.floor}:1`, () => {
            expect(
              ratio(),
              'this pair now clears its floor: remove it from RECORDED_DEBT',
            ).toBeLessThan(pair.floor)
          })
        } else {
          it(`${pair.fg} on ${pair.bg} (${pair.role}) clears ${pair.floor}:1`, () => {
            expect(ratio()).toBeGreaterThanOrEqual(pair.floor)
          })
        }
      }
    })
  }

  it('every recorded debt entry names a measured pair', () => {
    for (const d of RECORDED_DEBT) {
      expect(PAIRS.some((p) => p.fg === d.fg && p.bg === d.bg), `${d.fg} on ${d.bg}`).toBe(true)
    }
  })
})
