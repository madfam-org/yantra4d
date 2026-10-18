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
