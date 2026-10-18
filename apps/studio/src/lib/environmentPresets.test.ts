import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import {
  DEFAULT_ENVIRONMENT_PRESET,
  ENVIRONMENT_HDRI_PATH,
  ENVIRONMENT_PRESET_FILES,
  environmentFile,
  isEnvironmentPreset,
} from './environmentPresets'

const STUDIO = join(__dirname, '..', '..')
const HDRI_DIR = join(STUDIO, 'public', 'hdri')

describe('environment presets are served from this origin (CSP connect-src self)', () => {
  it('every preset maps to a Radiance HDR file under public/hdri', () => {
    for (const [preset, file] of Object.entries(ENVIRONMENT_PRESET_FILES)) {
      const path = join(HDRI_DIR, file)
      expect(existsSync(path), `${preset} → ${file} missing`).toBe(true)
      const head = readFileSync(path).subarray(0, 10).toString('latin1')
      expect(head.startsWith('#?RADIANCE'), `${file} is not a Radiance HDR`).toBe(true)
    }
  })

  it('the served path is same-origin and absolute', () => {
    expect(ENVIRONMENT_HDRI_PATH).toBe('/hdri/')
  })

  it('unknown names fall back to the default preset', () => {
    expect(isEnvironmentPreset('city')).toBe(true)
    expect(isEnvironmentPreset('mars')).toBe(false)
    expect(environmentFile('mars')).toBe(ENVIRONMENT_PRESET_FILES[DEFAULT_ENVIRONMENT_PRESET])
    expect(environmentFile('sunset')).toBe('venice_sunset_1k.hdr')
  })

  it('no component uses <Environment preset=…> (a runtime fetch of raw.githack.com)', () => {
    const offenders: string[] = []
    const walk = (dir: string) => {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const p = join(dir, entry.name)
        if (entry.isDirectory()) walk(p)
        else if (/\.(tsx|jsx)$/.test(entry.name) && /<Environment[^>]*\bpreset=/.test(readFileSync(p, 'utf8'))) offenders.push(p)
      }
    }
    walk(join(STUDIO, 'src'))
    expect(offenders).toEqual([])
  })
})
