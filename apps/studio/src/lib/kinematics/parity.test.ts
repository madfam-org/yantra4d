/**
 * Golden parity (Phase 7, D4): the viewer's forward kinematics reproduces the keystone's
 * golden pose files, string for string.
 *
 * The goldens are NOT copied into this repo. They are read from a keystone checkout at
 * the pinned SHA (the same SHA the spec-conformance job installs), named by the
 * environment variable Y4D_KEYSTONE_DIR. CI checks the keystone out in a step before
 * vitest runs (no network inside the test). Locally:
 *
 *   Y4D_KEYSTONE_DIR=/path/to/hyperobjects-spec npm test -- src/lib/kinematics
 *
 * Without the variable this file FAILS, by design: a parity test that silently passes
 * when it has nothing to compare is no parity test.
 *
 * Comparison rule (hyperobjects.assembly-poses 1.0.0): every number is compared as its
 * canonical string, except the entries listed in `tie_guard` (within 1e-9 of a rounding
 * boundary), which are compared numerically with |Δ| ≤ 1e-6.
 */
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { compileKinematics, formatNumber, jointValues, place } from './kinematics'
import { parseKinematicModel } from './model'

/** (name, model, poses) relative to the keystone root: the three goldens it maintains. */
const FIXTURES: [string, string, string][] = [
  [
    'voron-2-4-class-350-motion-frame',
    'tests/fixtures/assembly-golden/poses/voron-2-4-class-350-motion-frame.kinematics.json',
    'tests/fixtures/assembly-golden/poses/voron-2-4-class-350-motion-frame.poses.json',
  ],
  [
    'fpv-5in-freestyle',
    'tests/fixtures/assembly-golden/poses/fpv-5in-freestyle.kinematics.json',
    'tests/fixtures/assembly-golden/poses/fpv-5in-freestyle.poses.json',
  ],
  [
    'kinematic-gantry',
    'tests/fixtures/kinematics/kinematic-gantry.kinematics.json',
    'tests/fixtures/kinematics/kinematic-gantry.poses.json',
  ],
]

interface GoldenPose {
  name: string
  kind: string
  inputs: Record<string, number>
  joints: Record<string, string>
  transforms: Record<string, string[]>
}

const ROOT = process.env.Y4D_KEYSTONE_DIR

describe('keystone golden pose parity', () => {
  it('has a keystone checkout to compare against (Y4D_KEYSTONE_DIR)', () => {
    expect(ROOT, 'set Y4D_KEYSTONE_DIR to a hyperobjects-spec checkout at the pinned SHA').toBeTruthy()
    for (const [, model, poses] of FIXTURES) {
      expect(existsSync(join(ROOT!, model)), `${model} is missing at Y4D_KEYSTONE_DIR`).toBe(true)
      expect(existsSync(join(ROOT!, poses)), `${poses} is missing at Y4D_KEYSTONE_DIR`).toBe(true)
    }
  })

  for (const [name, modelPath, posesPath] of FIXTURES) {
    it(`${name}: every joint value and every transform of every pose`, () => {
      expect(ROOT, 'Y4D_KEYSTONE_DIR is not set').toBeTruthy()
      const model = parseKinematicModel(JSON.parse(readFileSync(join(ROOT!, modelPath), 'utf8')))
      const golden = JSON.parse(readFileSync(join(ROOT!, posesPath), 'utf8'))
      expect(golden.format).toBe('hyperobjects.assembly-poses')
      expect(golden.format_version.split('.')[0]).toBe('1')
      expect(model.assembly_digest).toBe(golden.assembly_digest)
      const guard = new Set<string>(golden.tie_guard)
      const k = compileKinematics(model)
      expect(k.unreached).toEqual([])
      let strings = 0
      let guarded = 0
      const mismatches: string[] = []
      for (const pose of golden.poses as GoldenPose[]) {
        const values = jointValues(k, pose.inputs)
        for (const [id, text] of Object.entries(pose.joints)) {
          const key = `${pose.name}/joint/${id}`
          if (guard.has(key)) {
            guarded++
            if (Math.abs(values[id] - Number(text)) > 1e-6) mismatches.push(key)
          } else {
            strings++
            if (formatNumber(values[id]) !== text) mismatches.push(`${key}: ${formatNumber(values[id])} != ${text}`)
          }
        }
        const placed = place(k, values)
        expect([...placed.keys()].sort()).toEqual(Object.keys(pose.transforms).sort())
        for (const [cid, expected] of Object.entries(pose.transforms)) {
          const m = placed.get(cid)!
          expected.forEach((text, i) => {
            const key = `${pose.name}/${cid}/${i}`
            if (guard.has(key)) {
              guarded++
              if (Math.abs(m[i] - Number(text)) > 1e-6) mismatches.push(key)
            } else {
              strings++
              if (formatNumber(m[i]) !== text) mismatches.push(`${key}: ${formatNumber(m[i])} != ${text}`)
            }
          })
        }
      }
      expect(mismatches.slice(0, 10)).toEqual([])
      expect(strings).toBeGreaterThan(0)
      // Printed so the CI log carries the evidence, not only a green tick.
      console.info(`parity ${name}: poses=${golden.poses.length} strings=${strings} tie_guard=${guarded} mismatches=0`)
    })
  }
})
