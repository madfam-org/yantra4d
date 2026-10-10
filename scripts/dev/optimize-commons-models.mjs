/**
 * Optimize the commons models for the landing (yantra4d.com) — Phase 1 of the
 * landing revamp (internal-devops docs/strategy/2026-09-18-yantra4d-landing-revamp-plan.md).
 *
 * Turns raw GLB renders of the cartridges into the small, meshopt-compressed
 * LOD files the page streams, and writes the `manifest.json` (v2) the page's
 * reader (`apps/landing/src/lib/models-manifest.ts`) consumes.
 *
 * Per input the pipeline is:
 *
 *   read → bake every mesh into ONE triangle soup in world space, dropping
 *   materials, textures, normals, UVs, colours, skins, cameras, animations and
 *   every extension (the page applies its own material; nothing but POSITION
 *   survives, by construction) → weld (bitwise) → simplify with MeshoptSimplifier
 *   down to the triangle budget → quantize + meshopt-compress
 *   (EXT_meshopt_compression, level medium) → write.
 *
 * Two levels of detail per cartridge, plus keyframes:
 *
 *   <slug>.lod1.glb   ≤ meshes.lod1Triangles / meshes.lod1Bytes   (every input)
 *   <slug>.lod0.glb   ≤ meshes.lod0Triangles / meshes.lod0Bytes   (--lod0 selection;
 *                     skipped when it would add no triangles over lod1)
 *   <slug>.<animation>.<index>.glb   keyframes at lod0 settings, ≤ meshes.keyframeBytes
 *                                    (a frame byte-identical to the base or to an
 *                                    earlier frame is not written; the manifest
 *                                    points its entry at the file that exists)
 *
 * Budgets come from `apps/landing/perf-budgets.json` (`meshes` block; a
 * `meshes.exceptions` map may raise them for one slug, with a written reason,
 * which the manifest then records on that entry — see validateExceptions). When the
 * triangle budget alone does not bring a file under its byte budget, the
 * triangle target is lowered further (reported as such) until it fits or hits
 * the floor. Anything still over budget is listed; `--strict` turns that into
 * exit 1 (the files are still written — nothing is ever silently dropped).
 *
 * Inputs:
 *   --in <dir>      raw GLBs, `<slug>.glb` and `<slug>.<animation>.<index>.glb`
 *                   (default apps/landing/public/models/raw). When --in is absent
 *                   AND that directory does not exist, the legacy uncompressed
 *                   `apps/landing/public/models/<slug>.glb` files are the inputs —
 *                   this is how the first run over the 2026-03 carousel GLBs works.
 *   --out <dir>     default apps/landing/public/models
 *
 * Determinism: inputs are processed in a stable order, GLBs carry no timestamps,
 * and `--generated <iso>` pins the manifest timestamp so two runs byte-compare.
 *   --check         exit 3 when the outputs on disk differ from what this run
 *                   would write (a CI drift lane; writes nothing). With --clean it
 *                   also reports files that a --clean run would remove.
 *   --clean         remove stale `*.lod*.glb` / frame files that no longer have an
 *                   input, and the legacy uncompressed `<slug>.glb` once its lod1
 *                   exists (only when the legacy file was the input).
 *
 * Usage (from apps/landing):
 *   npm run models:optimize -- [--in <dir>] [--out <dir>] [--lod0 all|hero|none|a,b,c]
 *                              [--strict] [--check] [--clean] [--generated <iso>]
 *                              [--commons-pin <sha>|none] [--budgets <file>] [--quiet]
 *
 * Exit codes:
 *   0  success (or --check: up to date)
 *   1  --strict and at least one output is over its byte budget
 *   2  usage error / nothing to do (no inputs, missing budgets file)
 *   3  --check: outputs differ from what is on disk
 *   4  at least one input could not be processed (the others were still written)
 *
 * Dependencies (@gltf-transform/*, meshoptimizer) are devDependencies of
 * apps/landing, so they are resolved from there rather than from this file's
 * own location — see loadDeps().
 */
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const DEFAULT_REPO = path.resolve(__dirname, '..', '..');

export const GENERATOR = 'scripts/dev/optimize-commons-models.mjs';
export const MANIFEST_VERSION = 2;

/** Exit codes, named so the workflow, the docs and the tests agree on them. */
export const EXIT_OK = 0;
export const EXIT_BUDGET = 1;
export const EXIT_USAGE = 2;
export const EXIT_DRIFT = 3;
export const EXIT_FAILED = 4;

/** Above this many input cartridges `--lod0` defaults to `hero` instead of `all`. */
export const LOD0_ALL_MAX_INPUTS = 40;

/** Never simplify below this many triangles, whatever the byte budget says. */
export const MIN_TRIANGLES = 64;

/**
 * Simplifier error bounds, as a fraction of the mesh radius, tried in order until
 * the triangle target is reached. 1 means "unconstrained": at that point only the
 * topology can stop the simplifier.
 */
export const ERROR_SCHEDULE = [0.001, 0.005, 0.02, 0.05, 0.1, 0.25, 0.5, 1];

/** Extra passes lowering the triangle target when the byte budget is the binding one. */
const MAX_BYTE_PASSES = 5;

/** Position quantization bits (KHR_mesh_quantization). 14 bits over a 300 mm part ≈ 0.02 mm. */
const POSITION_BITS = 14;

const BUDGET_KEYS = ['lod1Bytes', 'lod0Bytes', 'lod1Triangles', 'lod0Triangles', 'keyframeBytes'];

// ──────────────────────────────────────────────
// Dependencies
// ──────────────────────────────────────────────

/**
 * Resolve a package's ESM entry from `apps/landing/node_modules` by reading its
 * export map. Bare specifiers would resolve from this file's directory and
 * never find the landing's node_modules, and the npm script is fixed to run
 * this file from where it lives.
 */
