import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { STUDIO_LABEL_FONT } from './studioFonts'

const STUDIO = join(__dirname, '..', '..')

describe('drei <Text> fonts are served from this origin (CSP connect-src self)', () => {
  it('the label font exists under public/ and is a WOFF file', () => {
    const path = join(STUDIO, 'public', STUDIO_LABEL_FONT)
    expect(existsSync(path), `${STUDIO_LABEL_FONT} missing`).toBe(true)
    expect(readFileSync(path).subarray(0, 4).toString('latin1')).toBe('wOFF')
  })

  it('every <Text> in src passes an explicit font (no runtime font resolution)', () => {
    const offenders: string[] = []
    const walk = (dir: string) => {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const p = join(dir, entry.name)
        if (entry.isDirectory()) walk(p)
        else if (/\.(tsx|jsx)$/.test(entry.name)) {
          const src = readFileSync(p, 'utf8')
          if (!/from '@react-three\/drei'/.test(src) || !/\bText\b/.test(src)) continue
          for (const m of src.matchAll(/<Text\b[^>]*>/gs)) if (!/\bfont=/.test(m[0])) offenders.push(`${p}: ${m[0].slice(0, 60)}`)
        }
      }
    }
    walk(join(STUDIO, 'src'))
    expect(offenders).toEqual([])
  })
})
