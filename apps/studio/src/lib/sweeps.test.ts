import { describe, it, expect } from 'vitest'
import {
  manifestSweeps, sweepFrameInterval, sweepSeconds,
  DEFAULT_SWEEP_FRAMES, DEFAULT_SWEEP_DURATION_MS, MIN_SWEEP_FRAME_MS,
} from './sweeps'

describe('manifestSweeps', () => {
  it('reads the sweeps a manifest declares', () => {
    const sweeps = manifestSweeps({
      animations: [{ id: 'nema-sweep', label: { en: 'NEMA 17 → 34' }, frames: 5, duration_ms: 2500, mode: 'mount' }],
    })
    expect(sweeps).toHaveLength(1)
    expect(sweeps[0]).toMatchObject({ id: 'nema-sweep', frames: 5, duration_ms: 2500, mode: 'mount' })
  })

  it('is empty for a manifest without sweeps, or with something else under the key', () => {
    expect(manifestSweeps(null)).toEqual([])
    expect(manifestSweeps({})).toEqual([])
    expect(manifestSweeps({ animations: 'nope' })).toEqual([])
  })

  it('drops entries with no id and fills the API defaults for frames and duration', () => {
    const sweeps = manifestSweeps({
      animations: [null, 'x', { label: 'no id' }, { id: '' }, { id: 'a', frames: 0, duration_ms: -1, mode: '' }, { id: 'b', frames: 2.5 }],
    })
    expect(sweeps.map(s => s.id)).toEqual(['a', 'b'])
    expect(sweeps[0]).toMatchObject({ frames: DEFAULT_SWEEP_FRAMES, duration_ms: DEFAULT_SWEEP_DURATION_MS, mode: undefined })
    expect(sweeps[1].frames).toBe(DEFAULT_SWEEP_FRAMES)
  })
})

describe('sweepFrameInterval', () => {
  it('spreads one pass over the frames', () => {
    expect(sweepFrameInterval({ duration_ms: 2000 }, 5)).toBe(400)
  })

  it('never flips frames faster than the floor', () => {
    expect(sweepFrameInterval({ duration_ms: 100 }, 10)).toBe(MIN_SWEEP_FRAME_MS)
  })

  it('falls back to the default duration and to one frame', () => {
    expect(sweepFrameInterval(null, 0)).toBe(DEFAULT_SWEEP_DURATION_MS)
  })
})

describe('sweepSeconds', () => {
  it('prints whole seconds bare and others to one decimal', () => {
    expect(sweepSeconds({ duration_ms: 2000 })).toBe('2')
    expect(sweepSeconds({ duration_ms: 2400 })).toBe('2.4')
  })
})
