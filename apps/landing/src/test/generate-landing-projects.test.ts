/**
 * Tests for `scripts/dev/generate-landing-projects.mjs`.
 *
 * The generator writes `src/data/projects.ts`, which is what the public gallery
 * renders, so its two safety rules are tested here rather than left to a manual
 * run:
 *
 *   1. a private cartridge never reaches the generated list, and
 *   2. a checkout missing public cartridge submodules never produces a file that
 *      claims to be complete.
 *
 * Both are exercised against throwaway fixture repos built in a temp dir, so the
 * assertions do not move when a real cartridge is added. One test does read the
 * committed `src/data/projects.ts`: that one is the regression guard for the
 * `tablaco` entry that shipped in the public gallery, and it must keep running in
 * the landing CI job, which checks out no submodules at all.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {
  BUILTIN_PRIVATE_SLUGS,
  EXIT_DRIFT,
  EXIT_INCOMPLETE,
  EXIT_OK,
  cartridgeSubmodules,
  generate,
  isPrivateManifest,
  parseGitmodules,
  privateSlugs,
  run,
} from '../../../../scripts/dev/generate-landing-projects.mjs'

// ─── Fixture repo builder ───────────────────────────────────────────────────

type ManifestSpec = {
  slug: string
  name?: string
  description?: string
  unlisted?: boolean
  private?: boolean
  privateUnderProject?: boolean
  hyperobject?: boolean
}

type RepoSpec = {
  /** Cartridges written to `projects/<slug>/project.json`. */
  manifests?: ManifestSpec[]
  /** `.gitmodules` entries: `[path, update]` — an empty update means "public". */
  submodules?: Array<[string, string]>
  /** Submodule paths to create as empty (uninitialised) directories. */
  emptyDirs?: string[]
  /** Contents to seed `apps/landing/src/data/projects.ts` with, if any. */
  committed?: string
}

let repos: string[] = []

function makeRepo(spec: RepoSpec = {}): string {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'y4d-gen-'))
  repos.push(repo)

  fs.mkdirSync(path.join(repo, 'projects'), { recursive: true })
  fs.mkdirSync(path.join(repo, 'apps', 'landing', 'src', 'data'), { recursive: true })
  fs.mkdirSync(path.join(repo, 'apps', 'landing', 'public'), { recursive: true })

  for (const m of spec.manifests ?? []) {
    const dir = path.join(repo, 'projects', m.slug)
    fs.mkdirSync(dir, { recursive: true })
    const project: Record<string, unknown> = {
      slug: m.slug,
      name: m.name ?? m.slug,
      description: m.description ?? `${m.slug} description`,
      tags: [],
    }
    if (m.unlisted) project.unlisted = true
    if (m.privateUnderProject) project.access_control = { view: 'private' }
    const manifest: Record<string, unknown> = { project }
    if (m.private) manifest.access_control = { view: 'private' }
    if (m.hyperobject) manifest.hyperobject = { is_hyperobject: true, domain: 'industrial' }
    fs.writeFileSync(path.join(dir, 'project.json'), JSON.stringify(manifest, null, 2))
  }

  for (const rel of spec.emptyDirs ?? []) {
    fs.mkdirSync(path.join(repo, rel), { recursive: true })
  }

  if (spec.submodules) {
    const body = spec.submodules
      .map(([p, update]) =>
        [
          `[submodule "${p}"]`,
          `\tpath = ${p}`,
          `\turl = https://example.invalid/${p}.git`,
          ...(update ? [`\tupdate = ${update}`] : []),
        ].join('\n'),
      )
      .join('\n')
    fs.writeFileSync(path.join(repo, '.gitmodules'), `${body}\n`)
  }

  if (spec.committed !== undefined) {
    fs.writeFileSync(
      path.join(repo, 'apps', 'landing', 'src', 'data', 'projects.ts'),
      spec.committed,
      'utf8',
    )
  }

  return repo
}

function committedFile(repo: string): string {
  return fs.readFileSync(path.join(repo, 'apps', 'landing', 'src', 'data', 'projects.ts'), 'utf8')
}

