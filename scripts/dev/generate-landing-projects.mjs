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
 * Usage:
 *   node scripts/dev/generate-landing-projects.mjs
 *   node scripts/dev/generate-landing-projects.mjs --check   # fail if output is stale
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, '..', '..');
const PROJECTS_DIR = path.join(REPO, 'projects');
const PUBLIC_DIR = path.join(REPO, 'apps', 'landing', 'public');
const OUT_FILE = path.join(REPO, 'apps', 'landing', 'src', 'data', 'projects.ts');

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
function resolveThumbnail(proj, slug) {
  const declared = proj.thumbnail;
  if (declared && declared.startsWith('/')) {
    const abs = path.join(PUBLIC_DIR, declared.replace(/^\//, ''));
    if (fs.existsSync(abs)) return declared;
  }
  return `/projects/${slug}.svg`;
}

function collectProjects() {
  const entries = fs.readdirSync(PROJECTS_DIR, { withFileTypes: true });
  const projects = [];
  let skippedNoManifest = 0;
  let skippedBad = 0;

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const dir = path.join(PROJECTS_DIR, entry.name);
    const manifestPath = path.join(dir, 'project.json');
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
    const ho = resolveHyperobject(data, proj);

    const name = i18nName(proj, slug);
    const { en: description, es: descriptionEs } = descriptions(proj);
    const thumbnail = resolveThumbnail(proj, slug);
    const isHyperobject = isHyperobjectFlag(data, proj);
    const geometryType = firstGeometryType(ho);
    const rawDomain = ho.domain || '';
    const domain = DOMAIN_MAP[rawDomain];
    const category = deriveCategory(domain, geometryType, proj.tags);

    projects.push({
      slug,
      name,
      description,
      descriptionEs,
      category,
      thumbnail,
      isHyperobject,
      domain,
    });
  }

  return { projects, skippedNoManifest, skippedBad };
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
 */
function computeStats(projects) {
  const dirs = fs.readdirSync(PROJECTS_DIR, { withFileTypes: true }).filter((d) => d.isDirectory());
  const engines = new Set();
  const standards = new Set();
  const interfaceIds = new Set();
  let interfaceInstances = 0;
  let withInterfaces = 0;
  let stepCapable = 0;
  let cernLicensed = 0;

  for (const dir of dirs) {
    const manifestPath = path.join(PROJECTS_DIR, dir.name, 'project.json');
    if (!fs.existsSync(manifestPath)) continue;
    let manifest;
    try {
      manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    } catch {
      continue;
    }
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
  const catalogPath = path.join(REPO, 'docs', 'commons-catalog.json');
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

function renderFile(projects) {
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
    ...renderStats(computeStats(projects)),
  ];
  return lines.join('\n');
}

function summarize(projects, meta) {
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

  console.log(`Landing projects generated: ${projects.length}`);
  console.log(`  hyperobjects: ${hyperCount}`);
  console.log(`  non-hyperobjects: ${projects.length - hyperCount}`);
  if (meta.skippedNoManifest) console.log(`  skipped dirs (no project.json): ${meta.skippedNoManifest}`);
  if (meta.skippedBad) console.log(`  skipped dirs (invalid JSON): ${meta.skippedBad}`);
  console.log('  per-domain:');
  console.log(fmt(byDomain));
  console.log('  per-category:');
  console.log(fmt(byCategory));
}

function main() {
  const checkOnly = process.argv.includes('--check');
  const { projects, skippedNoManifest, skippedBad } = collectProjects();
  const sorted = sortProjects(projects);
  const output = renderFile(sorted);

  if (checkOnly) {
    const existing = fs.existsSync(OUT_FILE) ? fs.readFileSync(OUT_FILE, 'utf8') : '';
    if (existing !== output) {
      console.error('projects.ts is stale — run `npm run gen:projects` and commit the result.');
      process.exit(1);
    }
    console.log('projects.ts is up to date.');
    return;
  }

  fs.writeFileSync(OUT_FILE, output, 'utf8');
  summarize(sorted, { skippedNoManifest, skippedBad });
}

main();
