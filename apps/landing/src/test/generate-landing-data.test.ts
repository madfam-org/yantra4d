/**
 * The generator's newer outputs: tier facts from apps/api/tiers.json, figures
 * from the committed snapshots, and the explicit `--refresh-snapshots` fetch
 * (exercised with an injected fetch — never the network).
 */
import { describe, it, expect, afterEach } from 'vitest'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {
  SNAPSHOT_SOURCES,
  computeSnapshotStats,
  computeTierFacts,
  generate,
  makeContext,
  refreshSnapshots,
} from '../../../../scripts/dev/generate-landing-projects.mjs'

let repos: string[] = []
afterEach(() => {
  for (const r of repos) fs.rmSync(r, { recursive: true, force: true })
  repos = []
})

function makeRepo(): string {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'y4d-data-'))
  repos.push(repo)
  fs.mkdirSync(path.join(repo, 'projects', 'demo'), { recursive: true })
  fs.writeFileSync(
    path.join(repo, 'projects', 'demo', 'project.json'),
    JSON.stringify({ project: { slug: 'demo', name: 'Demo', description: 'd' }, export_formats: ['stl', 'step'], hyperobject: { is_hyperobject: true, domain: 'household' } }),
  )
  fs.mkdirSync(path.join(repo, 'apps', 'landing', 'src', 'data'), { recursive: true })
  fs.mkdirSync(path.join(repo, 'apps', 'landing', 'public'), { recursive: true })
  fs.mkdirSync(path.join(repo, 'apps', 'api'), { recursive: true })
  return repo
}

describe('computeTierFacts', () => {
  it('reads the quotas the API enforces', () => {
    const repo = makeRepo()
    fs.writeFileSync(
      path.join(repo, 'apps', 'api', 'tiers.json'),
      JSON.stringify({ guest: { backend_renders_per_hour: 10 }, essentials: { backend_renders_per_hour: 30, max_projects: 5 }, pro: { backend_renders_per_hour: 150, max_projects: -1 } }),
    )
    expect(computeTierFacts(makeContext(repo))).toEqual({
      guestRenders: 10,
      essentialsRenders: 30,
      proRenders: 150,
      essentialsProjects: 5,
      proProjects: -1,
    })
  })

  it('yields nulls, never guesses, when the file is absent or unreadable', () => {
    const repo = makeRepo()
    expect(computeTierFacts(makeContext(repo)).guestRenders).toBeNull()
    fs.writeFileSync(path.join(repo, 'apps', 'api', 'tiers.json'), '{not json')
    expect(computeTierFacts(makeContext(repo)).proRenders).toBeNull()
  })
})

describe('computeSnapshotStats', () => {
  it('derives the soft-commons and bridge figures from the snapshots', () => {
    const repo = makeRepo()
    const dir = path.join(repo, 'apps', 'landing', 'src', 'data', 'snapshots')
    fs.mkdirSync(dir, { recursive: true })
    fs.writeFileSync(path.join(dir, 'cdg-graph.json'), JSON.stringify({ edge_count: 266, node_count: 140, edges: [] }))
    fs.writeFileSync(path.join(dir, 'cdg-families.json'), JSON.stringify({ count: 113, families: [] }))
    fs.writeFileSync(path.join(dir, 'soft-catalog.json'), JSON.stringify({ total: 516, items: [{ slug: 'a', thumbnail: '/flats/a/front.svg' }, { slug: 'b', thumbnail: null }] }))
    fs.writeFileSync(path.join(dir, 'fc-consumers.json'), JSON.stringify({ consumers: { busk: [{ slug: 'corset' }], zipper: [{ slug: 'jeans' }, { slug: 'jacket' }] } }))
    expect(computeSnapshotStats(makeContext(repo))).toEqual({
      graphEdges: 266,
      graphNodes: 140,
      families: 113,
      softCartridges: 516,
      softWithFlats: 1,
      crossLinks: 3,
      bridgedSolids: 2,
    })
  })

  it('is all nulls without snapshots, and the generated file says so', () => {
    const repo = makeRepo()
    const stats = computeSnapshotStats(makeContext(repo))
    expect(Object.values(stats).every((v) => v === null)).toBe(true)
    const { output } = generate({ repo, env: {} })
    expect(output).toContain('softCartridges: null,')
    expect(output).toContain('export const TIER_FACTS = {')
    expect(output).toContain('guestRenders: null,')
  })
})

describe('refreshSnapshots', () => {
  it('fetches the three public sources, pages the soft catalog and writes trimmed files', async () => {
    const repo = makeRepo()
    const calls: string[] = []
    const fetchImpl = async (url: string) => {
      calls.push(url)
      const json = (body: unknown) => ({ ok: true, status: 200, json: async () => body })
      if (url === SNAPSHOT_SOURCES['cdg-graph.json']) return json({ edge_count: 1, node_count: 2, edges: [{ a: 'x', b: 'y', kind: 'mates_with', via: 'M3', geometry: 'thread↔thread', family: 'iso-m3', extra: 'dropped' }] })
      if (url === SNAPSHOT_SOURCES['cdg-families.json']) return json({ count: 1, families: [{ family: 'iso-m3', members: 2, slugs: ['x', 'y'] }] })
      if (url.startsWith(SNAPSHOT_SOURCES['soft-catalog.json'])) {
        const offset = Number(new URL(url).searchParams.get('offset'))
        const items = offset === 0
          ? Array.from({ length: 100 }, (_, i) => ({ slug: `g${String(i).padStart(3, '0')}`, name: `G${i}`, thumbnail: `/flats/g${i}/front.svg`, interfaces: ['hem'], description: 'dropped' }))
          : [{ slug: 'z-last', name: 'Z', thumbnail: null, interfaces: [] }]
        return json({ total: 101, items })
      }
      return { ok: false, status: 404, json: async () => ({}) }
    }
    const ctx = makeContext(repo)
    await refreshSnapshots(ctx, { fetchImpl: fetchImpl as unknown as typeof fetch, log: () => {} })

    expect(calls.filter((u) => u.startsWith(SNAPSHOT_SOURCES['soft-catalog.json']))).toHaveLength(2)
    const soft = JSON.parse(fs.readFileSync(path.join(ctx.snapshotsDir, 'soft-catalog.json'), 'utf8'))
    expect(soft.total).toBe(101)
    expect(soft.items).toHaveLength(101)
    expect(soft.items[0]).not.toHaveProperty('description')
    expect(soft.items.find((i: { slug: string }) => i.slug === 'g000').interfaces).toBe(1)
    const graph = JSON.parse(fs.readFileSync(path.join(ctx.snapshotsDir, 'cdg-graph.json'), 'utf8'))
    expect(graph.edges[0]).toEqual({ a: 'x', b: 'y', family: 'iso-m3', kind: 'mates_with', via: 'M3', geometry: 'thread↔thread' })
    expect(graph.source).toBe(SNAPSHOT_SOURCES['cdg-graph.json'])
    expect(computeSnapshotStats(ctx)).toMatchObject({ graphEdges: 1, families: 1, softCartridges: 101, softWithFlats: 100 })
  })

  it('refuses silently-empty results: a non-OK response throws', async () => {
    const repo = makeRepo()
    const fetchImpl = async () => ({ ok: false, status: 503, json: async () => ({}) })
    await expect(refreshSnapshots(makeContext(repo), { fetchImpl: fetchImpl as unknown as typeof fetch, log: () => {} })).rejects.toThrow(/HTTP 503/)
  })
})