function resolveLandingPackage(landingDir, name) {
  const pkgDir = path.join(landingDir, 'node_modules', ...name.split('/'));
  const pkgFile = path.join(pkgDir, 'package.json');
  if (!fs.existsSync(pkgFile)) {
    throw new Error(
      `${name} is not installed under ${path.relative(process.cwd(), pkgDir) || '.'} — run \`npm ci\` in apps/landing first.`,
    );
  }
  const pkg = JSON.parse(fs.readFileSync(pkgFile, 'utf8'));
  let entry = pkg.exports && typeof pkg.exports === 'object' && '.' in pkg.exports ? pkg.exports['.'] : pkg.exports;
  while (entry && typeof entry === 'object') {
    entry = entry.import ?? entry.default ?? entry.module ?? entry.node ?? entry.require;
  }
  entry = entry ?? pkg.module ?? pkg.main ?? 'index.js';
  return pathToFileURL(path.join(pkgDir, entry)).href;
}

let depsPromise = null;

/** Load @gltf-transform/* and meshoptimizer once, from the landing's node_modules. */
export function loadDeps(landingDir = path.join(DEFAULT_REPO, 'apps', 'landing')) {
  if (!depsPromise) {
    depsPromise = (async () => {
      const [core, extensions, functions, meshoptimizer] = await Promise.all(
        ['@gltf-transform/core', '@gltf-transform/extensions', '@gltf-transform/functions', 'meshoptimizer'].map(
          (name) => import(resolveLandingPackage(landingDir, name)),
        ),
      );
      const { MeshoptDecoder, MeshoptEncoder, MeshoptSimplifier } = meshoptimizer;
      await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready, MeshoptSimplifier.ready]);
      const io = new core.NodeIO()
        .registerExtensions(extensions.ALL_EXTENSIONS)
        .registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })
        .setLogger(new core.Logger(core.Logger.Verbosity.SILENT));
      return { core, functions, io, MeshoptDecoder, MeshoptEncoder, MeshoptSimplifier };
    })();
  }
  return depsPromise;
}

// ──────────────────────────────────────────────
// CLI arguments
// ──────────────────────────────────────────────

const VALUE_FLAGS = new Set(['in', 'out', 'lod0', 'generated', 'repo', 'commons-pin', 'budgets']);
const BOOL_FLAGS = new Set(['strict', 'check', 'clean', 'quiet', 'help']);

/** `--flag value` and `--flag=value` for the flags above; anything else is a usage error. */
export function parseArgs(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith('--')) throw new UsageError(`Unexpected argument: ${arg}`);
    const eq = arg.indexOf('=');
    const name = eq === -1 ? arg.slice(2) : arg.slice(2, eq);
    if (BOOL_FLAGS.has(name)) {
      if (eq !== -1) throw new UsageError(`--${name} takes no value`);
      opts[name] = true;
    } else if (VALUE_FLAGS.has(name)) {
      const value = eq === -1 ? argv[++i] : arg.slice(eq + 1);
      if (value === undefined || value.startsWith('--')) throw new UsageError(`--${name} needs a value`);
      opts[name] = value;
    } else {
      throw new UsageError(`Unknown flag: --${name}`);
    }
  }
  if (opts.generated !== undefined && Number.isNaN(Date.parse(opts.generated))) {
    throw new UsageError(`--generated must be an ISO-8601 timestamp, got ${opts.generated}`);
  }
  if (opts['commons-pin'] !== undefined && opts['commons-pin'] !== 'none' && !/^[0-9a-f]{40}$/.test(opts['commons-pin'])) {
    throw new UsageError(`--commons-pin must be a 40-hex sha or "none", got ${opts['commons-pin']}`);
  }
  return opts;
}

export class UsageError extends Error {}

export const USAGE = [
  'Usage: node scripts/dev/optimize-commons-models.mjs [options]',
  '',
  '  --in <dir>              raw GLBs (default apps/landing/public/models/raw; absent → legacy',
  '                          apps/landing/public/models/<slug>.glb files are the inputs)',
  '  --out <dir>             default apps/landing/public/models',
  '  --lod0 all|hero|none|a,b  which slugs also get a lod0 (default: all for ≤ 40 inputs, else hero)',
  '  --strict                exit 1 when any output is over its byte budget',
  '  --check                 compare against what is on disk, write nothing (exit 3 on drift)',
  '  --clean                 remove stale outputs and consumed legacy inputs',
  '  --generated <iso>       manifest timestamp (default: now, second precision)',
  '  --commons-pin <sha>|none  override the detected commons submodule sha',
  '  --budgets <file>        default apps/landing/perf-budgets.json',
  '  --quiet                 only warnings and the summary',
].join('\n');

// ──────────────────────────────────────────────
// Context
// ──────────────────────────────────────────────

/** Paths and options for one run, all derived from a repo root (tests point it at a fixture). */
export function makeContext({ repo = DEFAULT_REPO, opts = {}, cwd = process.cwd() } = {}) {
  const landingDir = path.join(repo, 'apps', 'landing');
  const modelsDir = path.join(landingDir, 'public', 'models');
  const outDir = opts.out ? path.resolve(cwd, opts.out) : modelsDir;
  const rawDir = opts.in ? path.resolve(cwd, opts.in) : path.join(modelsDir, 'raw');
  const legacyMode = !opts.in && !fs.existsSync(rawDir);
  return {
    repo,
    landingDir,
    projectsDir: path.join(repo, 'projects'),
    heroFile: path.join(landingDir, 'models.hero.json'),
    budgetsFile: opts.budgets ? path.resolve(cwd, opts.budgets) : path.join(landingDir, 'perf-budgets.json'),
    outDir,
    inDir: legacyMode ? outDir : rawDir,
    legacyMode,
    manifestFile: path.join(outDir, 'manifest.json'),
    opts,
  };
}

// ──────────────────────────────────────────────
// Budgets
// ──────────────────────────────────────────────

