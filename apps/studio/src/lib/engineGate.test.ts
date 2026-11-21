import { describe, it, expect } from 'vitest'
import { engineGateFor, modesAllowedForTier, ENGINE_TIER_FEATURE } from './engineGate'

const gridfinity = {
  engine: 'cadquery',
  modes: [{ id: 'bin' }, { id: 'grid', engine: 'openscad' }, { id: 'graph', scad_file: 'x.graph.json' }],
}
const guest = { cadquery_engine: false, graph_engine: false }

describe('engineGateFor', () => {
  it('denies an engine whose tier feature is false', () => {
    expect(engineGateFor(gridfinity, 'bin', guest)).toEqual({ allowed: false, engine: 'cadquery', feature: 'cadquery_engine' })
    expect(engineGateFor(gridfinity, 'graph', guest)).toEqual({ allowed: false, engine: 'graph', feature: 'graph_engine' })
  })

  it('allows an engine without a tier feature', () => {
    expect(engineGateFor(gridfinity, 'grid', guest).allowed).toBe(true)
    expect(engineGateFor({ engine: 'implicit' }, null, guest)).toEqual({ allowed: true, engine: 'implicit', feature: null })
  })

  it('allows when the feature is true', () => {
    expect(engineGateFor(gridfinity, 'bin', { cadquery_engine: true }).allowed).toBe(true)
  })

  it('allows when the answer is unknown: no limits, or no such key', () => {
    expect(engineGateFor(gridfinity, 'bin', null).allowed).toBe(true)
    expect(engineGateFor(gridfinity, 'bin', {}).allowed).toBe(true)
  })

  it('maps exactly the engines the API gates', () => {
    expect(ENGINE_TIER_FEATURE).toEqual({ cadquery: 'cadquery_engine', graph: 'graph_engine' })
  })
})

describe('modesAllowedForTier', () => {
  it('lists the modes a tier can render, in manifest order', () => {
    expect(modesAllowedForTier(gridfinity, guest)).toEqual(['grid'])
    expect(modesAllowedForTier(gridfinity, { cadquery_engine: true, graph_engine: true })).toEqual(['bin', 'grid', 'graph'])
    expect(modesAllowedForTier(null, guest)).toEqual([])
  })
})

describe('the free Commons quota', () => {
  const guestWithQuota = { ...guest, commons_brep_renders_per_day: 3 }

  it('lets a tier without the engine render, metered, when it has a daily quota', () => {
    expect(engineGateFor(gridfinity, 'bin', guestWithQuota)).toEqual({
      allowed: true, engine: 'cadquery', feature: 'cadquery_engine', metered: true,
    })
    expect(engineGateFor(gridfinity, 'graph', guestWithQuota).metered).toBe(true)
  })

  it('a quota of 0 keeps the gate closed', () => {
    expect(engineGateFor(gridfinity, 'bin', { ...guest, commons_brep_renders_per_day: 0 }).allowed).toBe(false)
  })

  it('a tier with the engine is never metered', () => {
    expect(engineGateFor(gridfinity, 'bin', { cadquery_engine: true, commons_brep_renders_per_day: -1 }))
      .toEqual({ allowed: true, engine: 'cadquery', feature: 'cadquery_engine' })
  })

  it('an engine without a tier feature is never metered', () => {
    expect(engineGateFor(gridfinity, 'grid', guestWithQuota).metered).toBeUndefined()
  })

  it('metered modes count as renderable', () => {
    expect(modesAllowedForTier(gridfinity, guestWithQuota)).toEqual(['bin', 'grid', 'graph'])
  })
})
