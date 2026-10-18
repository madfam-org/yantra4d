#!/usr/bin/env node
/**
 * Checks the vendored @madfam/geom-core tarball the Studio installs from.
 *
 * apps/studio depends on `file:vendor/madfam-geom-core-<version>.tgz`, a copy
 * of the geom-core GitHub Release asset committed to this repo, so the Studio
 * image build needs no network for it (a release-URL dependency failed with
 * `read ECONNRESET` on the self-hosted deploy pool). npm does NOT check the
 * lockfile `integrity` of a `file:` tarball, so this script does:
 *
 *   1. package.json names `file:vendor/madfam-geom-core-<version>.tgz` and the
 *      lockfile resolves `node_modules/@madfam/geom-core` to the same file at
 *      the same <version>;
 *   2. the vendored file's sha512 equals the lockfile `integrity`;
 *   3. (unless --offline) the vendored file is byte-for-byte the release asset
 *      https://github.com/madfam-org/geom-core/releases/download/v<version>/madfam-geom-core-<version>.tgz
 *      (its sha512 equals the downloaded file's).
 *
 * CI (ci.yml › studio, GitHub-hosted) runs the full check; the Studio
 * Dockerfile runs `--offline` before `npm install`. Exit 1 on any mismatch or
 * download failure, naming it.
 *
 * Usage: node scripts/dev/check-geom-core-vendor.mjs [--offline]
 */
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')
const STUDIO = path.join(REPO_ROOT, 'apps', 'studio')
const PKG = '@madfam/geom-core'
const offline = process.argv.includes('--offline')

const failures = []
const ok = (msg) => console.log(`ok   ${msg}`)
const fail = (msg) => { failures.push(msg); console.error(`FAIL ${msg}`) }
const sha512 = (buf) => `sha512-${createHash('sha512').update(buf).digest('base64')}`

const pkg = JSON.parse(readFileSync(path.join(STUDIO, 'package.json'), 'utf8'))
const lock = JSON.parse(readFileSync(path.join(STUDIO, 'package-lock.json'), 'utf8'))
const spec = pkg.dependencies?.[PKG]
const entry = lock.packages?.[`node_modules/${PKG}`]

const m = /^file:(vendor\/madfam-geom-core-(\d+\.\d+\.\d+(?:-[\w.]+)?)\.tgz)$/.exec(spec ?? '')
if (!m) {
  fail(`apps/studio/package.json: ${PKG} must be "file:vendor/madfam-geom-core-<version>.tgz", got ${JSON.stringify(spec)}`)
} else if (!entry) {
  fail(`apps/studio/package-lock.json has no node_modules/${PKG} entry`)
} else {
  const [, relPath, version] = m
  if (entry.resolved !== spec) fail(`lockfile resolved ${JSON.stringify(entry.resolved)} != package.json ${JSON.stringify(spec)}`)
  else ok(`package.json and lockfile both resolve ${spec}`)
  if (entry.version !== version) fail(`lockfile version ${entry.version} != tarball name version ${version}`)
  else ok(`lockfile version ${version}`)

  let vendored = null
  try {
    vendored = readFileSync(path.join(STUDIO, relPath))
  } catch (err) {
    fail(`cannot read apps/studio/${relPath}: ${err.message}`)
  }
  if (vendored) {
    const got = sha512(vendored)
    if (!entry.integrity) fail('lockfile entry has no integrity')
    else if (got !== entry.integrity) fail(`apps/studio/${relPath} is ${got}, lockfile integrity is ${entry.integrity}`)
    else ok(`apps/studio/${relPath} (${vendored.length} bytes) matches lockfile integrity ${got.slice(0, 19)}…`)

    if (offline) {
      console.log('skip release-asset comparison (--offline)')
    } else {
      const url = `https://github.com/madfam-org/geom-core/releases/download/v${version}/madfam-geom-core-${version}.tgz`
      try {
        const res = await fetch(url, { redirect: 'follow' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const release = Buffer.from(await res.arrayBuffer())
        const want = sha512(release)
        if (want !== got) fail(`vendored tarball ${got} != release asset ${want} (${url})`)
        else ok(`vendored tarball is byte-identical to the release asset ${url}`)
      } catch (err) {
        fail(`could not download the release asset ${url}: ${err.message}`)
      }
    }
  }
}

if (failures.length) {
  console.error(`check-geom-core-vendor: ${failures.length} failure(s)`)
  process.exit(1)
}
console.log('check-geom-core-vendor: all checks passed')