/** The `meshes` block of perf-budgets.json; every key the pipeline enforces must be a positive number. */
export function loadBudgets(file) {
  if (!fs.existsSync(file)) throw new UsageError(`Budgets file not found: ${file}`);
  const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
  const meshes = parsed && parsed.meshes;
  if (!meshes || typeof meshes !== 'object') throw new UsageError(`${file} has no "meshes" block`);
  for (const key of BUDGET_KEYS) {
    if (!(Number.isFinite(meshes[key]) && meshes[key] > 0)) {
      throw new UsageError(`${file}: meshes.${key} must be a positive number`);
    }
  }
  validateExceptions(meshes.exceptions, file);
  return meshes;
}

/**
 * `meshes.exceptions`: per-cartridge overrides of the byte/triangle budgets,
 * each with a written reason — for the mesh that cannot meet the block above
 * without a change the pipeline cannot make yet (the first: a lattice whose
 * simplification floors at 12,365 triangles / 28 KB against the 12 KB lod1
 * cap, 2026-09-19). The override applies to that slug's target only and is
 * recorded on its manifest entry, so a budget kept by exception is never
 * mistaken for one kept outright. Keys beside the budget keys and `reason`
 * are rejected: an exception must not smuggle anything else in.
 */
export function validateExceptions(exceptions, file = 'perf-budgets.json') {
  if (exceptions === undefined) return {};
  if (!exceptions || typeof exceptions !== 'object' || Array.isArray(exceptions)) {
    throw new UsageError(`${file}: meshes.exceptions must be an object keyed by slug`);
  }
  const out = {};
  for (const [slug, spec] of Object.entries(exceptions)) {
    if (slug.startsWith('_')) continue; // `_comment`
    if (!SLUG_RE.test(slug)) throw new UsageError(`${file}: meshes.exceptions has an invalid slug "${slug}"`);
    if (!spec || typeof spec !== 'object' || Array.isArray(spec)) {
      throw new UsageError(`${file}: meshes.exceptions.${slug} must be an object`);
    }
    if (typeof spec.reason !== 'string' || !spec.reason.trim()) {
      throw new UsageError(`${file}: meshes.exceptions.${slug} needs a written reason`);
    }
    const overrides = {};
    for (const [key, value] of Object.entries(spec)) {
      if (key === 'reason' || key.startsWith('_')) continue;
      if (!BUDGET_KEYS.includes(key)) throw new UsageError(`${file}: meshes.exceptions.${slug}.${key} is not a budget key`);
      if (!(Number.isFinite(value) && value > 0)) throw new UsageError(`${file}: meshes.exceptions.${slug}.${key} must be a positive number`);
      overrides[key] = value;
    }
    if (!Object.keys(overrides).length) throw new UsageError(`${file}: meshes.exceptions.${slug} overrides nothing`);
    out[slug] = { ...overrides, reason: spec.reason.trim() };
  }
  return out;
}

/**
 * The targets for one slug: the block's numbers, with that slug's exception
 * applied. `exception` is null when none applies, else `{ ...overrides, reason }`.
 */
export function targetsFor(budgets, slug) {
  const exception = validateExceptions(budgets.exceptions)[slug] ?? null;
  const pick = (key) => (exception && exception[key] !== undefined ? exception[key] : budgets[key]);
  return {
    exception,
    lod1: { triangles: pick('lod1Triangles'), bytes: pick('lod1Bytes') },
    lod0: { triangles: pick('lod0Triangles'), bytes: pick('lod0Bytes') },
    frame: { triangles: pick('lod0Triangles'), bytes: pick('keyframeBytes') },
  };
}

/** The budgets as the manifest records them: the block minus its `_comment`-style annotations. */
export function manifestBudgets(meshes) {
  const out = {};
  for (const [key, value] of Object.entries(meshes)) {
    if (key.startsWith('_') || key === 'exceptions') continue; // exceptions are recorded on the entry they apply to
    out[key] = value;
  }
  return out;
}

// ──────────────────────────────────────────────
// Inputs
// ──────────────────────────────────────────────

const SLUG_RE = /^[a-z0-9][a-z0-9_-]*$/;

/**
 * Classify a raw file name.
 *   `<slug>.glb`                        → { kind: 'base', slug }
 *   `<slug>.<animation>.<index>.glb`    → { kind: 'frame', slug, animation, index }
 * Anything else (outputs such as `<slug>.lod1.glb`, manifest.json, hidden files)
 * → null.
 */
export function parseInputName(fileName) {
  if (!fileName.endsWith('.glb') || fileName.startsWith('.')) return null;
  const parts = fileName.slice(0, -'.glb'.length).split('.');
  if (parts.length === 1 && SLUG_RE.test(parts[0])) return { kind: 'base', slug: parts[0] };
  if (parts.length === 3 && SLUG_RE.test(parts[0]) && SLUG_RE.test(parts[1]) && /^\d+$/.test(parts[2])) {
    return { kind: 'frame', slug: parts[0], animation: parts[1], index: Number.parseInt(parts[2], 10) };
  }
  return null;
}

function compareInputs(a, b) {
  if (a.slug !== b.slug) return a.slug < b.slug ? -1 : 1;
  if (a.kind !== b.kind) return a.kind === 'base' ? -1 : 1;
  if (a.kind === 'frame') {
    if (a.animation !== b.animation) return a.animation < b.animation ? -1 : 1;
    return a.index - b.index;
  }
  return 0;
}

/** Every input in the input directory, in a stable order. Legacy mode accepts base files only. */
export function discoverInputs(ctx) {
  if (!fs.existsSync(ctx.inDir)) return [];
  const inputs = [];
  for (const name of fs.readdirSync(ctx.inDir)) {
    const parsed = parseInputName(name);
    if (!parsed) continue;
    if (ctx.legacyMode && parsed.kind !== 'base') continue;
    inputs.push({ ...parsed, file: path.join(ctx.inDir, name), name });
  }
  return inputs.sort(compareInputs);
}

