#!/usr/bin/env node
/**
 * Generate `apps/landing/src/data/projects.ts` from the project manifests.
 *
 * The landing gallery used to be driven by a hand-maintained array of ~28 entries
 * that drifted ~9x out of sync with the real catalog (`projects/<slug>/project.json`).
 * This script regenerates that array from the manifests so the gallery reflects the
 * full Commons and stays in sync: re-run it (`npm run gen:projects`) whenever objects
 * are added or their manifests change.
 *
 * It only reads Node built-ins (fs, path, url) and writes a single TS file whose
 * exported type names/shape match what the gallery components already import.
 *
 * Extraction mirrors `scripts/dev/generate-placeholder-thumbnails.py` so the two
 * stay consistent (same hyperobject resolution, same domain / geometry_type source):
 *   - The manifests split the hyperobject data across two blocks: the rich metadata
 *     (`domain`, `cdg_interfaces`, …) lives in the TOP-LEVEL `hyperobject`, while the
 *     `is_hyperobject: true` flag lives in `project.hyperobject`. Both are consulted.
 *   - `domain` + `cdg_interfaces[].geometry_type` are read from whichever block has
 *     them (top-level preferred).
 *   - `name` may be a plain string or an { en, es } i18n object.
 *
 * ── Two invariants this script is responsible for ──────────────────────────────
 *
 * 1. PRIVATE CARTRIDGES NEVER REACH THE PUBLIC GALLERY.
 *    The API already hides them from `/api/projects`
 *    (`apps/api/services/core/project_access.py::filter_visible_projects`). The
 *    landing gallery is a *second*, statically generated surface over the same
 *    manifests, so it needs the same rule or it re-publishes the name, the
 *    description and a Studio link for a cartridge the API refuses to serve.
 *    Privacy is read from the same two signals the backend uses:
 *      - `access_control.view == "private"` in the manifest (the cartridge's own
 *        statement — travels with the project), and
 *      - the `PRIVATE_PROJECTS` env var (comma-separated slugs), the same shape
 *        `k8s/production/yantra4d-backend-deployment.yaml` sets.
 *    `BUILTIN_PRIVATE_SLUGS` below is a *floor*, not a default an empty env var
 *    can clear: `PRIVATE_PROJECTS` only ever adds. Making a client cartridge
 *    public has to be a reviewed edit here, not an unset variable in whatever
 *    shell happens to run the generator.
 *
 *    `project.unlisted` is deliberately NOT consulted — unlisted means "hidden
 *    from *API* listings but reachable by direct URL", which is a different
 *    thing from private, and the gallery's treatment of it is unchanged.
 *
 * 2. AN INCOMPLETE CHECKOUT NEVER PRODUCES A "COMPLETE" FILE.
 *    36 of the cartridges live in git submodules. Run in a checkout without
 *    them, this script used to silently emit a shorter list and overwrite the
 *    good one — the failure mode that left the committed file 138 entries
 *    short. Now every `projects/*` submodule declared in `.gitmodules` must
 *    have a `project.json` on disk before anything is written, and the run
 *    fails otherwise unless `--allow-partial` says the caller means it.
 *    Submodules marked `update = none` (the client-private cartridges) are
 *    EXPECTED to be absent: a recursive checkout skips them by design, so their
 *    absence is never an incomplete checkout.
 *
 * Usage:
 *   node scripts/dev/generate-landing-projects.mjs
 *   node scripts/dev/generate-landing-projects.mjs --check           # fail if stale
 *   node scripts/dev/generate-landing-projects.mjs --allow-partial   # write anyway
 *
 * Exit codes:
 *   0  success / up to date
 *   1  drift: the committed file differs from a freshly generated one (--check)
 *   2  incomplete checkout: a public cartridge submodule is missing
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const DEFAULT_REPO = path.resolve(__dirname, '..', '..');

/** Exit codes, named so the workflows and the tests agree on them. */
export const EXIT_OK = 0;
export const EXIT_DRIFT = 1;
export const EXIT_INCOMPLETE = 2;

/**
 * Slugs that are private regardless of manifest or environment.
 *
 * Mirrors the `PRIVATE_PROJECTS` value in
 * `k8s/production/yantra4d-backend-deployment.yaml`. Kept as a floor rather
 * than a default so that a generator run with `PRIVATE_PROJECTS=""` — an empty
 * CI env, a developer shell, a container that forgot the variable — still
 * excludes them. Fail closed.
 */