function slugsIn(output: string): string[] {
  return [...output.matchAll(/^ {2}\{ slug: "([^"]+)"/gm)].map((m) => m[1])
}

/** Collect stdout/stderr from a `run()` call instead of printing it. */
function capture() {
  const out: string[] = []
  const err: string[] = []
  return {
    out,
    err,
    log: (m: unknown) => out.push(String(m)),
    logError: (m: unknown) => err.push(String(m)),
  }
}

beforeEach(() => {
  repos = []
})

afterEach(() => {
  for (const repo of repos) fs.rmSync(repo, { recursive: true, force: true })
  repos = []
})

// ─── Private-slug resolution ────────────────────────────────────────────────

describe('privateSlugs', () => {
  it('always includes the built-in client-private cartridges', () => {
    expect([...privateSlugs({})]).toEqual(expect.arrayContaining(BUILTIN_PRIVATE_SLUGS))
  })

  it('keeps the built-ins private when PRIVATE_PROJECTS is empty or missing', () => {
    // The floor is the point: an env var that got lost between the deployment
    // and whatever shell runs the generator must not re-publish a cartridge.
    for (const env of [{}, { PRIVATE_PROJECTS: '' }, { PRIVATE_PROJECTS: '  ,, ' }]) {
      const slugs = privateSlugs(env)
      expect(slugs.has('tablaco')).toBe(true)
      expect(slugs.has('tablaco-v2')).toBe(true)
    }
  })

  it('adds slugs from PRIVATE_PROJECTS, trimmed and lower-cased', () => {
    const slugs = privateSlugs({ PRIVATE_PROJECTS: ' Acme-Bracket , client-widget ' })
    expect(slugs.has('acme-bracket')).toBe(true)
    expect(slugs.has('client-widget')).toBe(true)
    expect(slugs.has('tablaco')).toBe(true)
  })
})

describe('isPrivateManifest', () => {
  it('reads the top-level access_control block', () => {
    expect(isPrivateManifest({ access_control: { view: 'private' } })).toBe(true)
  })

  it('also reads a project-level access_control block', () => {
    expect(isPrivateManifest({ project: { access_control: { view: 'private' } } })).toBe(true)
  })

  it('treats public, authenticated and absent as not private', () => {
    expect(isPrivateManifest({ access_control: { view: 'public' } })).toBe(false)
    expect(isPrivateManifest({ access_control: { view: 'authenticated' } })).toBe(false)
    expect(isPrivateManifest({ project: {} })).toBe(false)
    expect(isPrivateManifest(null)).toBe(false)
  })
})

// ─── .gitmodules reading ────────────────────────────────────────────────────

describe('parseGitmodules', () => {
  it('reads path and update for each submodule block', () => {
    const entries = parseGitmodules(
      [
        '[submodule "projects/a"]',
        '\tpath = projects/a',
        '\turl = https://example.invalid/a.git',
        '[submodule "projects/b"]',
        '\tpath = projects/b',
        '\turl = https://example.invalid/b.git',
        '\tupdate = none',
      ].join('\n'),
    )
    expect(entries).toEqual([
      { path: 'projects/a', update: '' },
      { path: 'projects/b', update: 'none' },
    ])
  })

  it('returns nothing for empty or absent content', () => {
    expect(parseGitmodules('')).toEqual([])
    expect(parseGitmodules(undefined)).toEqual([])
  })
})

describe('cartridgeSubmodules', () => {
  it('separates public cartridges from `update = none` ones and ignores libs', () => {
    const repo = makeRepo({
      submodules: [
        ['libs/BOSL2', ''],
        ['projects/public-one', ''],
        ['projects/tablaco', 'none'],
      ],
    })
    const { required, expectedAbsent } = cartridgeSubmodules(repo)
    expect(required).toEqual(['projects/public-one'])
    expect(expectedAbsent).toEqual(['projects/tablaco'])
  })

  it('reports nothing when the repo has no .gitmodules', () => {
    const repo = makeRepo({})
    expect(cartridgeSubmodules(repo)).toEqual({ required: [], expectedAbsent: [] })
  })
})

// ─── Filtering ──────────────────────────────────────────────────────────────

describe('generate — private cartridges are dropped', () => {
  it('omits a manifest that declares access_control.view = "private"', () => {
    const repo = makeRepo({
      manifests: [{ slug: 'public-widget' }, { slug: 'client-thing', private: true }],
    })
    const { output, meta } = generate({ repo, env: {} })
    expect(slugsIn(output)).toEqual(['public-widget'])
    expect(meta.skippedPrivate).toEqual(['client-thing'])
  })

  it('omits a manifest whose privacy is declared under `project`', () => {
    const repo = makeRepo({
      manifests: [{ slug: 'public-widget' }, { slug: 'nested-private', privateUnderProject: true }],
    })
    expect(slugsIn(generate({ repo, env: {} }).output)).toEqual(['public-widget'])
  })

  it('omits a slug named by PRIVATE_PROJECTS even when its manifest says nothing', () => {
    const repo = makeRepo({
      manifests: [{ slug: 'public-widget' }, { slug: 'acme-bracket' }],
    })
    const { output } = generate({ repo, env: { PRIVATE_PROJECTS: 'acme-bracket' } })
    expect(slugsIn(output)).toEqual(['public-widget'])
  })

  it('omits the built-in client cartridges when PRIVATE_PROJECTS is unset', () => {
    // Reproduces the bug this change fixes: `tablaco` shipped in the public
    // gallery with a description and a Studio link while the API refused it.
    const repo = makeRepo({
      manifests: [{ slug: 'public-widget' }, { slug: 'tablaco' }, { slug: 'tablaco-v2' }],
    })
    const { output } = generate({ repo, env: {} })
    expect(slugsIn(output)).toEqual(['public-widget'])
    expect(output).not.toContain('tablaco')
  })

  it('omits a private cartridge from the commons figures too, not just the list', () => {
    const withPrivate = makeRepo({
      manifests: [{ slug: 'public-widget', hyperobject: true }, { slug: 'tablaco', hyperobject: true }],
    })
    const withoutPrivate = makeRepo({
      manifests: [{ slug: 'public-widget', hyperobject: true }],
    })
    expect(generate({ repo: withPrivate, env: {} }).stats).toEqual(
      generate({ repo: withoutPrivate, env: {} }).stats,
    )
  })

  it('leaves `unlisted` semantics unchanged — unlisted is not private', () => {
    const repo = makeRepo({
      manifests: [{ slug: 'public-widget' }, { slug: 'quiet-widget', unlisted: true }],
    })
    expect(slugsIn(generate({ repo, env: {} }).output).sort()).toEqual([
      'public-widget',
      'quiet-widget',
    ])
  })
})

// ─── Checkout completeness ──────────────────────────────────────────────────

describe('generate — checkout completeness', () => {
  it('treats an absent `update = none` submodule as expected, not incomplete', () => {
    const repo = makeRepo({
      manifests: [{ slug: 'public-one' }],
      submodules: [
        ['projects/public-one', ''],
        ['projects/tablaco', 'none'],
      ],
    })
    expect(generate({ repo, env: {} }).missing).toEqual([])
  })

  it('still reports complete when a `update = none` path exists but is empty', () => {
    // A recursive checkout leaves the gitlink directory behind, empty.
    const repo = makeRepo({
      manifests: [{ slug: 'public-one' }],
      submodules: [
        ['projects/public-one', ''],
        ['projects/tablaco', 'none'],
      ],
      emptyDirs: ['projects/tablaco'],
    })
    expect(generate({ repo, env: {} }).missing).toEqual([])
  })

  it('reports a public cartridge submodule with no project.json as missing', () => {
    const repo = makeRepo({
      manifests: [{ slug: 'public-one' }],
      submodules: [
        ['projects/public-one', ''],
        ['projects/public-two', ''],
        ['projects/tablaco', 'none'],
      ],
      emptyDirs: ['projects/public-two'],
    })
    expect(generate({ repo, env: {} }).missing).toEqual(['projects/public-two'])
  })
})

// ─── CLI behaviour ──────────────────────────────────────────────────────────

describe('run — fail closed on an incomplete checkout', () => {
  const partialRepo = () =>
    makeRepo({
      manifests: [{ slug: 'public-one' }],
      submodules: [
        ['projects/public-one', ''],
        ['projects/public-two', ''],
      ],
      emptyDirs: ['projects/public-two'],
    })

  it('refuses to write and names the missing path', () => {
    const repo = partialRepo()
    const io = capture()
    expect(run({ argv: [], repo, env: {}, ...io })).toBe(EXIT_INCOMPLETE)
    expect(io.err.join('\n')).toContain('INCOMPLETE CHECKOUT')
    expect(io.err.join('\n')).toContain('projects/public-two')
    expect(fs.existsSync(path.join(repo, 'apps/landing/src/data/projects.ts'))).toBe(false)
  })

  it('never suggests initialising an `update = none` path', () => {
    const repo = partialRepo()
    const io = capture()
    run({ argv: [], repo, env: {}, ...io })
    expect(io.err.join('\n')).not.toContain('tablaco')
  })

  it('writes anyway under --allow-partial, and says so loudly', () => {
    const repo = partialRepo()
    const io = capture()
    expect(run({ argv: ['--allow-partial'], repo, env: {}, ...io })).toBe(EXIT_OK)
    expect(io.err.join('\n')).toContain('--allow-partial')
    expect(slugsIn(committedFile(repo))).toEqual(['public-one'])
  })

  it('fails --check on an incomplete checkout even with --allow-partial', () => {
    // A partial regeneration cannot be compared against a file that claims to be
    // complete, so this lane only ever gets stricter.
    const repo = partialRepo()
    const io = capture()
    expect(run({ argv: ['--check', '--allow-partial'], repo, env: {}, ...io })).toBe(
      EXIT_INCOMPLETE,
    )
    expect(io.err.join('\n')).toContain('INCOMPLETE CHECKOUT')
  })
})

describe('run --check', () => {
  it('passes when the committed file matches the manifests', () => {
    const repo = makeRepo({ manifests: [{ slug: 'public-one' }] })
    expect(run({ argv: [], repo, env: {}, ...capture() })).toBe(EXIT_OK)

    const io = capture()
    expect(run({ argv: ['--check'], repo, env: {}, ...io })).toBe(EXIT_OK)
    expect(io.out.join('\n')).toContain('up to date')
  })

  it('reports drift, distinctly from an incomplete checkout', () => {
    const repo = makeRepo({
      manifests: [{ slug: 'public-one' }],
      committed: '// stale\n',
    })
    const io = capture()
    expect(run({ argv: ['--check'], repo, env: {}, ...io })).toBe(EXIT_DRIFT)
    expect(io.err.join('\n')).toContain('DRIFT')
    expect(io.err.join('\n')).not.toContain('INCOMPLETE CHECKOUT')
  })

  it('reports drift when the committed file still carries a now-private cartridge', () => {
    const repo = makeRepo({
      manifests: [{ slug: 'public-one' }, { slug: 'acme-bracket' }],
    })
    // Generate while the cartridge is still public, then mark it private: this
    // is what turns "a cartridge went private today" into a CI failure instead
    // of a gallery that keeps advertising it.
    expect(run({ argv: [], repo, env: {}, ...capture() })).toBe(EXIT_OK)
    expect(slugsIn(committedFile(repo))).toEqual(['acme-bracket', 'public-one'])

    const io = capture()
    expect(
      run({ argv: ['--check'], repo, env: { PRIVATE_PROJECTS: 'acme-bracket' }, ...io }),
    ).toBe(EXIT_DRIFT)
    expect(io.err.join('\n')).toContain('DRIFT')
  })

  it('never writes the output file', () => {
    const repo = makeRepo({ manifests: [{ slug: 'public-one' }], committed: '// stale\n' })
    run({ argv: ['--check'], repo, env: {}, ...capture() })
    expect(committedFile(repo)).toBe('// stale\n')
  })
})

// ─── Regression guard on the committed file ─────────────────────────────────

describe('committed src/data/projects.ts', () => {
  const committed = fs.readFileSync(
    path.resolve(__dirname, '..', 'data', 'projects.ts'),
    'utf8',
  )

  it('lists no client-private cartridge', () => {
    for (const slug of BUILTIN_PRIVATE_SLUGS) {
      expect(committed).not.toContain(`slug: "${slug}"`)
    }
  })

  it('carries the full commons, not a submodule-less subset', () => {
    // 466 in-tree manifests + 35 public submodule cartridges at the time of
    // writing. A regeneration in a checkout without submodules would land here
    // around 328, which is exactly the drift this guard exists to catch.
    expect(slugsIn(committed).length).toBeGreaterThan(450)
  })

  it('has no duplicate slugs', () => {
    const slugs = slugsIn(committed)
    expect(new Set(slugs).size).toBe(slugs.length)
  })
})