// ──────────────────────────────────────────────
// lod0 selection
// ──────────────────────────────────────────────

/**
 * Slugs that get a lod0 under `--lod0 hero`: `apps/landing/models.hero.json`
 * (a JSON array of slugs, or `{ "slugs": [...] }`) when it exists, else every
 * manifest under `projects/*` that declares a top-level `animations` array.
 */
export function heroSlugs(ctx) {
  if (fs.existsSync(ctx.heroFile)) {
    const parsed = JSON.parse(fs.readFileSync(ctx.heroFile, 'utf8'));
    const list = Array.isArray(parsed) ? parsed : parsed && Array.isArray(parsed.slugs) ? parsed.slugs : null;
    if (!list) throw new UsageError(`${ctx.heroFile} must be a JSON array of slugs or { "slugs": [...] }`);
    return new Set(list.map(String));
  }
  const slugs = new Set();
  if (!fs.existsSync(ctx.projectsDir)) return slugs;
  for (const entry of fs.readdirSync(ctx.projectsDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const file = path.join(ctx.projectsDir, entry.name, 'project.json');
    if (!fs.existsSync(file)) continue;
    try {
      const data = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (Array.isArray(data.animations) && data.animations.length > 0) slugs.add(entry.name);
    } catch {
      /* an unreadable manifest is validate_manifests.py's problem, not this lane's */
    }
  }
  return slugs;
}

/** Resolve `--lod0` against the slugs that actually have a base input. */
export function resolveLod0Selection(spec, baseSlugs, ctx) {
  const mode = spec ?? (baseSlugs.length <= LOD0_ALL_MAX_INPUTS ? 'all' : 'hero');
  if (mode === 'all') return { mode, slugs: new Set(baseSlugs) };
  if (mode === 'none') return { mode, slugs: new Set() };
  if (mode === 'hero') {
    const hero = heroSlugs(ctx);
    return { mode, slugs: new Set(baseSlugs.filter((s) => hero.has(s))) };
  }
  const wanted = mode.split(',').map((s) => s.trim()).filter(Boolean);
  if (!wanted.length) throw new UsageError(`--lod0 needs all, hero, none or a comma-separated list of slugs`);
  const known = new Set(baseSlugs);
  return { mode: 'list', slugs: new Set(wanted.filter((s) => known.has(s))), unknown: wanted.filter((s) => !known.has(s)) };
}

// ──────────────────────────────────────────────
// Geometry
// ──────────────────────────────────────────────

function triangleCount(doc, core) {
  let count = 0;
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const prim of mesh.listPrimitives()) {
      if (prim.getMode() !== core.Primitive.Mode.TRIANGLES) continue;
      const indices = prim.getIndices();
      const n = indices ? indices.getCount() : prim.getAttribute('POSITION').getCount();
      count += Math.floor(n / 3);
    }
  }
  return count;
}

function vertexCount(doc) {
  let count = 0;
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const prim of mesh.listPrimitives()) count += prim.getAttribute('POSITION').getCount();
  }
  return count;
}

/** Column-major 4x4 × (x, y, z, 1). */
function transformPoint(m, x, y, z) {
  const w = m[3] * x + m[7] * y + m[11] * z + m[15] || 1;
  return [
    (m[0] * x + m[4] * y + m[8] * z + m[12]) / w,
    (m[1] * x + m[5] * y + m[9] * z + m[13]) / w,
    (m[2] * x + m[6] * y + m[10] * z + m[14]) / w,
  ];
}

function determinant3(m) {
  return (
    m[0] * (m[5] * m[10] - m[9] * m[6]) -
    m[4] * (m[1] * m[10] - m[9] * m[2]) +
    m[8] * (m[1] * m[6] - m[5] * m[2])
  );
}

/**
 * Bake every triangle primitive reachable from the scene into one world-space
 * triangle soup. This is the "merge/flatten meshes, drop materials" step: the
 * result is a fresh Document holding a single POSITION accessor, one index
 * accessor, one primitive — no material, no normals, no extension, no extras.
 * Instanced meshes are copied once per node; mirrored nodes get their winding
 * flipped so the page's back-face culling still agrees.
 */