export const BUILTIN_PRIVATE_SLUGS = ['tablaco', 'tablaco-v2'];

/**
 * Map a manifest `hyperobject.domain` onto the landing `HyperobjectDomain` enum.
 * The landing enum has no direct 'infrastructure' / 'soft-robotics' members, so
 * both fold into 'industrial'. There is no 'culture' domain in the manifests, so it
 * is never produced here (the previous hand-curated 'culture' entry is dropped by the
 * full regen, per the task). Unknown / empty domains yield `undefined`.
 */
const DOMAIN_MAP = {
  household: 'household',
  industrial: 'industrial',
  medical: 'medical',
  commercial: 'commercial',
  hybrid: 'hybrid',
  infrastructure: 'industrial',
  'soft-robotics': 'industrial',
};

// Geometry types that read as physical storage/containment features.
const STORAGE_GEOMETRY = new Set(['grid', 'rail', 'socket', 'pocket']);
// Geometry types that read as machined / mechanical interfaces.
const MECHANICAL_GEOMETRY = new Set(['bolt_pattern', 'thread', 'profile', 'snap']);
// Geometry types that read as freeform / sculptural surfaces.
const ART_GEOMETRY = new Set(['spline', 'surface']);

// Tag buckets used as tie-breakers when geometry/domain are ambiguous.
const ART_TAGS = new Set([
  'art', 'generative', 'sculpture', 'voronoi', 'fractal', 'vase', 'decor',
  'decorative', 'ornament', 'planter', 'lamp', 'lampshade', 'parametric-art',
]);
const TABLETOP_TAGS = new Set([
  'tabletop', 'dice', 'mini', 'miniature', 'rpg', 'boardgame', 'board-game', 'game', 'gaming', 'token',
]);
const ELECTRONICS_TAGS = new Set([
  'electronics', 'pcb', 'led', 'enclosure', 'keycap', 'keycaps', 'keyboard',
  'arduino', 'raspberry-pi', 'circuit', 'wiring', 'cable', 'connector-electronic',
]);
const EDUCATION_TAGS = new Set([
  'education', 'educational', 'stem', 'teaching', 'lab', 'laboratory', 'science', 'classroom',
]);

/** Paths a run reads and writes, all derived from one repo root (tests point it at a fixture). */
export function makeContext(repo = DEFAULT_REPO) {
  return {
    repo,
    projectsDir: path.join(repo, 'projects'),
    publicDir: path.join(repo, 'apps', 'landing', 'public'),
    outFile: path.join(repo, 'apps', 'landing', 'src', 'data', 'projects.ts'),
  };
}

// ──────────────────────────────────────────────
// Privacy
// ──────────────────────────────────────────────

/**
 * Every slug this run must treat as private: the built-in floor plus whatever
 * `PRIVATE_PROJECTS` adds. Same comma-separated shape as the backend env var.
 */
export function privateSlugs(env = process.env) {
  const slugs = new Set(BUILTIN_PRIVATE_SLUGS.map((s) => s.toLowerCase()));
  for (const chunk of String(env.PRIVATE_PROJECTS ?? '').split(',')) {
    const slug = chunk.trim().toLowerCase();
    if (slug) slugs.add(slug);
  }
  return slugs;
}

/**
 * True when the manifest itself declares `access_control.view == "private"`.
 * The block is top-level in the schema; `project.access_control` is also read
 * because reading one extra place can only ever hide more, never less.
 */
export function isPrivateManifest(data) {
  if (!data || typeof data !== 'object') return false;
  const blocks = [data.access_control, data.project && data.project.access_control];
  return blocks.some((b) => b && typeof b === 'object' && b.view === 'private');
}

// ──────────────────────────────────────────────
// Checkout completeness
// ──────────────────────────────────────────────