async function bakeToSoup(srcDoc, deps) {
  const { core, functions } = deps;
  // Quantized inputs (KHR_mesh_quantization) become plain floats first, so the
  // arrays below are Float32 and the baked positions are exact.
  await srcDoc.transform(functions.dequantize());

  const root = srcDoc.getRoot();
  const scenes = root.getDefaultScene() ? [root.getDefaultScene()] : root.listScenes();
  const chunks = [];
  let total = 0;
  let skippedPrimitives = 0;

  for (const scene of scenes) {
    scene.traverse((node) => {
      const mesh = node.getMesh();
      if (!mesh) return;
      const matrix = node.getWorldMatrix();
      const mirrored = determinant3(matrix) < 0;
      for (const prim of mesh.listPrimitives()) {
        const position = prim.getAttribute('POSITION');
        if (!position || prim.getMode() !== core.Primitive.Mode.TRIANGLES) {
          skippedPrimitives += 1;
          continue;
        }
        const src = position.getArray();
        const count = position.getCount();
        const positions = new Float32Array(count * 3);
        for (let i = 0; i < count; i += 1) {
          const [x, y, z] = transformPoint(matrix, src[i * 3], src[i * 3 + 1], src[i * 3 + 2]);
          positions[i * 3] = x;
          positions[i * 3 + 1] = y;
          positions[i * 3 + 2] = z;
        }
        const srcIndices = prim.getIndices();
        const indexCount = srcIndices ? srcIndices.getCount() : count;
        const triCount = Math.floor(indexCount / 3);
        const indices = new Uint32Array(triCount * 3);
        for (let t = 0; t < triCount; t += 1) {
          const a = srcIndices ? srcIndices.getScalar(t * 3) : t * 3;
          const b = srcIndices ? srcIndices.getScalar(t * 3 + 1) : t * 3 + 1;
          const c = srcIndices ? srcIndices.getScalar(t * 3 + 2) : t * 3 + 2;
          indices[t * 3] = a;
          indices[t * 3 + 1] = mirrored ? c : b;
          indices[t * 3 + 2] = mirrored ? b : c;
        }
        chunks.push({ positions, indices, count });
        total += count;
      }
    });
  }

  const positions = new Float32Array(total * 3);
  const indexTotal = chunks.reduce((n, c) => n + c.indices.length, 0);
  const indices = new Uint32Array(indexTotal);
  let vOffset = 0;
  let iOffset = 0;
  for (const chunk of chunks) {
    positions.set(chunk.positions, vOffset * 3);
    for (let i = 0; i < chunk.indices.length; i += 1) indices[iOffset + i] = chunk.indices[i] + vOffset;
    vOffset += chunk.count;
    iOffset += chunk.indices.length;
  }

  const doc = new core.Document().setLogger(new core.Logger(core.Logger.Verbosity.SILENT));
  const buffer = doc.createBuffer();
  const positionAccessor = doc.createAccessor().setType('VEC3').setArray(positions).setBuffer(buffer);
  const indexAccessor = doc.createAccessor().setType('SCALAR').setArray(indices).setBuffer(buffer);
  const prim = doc
    .createPrimitive()
    .setMode(core.Primitive.Mode.TRIANGLES)
    .setAttribute('POSITION', positionAccessor)
    .setIndices(indexAccessor);
  const mesh = doc.createMesh().addPrimitive(prim);
  const node = doc.createNode().setMesh(mesh);
  doc.createScene().addChild(node);
  doc.getRoot().setDefaultScene(doc.getRoot().listScenes()[0]);

  // Bitwise weld: STL- and tessellator-derived meshes repeat shared vertices
  // exactly, so this both shrinks the file and gives the simplifier real
  // topology to collapse across.
  await doc.transform(functions.weld());
  return { doc, triangles: triangleCount(doc, core), skippedPrimitives };
}

/** `Document.clone()` left the core in v4; the functions package clones, and the clone needs its own silent logger. */
function cloneSilently(doc, { core, functions }) {
  return functions.cloneDocument(doc).setLogger(new core.Logger(core.Logger.Verbosity.SILENT));
}

/**
 * Simplify a copy of `prepared` down to `target` triangles, loosening the error
 * bound step by step. Returns the first result under the target, or the
 * lowest-triangle result the schedule could reach.
 */
async function simplifyTo(prepared, target, deps) {
  const { core, functions, MeshoptSimplifier } = deps;
  const current = triangleCount(prepared, core);
  if (current <= target) return { doc: cloneSilently(prepared, deps), triangles: current, reached: true, error: 0 };
  let best = null;
  for (const error of ERROR_SCHEDULE) {
    const doc = cloneSilently(prepared, deps);
    await doc.transform(
      functions.simplify({ simplifier: MeshoptSimplifier, ratio: target / current, error, lockBorder: false }),
    );
    const triangles = triangleCount(doc, core);
    if (!best || triangles < best.triangles) best = { doc, triangles, reached: triangles <= target, error };
    if (triangles <= target) break;
  }
  return best;
}

/** Quantize + meshopt-compress a copy of `doc` and serialize it as a GLB. */
async function encode(doc, deps) {
  const { functions, io, MeshoptEncoder } = deps;
  const out = cloneSilently(doc, deps);
  await out.transform(functions.meshopt({ encoder: MeshoptEncoder, level: 'medium', quantizePosition: POSITION_BITS }));
  return io.writeBinary(out);
}

/**
 * Build one output for `prepared` under `{ triangles, bytes }`. The triangle
 * budget drives the simplifier; when the encoded file is still over the byte
 * budget the triangle target is lowered proportionally, a few passes, down to
 * MIN_TRIANGLES.
 */
export async function buildLod(prepared, target, deps) {
  const { core } = deps;
  let triangleTarget = target.triangles;
  let result = null;
  for (let pass = 0; pass < MAX_BYTE_PASSES; pass += 1) {
    const simplified = await simplifyTo(prepared, triangleTarget, deps);
    const bytes = await encode(simplified.doc, deps);
    result = {
      bytes,
      triangles: simplified.triangles,
      vertices: vertexCount(simplified.doc),
      reachedTriangleBudget: simplified.triangles <= target.triangles,
      simplifierError: simplified.error,
      byteCapped: triangleTarget < target.triangles,
      withinBytes: bytes.length <= target.bytes,
    };
    if (result.withinBytes || simplified.triangles <= MIN_TRIANGLES || !simplified.reached) break;
    const next = Math.floor(simplified.triangles * (target.bytes / bytes.length) * 0.9);
    triangleTarget = Math.max(MIN_TRIANGLES, Math.min(next, simplified.triangles - 1));
  }
  void core;
  return result;
}

/**
 * Optimize one raw GLB (as bytes) into the requested targets.
 * `targets` is `{ lod1?: {triangles, bytes}, lod0?: {...}, frame?: {...} }`.
 */
export async function optimizeGlb(rawBytes, targets, deps) {
  const { core, io } = deps;
  const srcDoc = await io.readBinary(rawBytes instanceof Uint8Array ? rawBytes : new Uint8Array(rawBytes));
  const before = { bytes: rawBytes.length, triangles: triangleCount(srcDoc, core) };
  const { doc: prepared, triangles: preparedTriangles, skippedPrimitives } = await bakeToSoup(srcDoc, deps);
  if (preparedTriangles === 0) throw new Error('no triangle geometry found');

  const outputs = {};
  if (targets.lod1) outputs.lod1 = await buildLod(prepared, targets.lod1, deps);
  if (targets.lod0) {
    // lod0 exists to carry more detail than lod1. When lod1 already holds every
    // triangle the raw render had, a lod0 would be the same bytes under a second
    // name, so it is skipped and the manifest simply carries no lod0.
    if (outputs.lod1 && outputs.lod1.triangles >= preparedTriangles) outputs.lod0Skipped = 'already complete at lod1';
    else outputs.lod0 = await buildLod(prepared, targets.lod0, deps);
  }
  if (targets.frame) outputs.frame = await buildLod(prepared, targets.frame, deps);
  return { before, preparedTriangles, skippedPrimitives, outputs };
}

// ──────────────────────────────────────────────
// Manifest
// ──────────────────────────────────────────────

/** The commons pin: the commit the `projects` submodule has checked out, or null. */
export function detectCommonsPin(repo) {
  const attempts = [
    ['-C', path.join(repo, 'projects'), 'rev-parse', 'HEAD'],
    ['-C', repo, 'rev-parse', 'HEAD:projects'],
  ];
  for (const args of attempts) {
    try {
      const sha = execFileSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
      if (/^[0-9a-f]{40}$/.test(sha)) return sha;
    } catch {
      /* not a git checkout, or the submodule is not initialised */
    }
  }
  return null;
}

/** Second-precision ISO timestamp, like the v1 manifest carried. */
export function isoNow(now = new Date()) {
  return now.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

/**
 * The v2 manifest, with a stable key order. `entries` is a Map slug → { lod1?,
 * lod0?, frames: [] }, each value `{ file, bytes, triangles }` (frames also carry
 * `animation` and `index`).
 */
export function buildManifest({ generated, sourceKind, commonsPin, budgets, entries }) {
  const models = [];
  for (const slug of [...entries.keys()].sort()) {
    const entry = entries.get(slug);
    const files = [entry.lod1, entry.lod0, ...entry.frames].filter(Boolean);
    if (!files.length) continue;
    const model = { slug, size: Math.min(...files.map((f) => f.bytes)) };
    // A budget kept by exception says so on the entry: the overrides and why.
    if (entry.budget) model.budget = { ...entry.budget };
    if (entry.lod1) model.lod1 = { file: entry.lod1.file, bytes: entry.lod1.bytes, triangles: entry.lod1.triangles };
    if (entry.lod0) model.lod0 = { file: entry.lod0.file, bytes: entry.lod0.bytes, triangles: entry.lod0.triangles };
    if (entry.frames.length) {
      model.frames = [...entry.frames]
        .sort((a, b) => (a.animation === b.animation ? a.index - b.index : a.animation < b.animation ? -1 : 1))
        .map((f) => ({ animation: f.animation, index: f.index, file: f.file, bytes: f.bytes, triangles: f.triangles }));
    }
    models.push(model);
  }
  return {
    version: MANIFEST_VERSION,
    generated,
    generator: GENERATOR,
    source: { kind: sourceKind, commons_pin: commonsPin },
    budgets: manifestBudgets(budgets),
    models,
  };
}

export function serializeManifest(manifest) {
  return `${JSON.stringify(manifest, null, 2)}\n`;
}

// ──────────────────────────────────────────────
// Report
// ──────────────────────────────────────────────

const fmtInt = (n) => Number(n).toLocaleString('en-US');
const pct = (bytes, budget) => `${Math.round(((bytes - budget) / budget) * 100)}%`;

function statusOf(row) {
  if (row.sameAs) return `= ${row.sameAs}`;
  if (!row.withinBytes) return `OVER +${pct(row.afterBytes, row.budgetBytes)}`;
  const notes = [];
  if (row.exception) notes.push('by exception');
  if (row.byteCapped) notes.push('byte-capped');
  if (!row.reachedTriangleBudget) notes.push('triangles over budget');
  return notes.length ? `ok (${notes.join(', ')})` : 'ok';
}

/** Fixed-width text table for the terminal. */
export function renderReport(rows) {
  const header = ['slug', 'target', 'before B', 'before tris', 'after B', 'after tris', 'budget B', 'status'];
  const body = rows.map((r) => [
    r.slug,
    r.target,
    fmtInt(r.beforeBytes),
    fmtInt(r.beforeTriangles),
    fmtInt(r.afterBytes),
    fmtInt(r.afterTriangles),
    fmtInt(r.budgetBytes),
    statusOf(r),
  ]);
  const widths = header.map((h, i) => Math.max(h.length, ...body.map((b) => b[i].length)));
  const line = (cells) =>
    cells
      .map((c, i) => (i >= 2 && i <= 6 ? c.padStart(widths[i]) : i === cells.length - 1 ? c : c.padEnd(widths[i])))
      .join('  ');
  return [line(header), widths.map((w) => '-'.repeat(w)).join('  '), ...body.map(line)].join('\n');
}

/** Markdown table for $GITHUB_STEP_SUMMARY. */
export function renderMarkdownReport(rows, totals) {
  const lines = [
    '### Commons models',
    '',
    `${fmtInt(totals.inputs)} input(s) → ${fmtInt(totals.outputs)} output file(s); ${fmtInt(totals.beforeBytes)} B raw → ${fmtInt(totals.afterBytes)} B on disk.`,
    '',
    '| slug | target | before (B / tris) | after (B / tris) | budget (B) | status |',
    '| :-- | :-- | --: | --: | --: | :-- |',
    ...rows.map(
      (r) =>
        `| ${r.slug} | ${r.target} | ${fmtInt(r.beforeBytes)} / ${fmtInt(r.beforeTriangles)} | ${fmtInt(r.afterBytes)} / ${fmtInt(r.afterTriangles)} | ${fmtInt(r.budgetBytes)} | ${statusOf(r)} |`,
    ),
    '',
  ];
  return lines.join('\n');
}

// ──────────────────────────────────────────────
// Run
// ──────────────────────────────────────────────

function outputNameFor(input, target) {
  if (input.kind === 'frame') return input.name;
  return `${input.slug}.${target}.glb`;
}

function isOutputName(name) {
  return /\.lod[01]\.glb$/.test(name) || (parseInputName(name) || {}).kind === 'frame';
}

function readExistingGenerated(manifestFile) {
  try {
    const parsed = JSON.parse(fs.readFileSync(manifestFile, 'utf8'));
    return typeof parsed.generated === 'string' ? parsed.generated : null;
  } catch {
    return null;
  }
}

function bytesEqual(a, b) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) if (a[i] !== b[i]) return false;
  return true;
}