/** Minimal `.gitmodules` reader: `[{ path, update }]` in declaration order. */
export function parseGitmodules(text) {
  const entries = [];
  let current = null;
  for (const rawLine of String(text ?? '').split('\n')) {
    const line = rawLine.trim();
    if (/^\[submodule\b/.test(line)) {
      current = { path: '', update: '' };
      entries.push(current);
      continue;
    }
    if (!current) continue;
    const match = /^([A-Za-z0-9_.-]+)\s*=\s*(.*)$/.exec(line);
    if (!match) continue;
    if (match[1] === 'path') current.path = match[2].trim();
    else if (match[1] === 'update') current.update = match[2].trim();
  }
  return entries.filter((e) => e.path);
}

/**
 * Cartridge submodules split by whether this checkout is supposed to contain them.
 *
 * `required` — public cartridges; a recursive checkout brings them in, so a
 *              missing one means the checkout is incomplete.
 * `expectedAbsent` — `update = none`; git skips these even recursively, which
 *              is exactly how the client-private cartridges stay out of public
 *              build contexts. Their absence is normal and must never be
 *              reported as an incomplete checkout.
 */
export function cartridgeSubmodules(repo = DEFAULT_REPO) {
  const file = path.join(repo, '.gitmodules');
  if (!fs.existsSync(file)) return { required: [], expectedAbsent: [] };
  const entries = parseGitmodules(fs.readFileSync(file, 'utf8'))
    .filter((e) => e.path.startsWith('projects/'));
  return {
    required: entries.filter((e) => e.update !== 'none').map((e) => e.path),
    expectedAbsent: entries.filter((e) => e.update === 'none').map((e) => e.path),
  };
}

/** Public cartridge submodules with no `project.json` on disk. Empty = complete. */
export function missingCartridges(repo = DEFAULT_REPO) {
  return cartridgeSubmodules(repo).required
    .filter((rel) => !fs.existsSync(path.join(repo, rel, 'project.json')));
}

// ──────────────────────────────────────────────
// Manifest extraction
// ──────────────────────────────────────────────

/** Read `name` which may be a string or an { en, es } i18n object. */
function i18nName(proj, slug) {
  const name = proj.name;
  if (name && typeof name === 'object') {
    return name.en || Object.values(name)[0] || slug;
  }
  return name || slug;
}

/**
 * Read a description field that may be a string or { en, es } object.
 * Returns only the first line so gallery cards stay single-line-ish (the manifest
 * descriptions often pack a second "Official Visualizer …" paragraph after \n\n).
 */
function firstLine(value) {
  if (!value) return '';
  const str = typeof value === 'object' ? (value.en || Object.values(value)[0] || '') : String(value);
  return str.split('\n')[0].trim();
}

function descriptions(proj) {
  const desc = proj.description;
  if (desc && typeof desc === 'object') {
    const en = firstLine(desc.en) || firstLine(Object.values(desc)[0]);
    const es = firstLine(desc.es) || en;
    return { en, es };
  }
  const en = firstLine(desc);
  return { en, es: en };
}

/**
 * Resolve the hyperobject metadata block (domain / cdg_interfaces), preferring the
 * top-level one and falling back to `project.hyperobject`. This is NOT where the
 * `is_hyperobject` flag reliably lives — see `isHyperobjectFlag`.
 */
function resolveHyperobject(data, proj) {
  const top = data.hyperobject;
  if (top && typeof top === 'object' && Object.keys(top).length) return top;
  const inner = proj.hyperobject;
  if (inner && typeof inner === 'object') return inner;
  return {};
}

/** True when either hyperobject block sets `is_hyperobject` truthy. */
function isHyperobjectFlag(data, proj) {
  const top = data.hyperobject;
  const inner = proj.hyperobject;
  return Boolean(
    (top && typeof top === 'object' && top.is_hyperobject) ||
      (inner && typeof inner === 'object' && inner.is_hyperobject),
  );
}

/** First geometry_type declared across the hyperobject's CDG interfaces. */
function firstGeometryType(ho) {
  const interfaces = Array.isArray(ho.cdg_interfaces) ? ho.cdg_interfaces : [];
  const types = interfaces
    .map((i) => i && i.geometry_type)
    .filter(Boolean)
    .sort();
  return types[0] || '';
}

/**
 * Derive a `ProjectCategory` deterministically from domain + first geometry_type + tags.
 *
 * Priority (first match wins), tuned to the real manifest distribution:
 *   1. explicit intent tags (electronics / tabletop / art) — most specific signal
 *   2. medical domain            → 'education' (clinical/teaching hardware)
 *   3. education tags            → 'education'
 *   4. storage geometry + household → 'storage'
 *   5. mechanical geometry + industrial/commercial → 'mechanical'
 *   6. art geometry or art tags  → 'art'
 *   7. storage geometry (any domain) → 'storage'
 *   8. household domain          → 'storage'  (household objects are mostly organizers)
 *   9. fallback                  → 'mechanical'
 */
function deriveCategory(domain, geometryType, tags) {
  const tagSet = new Set((tags || []).map((t) => String(t).toLowerCase()));
  const hasAny = (set) => [...tagSet].some((t) => set.has(t));

  if (hasAny(ELECTRONICS_TAGS)) return 'electronics';
  if (hasAny(TABLETOP_TAGS)) return 'tabletop';
  if (hasAny(ART_TAGS)) return 'art';

  if (domain === 'medical') return 'education';
  if (hasAny(EDUCATION_TAGS)) return 'education';

  if (STORAGE_GEOMETRY.has(geometryType) && domain === 'household') return 'storage';
  if (MECHANICAL_GEOMETRY.has(geometryType) && (domain === 'industrial' || domain === 'commercial')) {
    return 'mechanical';
  }
  if (ART_GEOMETRY.has(geometryType)) return 'art';

  if (STORAGE_GEOMETRY.has(geometryType)) return 'storage';
  if (domain === 'household') return 'storage';

  return 'mechanical';
}

/**
 * Resolve the thumbnail path. The manifest `thumbnail` usually points at
 * `/projects/<slug>.webp`, but only ~21 of those real renders exist; the rest were
 * never rendered. To avoid ~230 broken tiles we use the manifest thumbnail only when
 * the referenced asset actually exists under apps/landing/public, and otherwise fall
 * back to the guaranteed-present `/projects/<slug>.svg` placeholder.
 */
function resolveThumbnail(ctx, proj, slug) {
  const declared = proj.thumbnail;
  if (declared && declared.startsWith('/')) {
    const abs = path.join(ctx.publicDir, declared.replace(/^\//, ''));
    if (fs.existsSync(abs)) return declared;
  }
  return `/projects/${slug}.svg`;
}

/**
 * Walk `projects/`, yielding `{ dirName, slug, data, proj }` for every readable
 * manifest. Private cartridges are dropped here, once, so neither the gallery
 * list nor the commons figures below can accidentally include one.
 */
function readManifests(ctx, priv) {
  const entries = fs.existsSync(ctx.projectsDir)
    ? fs.readdirSync(ctx.projectsDir, { withFileTypes: true })
    : [];
  const manifests = [];
  let skippedNoManifest = 0;
  let skippedBad = 0;
  const skippedPrivate = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const manifestPath = path.join(ctx.projectsDir, entry.name, 'project.json');
    if (!fs.existsSync(manifestPath)) {
      skippedNoManifest += 1;
      continue;
    }

    let data;
    try {
      data = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    } catch {
      skippedBad += 1;
      continue;
    }

    const proj = data.project || {};
    const slug = proj.slug || entry.name;

    // Either identifier being on the private list is enough: a manifest whose
    // slug disagrees with its directory must not slip through on the mismatch.
    if (
      priv.has(String(slug).toLowerCase()) ||
      priv.has(entry.name.toLowerCase()) ||
      isPrivateManifest(data)
    ) {
      skippedPrivate.push(slug);
      continue;
    }

    manifests.push({ dirName: entry.name, slug, data, proj });
  }

  return { manifests, skippedNoManifest, skippedBad, skippedPrivate: skippedPrivate.sort() };
}

function collectProjects(ctx, priv) {
  const read = readManifests(ctx, priv);
  const projects = read.manifests.map(({ slug, data, proj }) => {
    const ho = resolveHyperobject(data, proj);
    const { en: description, es: descriptionEs } = descriptions(proj);
    const geometryType = firstGeometryType(ho);
    const domain = DOMAIN_MAP[ho.domain || ''];
    return {
      slug,
      name: i18nName(proj, slug),
      description,
      descriptionEs,
      category: deriveCategory(domain, geometryType, proj.tags),
      thumbnail: resolveThumbnail(ctx, proj, slug),
      isHyperobject: isHyperobjectFlag(data, proj),
      domain,
    };
  });
  return { ...read, projects };
}

/** hyperobjects first, then alphabetical by name (locale-aware, stable). */
function sortProjects(projects) {
  return [...projects].sort((a, b) => {
    if (a.isHyperobject !== b.isHyperobject) return a.isHyperobject ? -1 : 1;
    return a.name.localeCompare(b.name, 'en', { sensitivity: 'base' });
  });
}

function tsString(value) {
  // JSON.stringify yields a valid, correctly-escaped double-quoted TS string literal.
  return JSON.stringify(value ?? '');
}

function renderProject(p) {
  const fields = [
    `slug: ${tsString(p.slug)}`,
    `name: ${tsString(p.name)}`,
    `description: ${tsString(p.description)}`,
    `descriptionEs: ${tsString(p.descriptionEs)}`,
    `category: ${tsString(p.category)}`,
    `thumbnail: ${tsString(p.thumbnail)}`,
  ];
  if (p.isHyperobject) fields.push('isHyperobject: true');
  if (p.domain) fields.push(`domain: ${tsString(p.domain)}`);
  return `  { ${fields.join(', ')} },`;
}

/**
 * Commons figures the landing quotes, derived from the same manifests as the
 * project list. Hardcoded copy went stale by more than fifteenfold ("21
 * Projects" against a commons of 326) — numbers the page states about itself
 * are generated so they cannot drift again.
 *
 * Reads the same already-filtered manifests as the gallery, so a private
 * cartridge cannot leak here either: an interface count or a standards list is
 * a smaller disclosure than a card, but it is still a disclosure.
 */
function computeStats(ctx, manifests, projects) {
  const engines = new Set();
  const standards = new Set();
  const interfaceIds = new Set();
  let interfaceInstances = 0;
  let withInterfaces = 0;
  let stepCapable = 0;
  let cernLicensed = 0;

  for (const { data: manifest } of manifests) {
    const project = manifest.project ?? {};
    const ho = manifest.hyperobject ?? project.hyperobject ?? {};

    engines.add(project.engine ?? 'openscad');
    for (const mode of manifest.modes ?? []) if (mode.engine) engines.add(mode.engine);

    const interfaces = Array.isArray(ho.cdg_interfaces) ? ho.cdg_interfaces : [];
    if (interfaces.length > 0) withInterfaces += 1;
    for (const iface of interfaces) {
      interfaceInstances += 1;
      if (iface.id) interfaceIds.add(iface.id);
      if (iface.standard) standards.add(iface.standard);
    }

    const formats = manifest.export_formats ?? [];
    if (formats.includes('step')) stepCapable += 1;

    const license = ho.commons_license ?? project.attribution?.license ?? '';
    if (license.startsWith('CERN-OHL')) cernLicensed += 1;
  }

  // The commons catalog is canonical for the headline count: it applies the
  // same exclusions as COMMONS.md (engine test fixtures are not commons
  // objects), so quoting it keeps the landing and the catalog telling one story.
  const catalogPath = path.join(ctx.repo, 'docs', 'commons-catalog.json');
  let cartridges = projects.length;
  if (fs.existsSync(catalogPath)) {
    try {
      const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
      if (catalog?.counts?.cartridges) cartridges = catalog.counts.cartridges;
    } catch {
      /* fall back to the directory count */
    }
  }

  return {
    cartridges,
    hyperobjects: projects.filter((p) => p.isHyperobject).length,
    withInterfaces,
    interfaceInstances,
    distinctInterfaces: interfaceIds.size,
    standards: standards.size,
    engines: engines.size,
    stepCapable,
    cernLicensed,
  };
}

function renderStats(stats) {
  const entries = Object.entries(stats).map(([key, value]) => `  ${key}: ${value},`);
  return [
    '/**',
    ' * Live commons figures, regenerated with the project list. Quote these in',
    ' * copy instead of writing a number into a locale string.',
    ' */',
    'export const COMMONS_STATS = {',
    ...entries,
    '} as const;',
    '',
  ];
}

function renderFile(projects, stats) {
  const lines = [
    '// AUTO-GENERATED by scripts/dev/generate-landing-projects.mjs — do not edit by hand.',
    '// Run `npm run gen:projects` (from apps/landing) to regenerate from projects/*/project.json.',
    '',
    "export type ProjectCategory = 'storage' | 'mechanical' | 'art' | 'tabletop' | 'education' | 'electronics';",
    "export type HyperobjectDomain = 'household' | 'industrial' | 'medical' | 'commercial' | 'hybrid' | 'culture';",
    '',
    'export type Project = {',
    '  slug: string;',
    '  name: string;',
    '  description: string;',
    '  descriptionEs: string;',
    '  category: ProjectCategory;',
    '  thumbnail: string;',
    '  isHyperobject?: boolean;',
    '  domain?: HyperobjectDomain;',
    '};',
    '',
    'export const PROJECTS: Project[] = [',
    ...projects.map(renderProject),
    '];',
    '',
    "export const CATEGORIES = ['all', 'commons', 'storage', 'mechanical', 'art', 'tabletop', 'education', 'electronics'] as const;",
    '',
    ...renderStats(stats),
  ];
  return lines.join('\n');
}

/**
 * Everything a run needs, computed without writing anything.
 * Returns `{ ctx, output, projects, stats, missing, meta }`; callers decide what
 * to do about `missing`.
 */
export function generate({ repo = DEFAULT_REPO, env = process.env } = {}) {
  const ctx = makeContext(repo);
  const priv = privateSlugs(env);
  const { manifests, projects, skippedNoManifest, skippedBad, skippedPrivate } =
    collectProjects(ctx, priv);
  const sorted = sortProjects(projects);
  const stats = computeStats(ctx, manifests, sorted);
  return {
    ctx,
    output: renderFile(sorted, stats),
    projects: sorted,
    stats,
    missing: missingCartridges(repo),
    meta: { skippedNoManifest, skippedBad, skippedPrivate },
  };
}

function summarize(projects, meta, log) {
  const byDomain = {};
  const byCategory = {};
  let hyperCount = 0;
  for (const p of projects) {
    if (p.isHyperobject) hyperCount += 1;
    const dom = p.domain || '(none)';
    byDomain[dom] = (byDomain[dom] || 0) + 1;
    byCategory[p.category] = (byCategory[p.category] || 0) + 1;
  }
  const fmt = (obj) =>
    Object.entries(obj)
      .sort((a, b) => b[1] - a[1])
      .map(([k, v]) => `    ${k}: ${v}`)
      .join('\n');

  log(`Landing projects generated: ${projects.length}`);
  log(`  hyperobjects: ${hyperCount}`);
  log(`  non-hyperobjects: ${projects.length - hyperCount}`);
  if (meta.skippedNoManifest) log(`  skipped dirs (no project.json): ${meta.skippedNoManifest}`);
  if (meta.skippedBad) log(`  skipped dirs (invalid JSON): ${meta.skippedBad}`);
  log(
    `  skipped (private): ${meta.skippedPrivate.length}` +
      (meta.skippedPrivate.length ? ` — ${meta.skippedPrivate.join(', ')}` : ''),
  );
  log('  per-domain:');
  log(fmt(byDomain));
  log('  per-category:');
  log(fmt(byCategory));
}

export function incompleteMessage(missing) {
  return [
    `INCOMPLETE CHECKOUT — ${missing.length} public cartridge submodule(s) have no project.json:`,
    ...missing.map((p) => `  ${p}`),
    'Their entries would be silently dropped from the gallery. Run',
    '  git submodule update --init -- projects/<slug> …',
    'for the paths above (never for `update = none` paths), or pass --allow-partial',
    'if a deliberately partial file is what you want.',
  ].join('\n');
}

/**
 * CLI body. Returns an exit code instead of calling process.exit, so the test
 * suite can drive it directly.
 */
export function run({
  argv = process.argv.slice(2),
  repo = DEFAULT_REPO,
  env = process.env,
  log = console.log,
  logError = console.error,
  write = true,
} = {}) {
  const checkOnly = argv.includes('--check');
  const allowPartial = argv.includes('--allow-partial');

  const { ctx, output, projects, missing, meta } = generate({ repo, env });

  if (missing.length) {
    // --check compares against a file that claims to be complete, so a partial
    // regeneration would report drift indistinguishable from real drift. The
    // completeness gate therefore stands in --check even with --allow-partial:
    // this lane only ever gets stricter.
    if (checkOnly) {
      logError(incompleteMessage(missing));
      logError('--check cannot run against a partial checkout (--allow-partial does not apply here).');
      return EXIT_INCOMPLETE;
    }
    if (!allowPartial) {
      logError(incompleteMessage(missing));
      logError('Refusing to write apps/landing/src/data/projects.ts.');
      return EXIT_INCOMPLETE;
    }
    logError(
      `WARNING: --allow-partial — writing a file that omits ${missing.length} submodule cartridge(s).`,
    );
  }

  if (checkOnly) {
    const existing = fs.existsSync(ctx.outFile) ? fs.readFileSync(ctx.outFile, 'utf8') : '';
    if (existing !== output) {
      logError('DRIFT — apps/landing/src/data/projects.ts does not match the manifests.');
      logError('Run `npm run gen:projects` (from apps/landing, in a checkout with the public');
      logError('cartridge submodules initialised) and commit the result.');
      return EXIT_DRIFT;
    }
    log(`projects.ts is up to date (${projects.length} entries).`);
    return EXIT_OK;
  }

  if (write) fs.writeFileSync(ctx.outFile, output, 'utf8');
  summarize(projects, meta, log);
  return EXIT_OK;
}

// Only self-execute as a CLI, so the test suite can import the functions above.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(run());
}