/**
 * CLI body. Returns an exit code instead of calling process.exit, so the test
 * suite can drive it directly.
 */
export async function run({
  argv = process.argv.slice(2),
  repo = DEFAULT_REPO,
  env = process.env,
  cwd = process.cwd(),
  log = console.log,
  logError = console.error,
  now = new Date(),
} = {}) {
  let opts;
  try {
    opts = parseArgs(argv);
  } catch (err) {
    logError(err.message);
    logError(USAGE);
    return EXIT_USAGE;
  }
  if (opts.help) {
    log(USAGE);
    return EXIT_OK;
  }
  if (opts.repo) repo = path.resolve(cwd, opts.repo);
  const ctx = makeContext({ repo, opts, cwd });
  const info = opts.quiet ? () => {} : log;

  let budgets;
  try {
    budgets = loadBudgets(ctx.budgetsFile);
  } catch (err) {
    logError(err.message);
    return EXIT_USAGE;
  }

  const inputs = discoverInputs(ctx);
  if (!inputs.length) {
    logError(
      ctx.legacyMode
        ? `No inputs: neither ${path.join(path.dirname(ctx.inDir), 'raw')} nor legacy <slug>.glb files in ${ctx.inDir}. Render the cartridges first (.github/workflows/prerender-commons.yml) or pass --in.`
        : `No inputs found in ${ctx.inDir}. Expected <slug>.glb or <slug>.<animation>.<index>.glb files.`,
    );
    return EXIT_USAGE;
  }

  const baseSlugs = inputs.filter((i) => i.kind === 'base').map((i) => i.slug);
  let lod0;
  try {
    lod0 = resolveLod0Selection(opts.lod0, baseSlugs, ctx);
  } catch (err) {
    logError(err.message);
    return EXIT_USAGE;
  }
  if (lod0.unknown && lod0.unknown.length) logError(`WARNING: --lod0 names slugs with no input: ${lod0.unknown.join(', ')}`);
  for (const input of inputs) {
    if (input.kind === 'frame' && !baseSlugs.includes(input.slug)) {
      logError(`WARNING: ${input.name} is a keyframe for a slug with no base render (${input.slug}.glb)`);
    }
  }

  const deps = await loadDeps();
  const sourceKind = ctx.legacyMode ? 'legacy-glb' : 'render-api';
  info(
    `${sourceKind === 'legacy-glb' ? 'Legacy inputs' : 'Raw inputs'}: ${inputs.length} file(s) in ${path.relative(cwd, ctx.inDir) || '.'} → ${path.relative(cwd, ctx.outDir) || '.'} (lod0: ${lod0.mode}, ${lod0.slugs.size} slug(s))`,
  );

  const targetsCache = new Map();
  const targetsOf = (slug) => {
    if (!targetsCache.has(slug)) targetsCache.set(slug, targetsFor(budgets, slug));
    return targetsCache.get(slug);
  };

  const planned = []; // { name, bytes, row }
  // `${slug}:${sha256}` → the output already planned with exactly these bytes.
  // A keyframe that comes out byte-identical to the base or to an earlier
  // frame (a sweep parked on the same grid step, run 35460054814: 11 of 245)
  // is not written again; its manifest entry points at the file that exists.
  const seenBytes = new Map();
  const rows = [];
  const failures = [];
  let rawBytesTotal = 0;
  const entries = new Map();
  const entryFor = (slug) => {
    if (!entries.has(slug)) {
      const { exception } = targetsOf(slug);
      entries.set(slug, { lod1: null, lod0: null, frames: [], budget: exception });
    }
    return entries.get(slug);
  };

  for (const input of inputs) {
    let rawBytes;
    let result;
    try {
      rawBytes = fs.readFileSync(input.file);
      rawBytesTotal += rawBytes.length;
      const targets = targetsOf(input.slug);
      const wanted =
        input.kind === 'frame'
          ? { frame: targets.frame }
          : { lod1: targets.lod1, ...(lod0.slugs.has(input.slug) ? { lod0: targets.lod0 } : {}) };
      result = await optimizeGlb(rawBytes, wanted, deps);
    } catch (err) {
      failures.push(`${input.name}: ${err.message}`);
      logError(`FAILED ${input.name}: ${err.message}`);
      continue;
    }
    if (result.skippedPrimitives) {
      logError(`WARNING: ${input.name}: dropped ${result.skippedPrimitives} non-triangle primitive(s)`);
    }
    if (result.outputs.lod0Skipped) info(`  ${input.slug}: lod0 skipped (${result.outputs.lod0Skipped})`);

    for (const target of ['lod1', 'lod0', 'frame']) {
      const built = result.outputs[target];
      if (!built) continue;
      const name = outputNameFor(input, target);
      const targets = targetsOf(input.slug);
      const budget = targets[target];
      const digest = `${input.slug}:${createHash('sha256').update(built.bytes).digest('hex')}`;
      const sameAs = target === 'frame' ? (seenBytes.get(digest) ?? null) : null;
      if (!seenBytes.has(digest)) seenBytes.set(digest, name);
      const row = {
        slug: input.slug,
        target: input.kind === 'frame' ? `${input.animation}#${input.index}` : target,
        file: name,
        beforeBytes: result.before.bytes,
        beforeTriangles: result.before.triangles,
        afterBytes: built.bytes.length,
        afterTriangles: built.triangles,
        budgetBytes: budget.bytes,
        budgetTriangles: budget.triangles,
        withinBytes: built.withinBytes,
        byteCapped: built.byteCapped,
        reachedTriangleBudget: built.reachedTriangleBudget,
        exception: targets.exception ? targets.exception.reason : null,
        sameAs,
      };
      rows.push(row);
      if (!sameAs) planned.push({ name, bytes: built.bytes, row });
      const record = { file: sameAs ?? name, bytes: built.bytes.length, triangles: built.triangles };
      const entry = entryFor(input.slug);
      if (target === 'frame') entry.frames.push({ ...record, animation: input.animation, index: input.index });
      else entry[target] = record;
      info(
        sameAs
          ? `  ${name.padEnd(44)} = ${sameAs} (identical bytes; not written)`
          : `  ${name.padEnd(44)} ${fmtInt(result.before.bytes).padStart(10)} B → ${fmtInt(built.bytes.length).padStart(8)} B  ${fmtInt(result.before.triangles).padStart(8)} → ${fmtInt(built.triangles).padStart(6)} tris  ${statusOf(row)}`,
      );
    }
  }

  // Manifest
  const commonsPin =
    opts['commons-pin'] === 'none' ? null : opts['commons-pin'] ? opts['commons-pin'] : detectCommonsPin(repo);
  const generated = opts.generated ?? (opts.check ? readExistingGenerated(ctx.manifestFile) : null) ?? isoNow(now);
  const manifest = buildManifest({ generated, sourceKind, commonsPin, budgets, entries });
  const manifestText = serializeManifest(manifest);

  // Clean plan: stale outputs with no input any more, and consumed legacy files.
  const expected = new Set(planned.map((p) => p.name));
  const removals = [];
  if (fs.existsSync(ctx.outDir)) {
    for (const name of fs.readdirSync(ctx.outDir)) {
      if (isOutputName(name) && !expected.has(name)) removals.push(name);
    }
  }
  if (ctx.legacyMode) {
    for (const input of inputs) {
      if (entries.get(input.slug) && entries.get(input.slug).lod1) removals.push(input.name);
    }
  }
  removals.sort();

  // --check: compare, write nothing.
  if (opts.check) {
    const drift = [];
    for (const { name, bytes } of planned) {
      const file = path.join(ctx.outDir, name);
      if (!fs.existsSync(file)) drift.push(`missing: ${name}`);
      else if (!bytesEqual(fs.readFileSync(file), bytes)) drift.push(`differs: ${name}`);
    }
    const existingManifest = fs.existsSync(ctx.manifestFile) ? fs.readFileSync(ctx.manifestFile, 'utf8') : null;
    if (existingManifest === null) drift.push('missing: manifest.json');
    else if (existingManifest !== manifestText) drift.push('differs: manifest.json');
    if (opts.clean) for (const name of removals) drift.push(`stale (would be removed): ${name}`);
    if (failures.length) {
      logError(`${failures.length} input(s) could not be processed:`);
      for (const f of failures) logError(`  ${f}`);
      return EXIT_FAILED;
    }
    if (drift.length) {
      logError(`DRIFT — ${path.relative(cwd, ctx.outDir) || '.'} does not match the inputs:`);
      for (const d of drift) logError(`  ${d}`);
      logError('Run `npm run models:optimize` (from apps/landing) with the same inputs and commit the result.');
      return EXIT_DRIFT;
    }
    log(`models are up to date (${planned.length} file(s) + manifest.json).`);
    return EXIT_OK;
  }

  // Write.
  fs.mkdirSync(ctx.outDir, { recursive: true });
  for (const { name, bytes } of planned) fs.writeFileSync(path.join(ctx.outDir, name), bytes);
  fs.writeFileSync(ctx.manifestFile, manifestText, 'utf8');
  if (opts.clean) {
    for (const name of removals) {
      fs.rmSync(path.join(ctx.outDir, name), { force: true });
      info(`  removed ${name}`);
    }
  } else if (removals.length) {
    logError(`NOTE: ${removals.length} file(s) would be removed by --clean: ${removals.join(', ')}`);
  }

  // Report.
  const totals = {
    inputs: inputs.length,
    outputs: planned.length,
    beforeBytes: rawBytesTotal,
    afterBytes: planned.reduce((n, p) => n + p.bytes.length, 0),
  };
  log('');
  log(renderReport(rows));
  log('');
  log(
    `${fmtInt(totals.inputs)} input(s), ${fmtInt(totals.beforeBytes)} B → ${fmtInt(totals.outputs)} output(s), ${fmtInt(totals.afterBytes)} B; manifest v${MANIFEST_VERSION} generated ${generated} (commons pin ${commonsPin ?? 'unknown'}).`,
  );
  if (env.GITHUB_STEP_SUMMARY) {
    fs.appendFileSync(env.GITHUB_STEP_SUMMARY, `${renderMarkdownReport(rows, totals)}\n`);
  }

  // Aliased frames are the same bytes as a row already counted.
  const written = rows.filter((r) => !r.sameAs);
  const offenders = written.filter((r) => !r.withinBytes);
  const shortfalls = written.filter((r) => r.withinBytes && !r.reachedTriangleBudget);
  if (shortfalls.length) {
    logError(`NOTE: ${shortfalls.length} output(s) stayed over the triangle budget (topology limits the simplifier): ${shortfalls.map((r) => r.file).join(', ')}`);
  }
  if (offenders.length) {
    logError(`${opts.strict ? 'ERROR' : 'WARNING'}: ${offenders.length} output(s) over their byte budget (written anyway):`);
    for (const r of offenders) logError(`  ${r.file}: ${fmtInt(r.afterBytes)} B > ${fmtInt(r.budgetBytes)} B (${r.afterTriangles} tris)`);
  }
  if (failures.length) {
    logError(`${failures.length} input(s) could not be processed:`);
    for (const f of failures) logError(`  ${f}`);
    return EXIT_FAILED;
  }
  if (opts.strict && offenders.length) return EXIT_BUDGET;
  return EXIT_OK;
}

// Only self-execute as a CLI, so the test suite can import the functions above.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(await run());
}
