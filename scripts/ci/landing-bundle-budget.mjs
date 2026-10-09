#!/usr/bin/env node
/**
 * Landing bundle budget — the transfer-size gate for yantra4d.com.
 *
 * Reads the built site (`apps/landing/dist` by default), measures every
 * JavaScript chunk under `_astro/` compressed the way it travels (brotli, with
 * gzip alongside as the proxy the preview server and older CDN paths speak),
 * works out which chunks the page requests BEFORE any interaction, and compares
 * the totals with `apps/landing/perf-budgets.json` — the ONE source of truth the
 * Playwright suite and Lighthouse CI also read. No budget number lives here.
 *
 * Classes
 *   initial  reachable from dist/index.html or dist/en/index.html through
 *            <script src>, <link rel="modulepreload">, an astro-island's
 *            component-url / renderer-url, plus the STATIC import closure of
 *            those files (`import … from "./x.js"`, `import "./x.js"`,
 *            `export … from "./x.js"`). A dynamic `import("./x.js")` is an edge
 *            the page may never follow, so it is NOT initial.
 *   three    the 3D chunk, `vendor-three.<hash>.js` (astro.config.mjs names it)
 *   post     the post-processing chunk, `vendor-postprocessing.<hash>.js`
 *   other    everything else — chunks reachable only through dynamic imports
 *
 * Reachability wins over the name: a 3D chunk that some initial script imports
 * statically IS initial, and counts against the initial budget like any other
 * load-time script — that total is what fails the gate. The wiring itself is
 * reported as a `::warning::` naming the importer, so the reader knows the fix
 * is a dynamic import(), not a bigger number. The three/post budgets are
 * checked BY NAME regardless of class.
 *
 * Usage (from apps/landing: `npm run budget -- [dist-dir] [flags]`):
 *   node scripts/ci/landing-bundle-budget.mjs [dist-dir]
 *       --budgets <perf-budgets.json>   default apps/landing/perf-budgets.json
 *       --json <path>                   write the measurements as JSON
 *       --baseline <path>               print deltas against an earlier --json
 *
 * Appends the markdown report to $GITHUB_STEP_SUMMARY when that is set.
 *
 * Exit codes:
 *   0  every budget holds (warnings, if any, are `::warning::` lines)
 *   1  a budget is breached (each breach is also an `::error::` line)
 *   2  nothing to measure (no dist, no entry page, unreadable budgets)
 */
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(__dirname, '..', '..');
export const DEFAULT_DIST = path.join(REPO_ROOT, 'apps', 'landing', 'dist');
export const DEFAULT_BUDGETS_FILE = path.join(REPO_ROOT, 'apps', 'landing', 'perf-budgets.json');

/** Exit codes, named so the workflow and the tests agree on them. */
export const EXIT_OK = 0;
export const EXIT_BREACH = 1;
export const EXIT_USAGE = 2;

/** The pages whose load-time graph defines `initial` (both locales). */
export const ENTRY_PAGES = ['index.html', 'en/index.html'];
/** Chunk names pinned by astro.config.mjs `manualChunks`. */
export const THREE_CHUNK_RE = /vendor-three\./;
export const POST_CHUNK_RE = /vendor-postprocessing\./;
export const CLASSES = ['initial', 'three', 'post', 'other'];

const JS_FILE_RE = /\.m?js$/i;
const EXTERNAL_URL_RE = /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i;
const KIB = 1024;

// ─── Formatting ─────────────────────────────────────────────────────────────

/** Bytes as `123.4 KB` (KiB — the budgets are round KiB numbers). */
export function formatBytes(bytes) {
  if (bytes < KIB) return `${bytes} B`;
  return `${(bytes / KIB).toFixed(1)} KB`;
}

function formatDelta(current, previous) {
  if (previous === undefined || previous === null) return 'new';
  const diff = current - previous;
  if (diff === 0) return '±0';
  return `${diff > 0 ? '+' : '-'}${formatBytes(Math.abs(diff))}`;
}

/** `ProjectGalleryContainer.BdGhvEbY.js` → `ProjectGalleryContainer` — stable across builds. */
export function fileStem(file) {
  return path.basename(file).replace(/\.[A-Za-z0-9_-]{8}\.m?js$/, '').replace(/\.m?js$/, '');
}

// ─── Budgets ────────────────────────────────────────────────────────────────

/**
 * The three transfer budgets this gate enforces, read from perf-budgets.json.
 * A missing or non-numeric key is an error, never a default: a budget that
 * silently became "unlimited" is worse than no gate.
 */
export function readBudgets(file = DEFAULT_BUDGETS_FILE) {
  let data;
  try {
    data = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (err) {
    throw usageError(`cannot read budgets from ${file}: ${err.message}`);
  }
  const transfer = data && typeof data === 'object' ? data.transfer : undefined;
  const pick = (key) => {
    const value = transfer ? transfer[key] : undefined;
    if (typeof value !== 'number' || !(value > 0)) {
      throw usageError(`${file}: transfer.${key} must be a positive number of bytes`);
    }
    return value;
  };
  return {
    initialJsBytes: pick('initialJsBytes'),
    threeChunkBytes: pick('threeChunkBytes'),
    postprocessingChunkBytes: pick('postprocessingChunkBytes'),
  };
}

function usageError(message) {
  const err = new Error(message);
  err.code = 'EUSAGE';
  return err;
}

// ─── HTML entrypoints ───────────────────────────────────────────────────────

const TAG_RE = /<(script|link|astro-island)\b([^>]*)>/gi;
const ATTR_RE = /([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))/g;

function attributesOf(raw) {
  const attrs = {};
  for (const m of raw.matchAll(ATTR_RE)) attrs[m[1].toLowerCase()] = m[2] ?? m[3] ?? m[4] ?? '';
  return attrs;
}

/**
 * Every script URL a page requests at load, with how it got there:
 * `<script src>`, `<link rel="modulepreload">`, and each astro-island's
 * component-url / renderer-url. The island's client directive rides along in
 * `via` so a `client:visible` island is visible as such in the report.
 * @param {string} html
 * @returns {Array<{url: string, via: string}>}
 */
export function htmlEntrypoints(html) {
  const found = [];
  for (const m of html.matchAll(TAG_RE)) {
    const tag = m[1].toLowerCase();
    const a = attributesOf(m[2]);
    if (tag === 'script') {
      if (a.src) found.push({ url: a.src, via: '<script src>' });
    } else if (tag === 'link') {
      if (a.href && /(?:^|\s)modulepreload(?:\s|$)/i.test(a.rel || '')) {
        found.push({ url: a.href, via: '<link rel="modulepreload">' });
      }
    } else if (tag === 'astro-island') {
      const directive = a.client ? `client:${a.client}` : 'client:?';
      if (a['component-url']) found.push({ url: a['component-url'], via: `island component (${directive})` });
      if (a['renderer-url']) found.push({ url: a['renderer-url'], via: `island renderer (${directive})` });
    }
  }
  return found;
}

// ─── JavaScript import graph ────────────────────────────────────────────────

// Written for MINIFIED output: no whitespace around braces or `from`, and
// specifiers in either quote. `[\w$*{}\s,]` is exactly the character set an
// import/export clause is made of, so the match cannot run through a string,
// a call (`import(`) or a member access (`import.meta`).
const STATIC_FROM_RE = /\b(?:import|export)\s*[\w$*{}\s,]*?from\s*["']([^"']+)["']/g;
const STATIC_BARE_RE = /\bimport\s*["']([^"']+)["']/g;
const DYNAMIC_RE = /\bimport\s*\(\s*["']([^"']+)["']\s*\)/g;

function isLocalSpecifier(spec) {
  return spec.startsWith('./') || spec.startsWith('../') || (spec.startsWith('/') && !spec.startsWith('//'));
}

/**
 * Static and dynamic import specifiers of one module. Only local specifiers
 * (`./`, `../`, `/`) are returned: bare package names and URLs are never files
 * in dist.
 * @param {string} source
 * @returns {{static: string[], dynamic: string[]}}
 */
export function jsImports(source) {
  const statics = new Set();
  const dynamics = new Set();
  for (const m of source.matchAll(STATIC_FROM_RE)) if (isLocalSpecifier(m[1])) statics.add(m[1]);
  for (const m of source.matchAll(STATIC_BARE_RE)) if (isLocalSpecifier(m[1])) statics.add(m[1]);
  for (const m of source.matchAll(DYNAMIC_RE)) if (isLocalSpecifier(m[1])) dynamics.add(m[1]);
  return { static: [...statics], dynamic: [...dynamics] };
}

/** A page URL or import specifier → absolute path inside dist, or null when it is not a local JS file. */
export function resolveLocal(distDir, fromFile, spec) {
  if (!spec || EXTERNAL_URL_RE.test(spec)) return null;
  const clean = spec.split(/[?#]/)[0];
  if (!JS_FILE_RE.test(clean)) return null;
  const abs = clean.startsWith('/')
    ? path.join(distDir, clean)
    : path.resolve(path.dirname(fromFile), clean);
  // Never escape dist, whatever a specifier says.
  const rel = path.relative(distDir, abs);
  if (rel.startsWith('..') || path.isAbsolute(rel)) return null;
  return abs;
}

// ─── Measurement ────────────────────────────────────────────────────────────

/** Raw, gzip (level 9) and brotli (quality 11, static-asset settings) sizes of a buffer. */
export function compressedSizes(buffer) {
  return {
    raw: buffer.length,
    gzip: zlib.gzipSync(buffer, { level: 9 }).length,
    brotli: zlib.brotliCompressSync(buffer, {
      params: {
        [zlib.constants.BROTLI_PARAM_QUALITY]: 11,
        [zlib.constants.BROTLI_PARAM_SIZE_HINT]: buffer.length,
      },
    }).length,
  };
}

function emptyTotal() {
  return { files: 0, raw: 0, gzip: 0, brotli: 0 };
}

function addTo(total, sizes) {
  total.files += 1;
  total.raw += sizes.raw;
  total.gzip += sizes.gzip;
  total.brotli += sizes.brotli;
}

/**
 * Measure and classify a built dist against the budgets.
 *
 * @param {string} distDir
 * @param {{initialJsBytes: number, threeChunkBytes: number, postprocessingChunkBytes: number}} budgets
 * @param {{entryPages?: string[]}} [options]
 */
export function analyzeDist(distDir, budgets, { entryPages = ENTRY_PAGES } = {}) {
  if (!fs.existsSync(distDir)) {
    throw usageError(`no build at ${distDir} — run \`npm run build\` in apps/landing first`);
  }
  const missingPages = entryPages.filter((p) => !fs.existsSync(path.join(distDir, p)));
  if (missingPages.length) {
    throw usageError(`entry page(s) missing from ${distDir}: ${missingPages.join(', ')} — is this a complete landing build?`);
  }

  /** @type {Map<string, {via: Set<string>, importers: Set<string>}>} */
  const reachable = new Map();
  const queue = [];
  const mark = (abs, via, importer) => {
    let entry = reachable.get(abs);
    if (!entry) {
      entry = { via: new Set(), importers: new Set() };
      reachable.set(abs, entry);
      queue.push(abs);
    }
    if (via) entry.via.add(via);
    if (importer) entry.importers.add(importer);
  };

  for (const page of entryPages) {
    const pageFile = path.join(distDir, page);
    const html = fs.readFileSync(pageFile, 'utf8');
    for (const { url, via } of htmlEntrypoints(html)) {
      const abs = resolveLocal(distDir, pageFile, url);
      if (abs) mark(abs, `${page}: ${via}`);
    }
  }

  /** @type {Map<string, Set<string>>} dynamic edges, importer → targets */
  const dynamicEdges = new Map();
  const unresolved = new Set();
  while (queue.length) {
    const file = queue.shift();
    if (!fs.existsSync(file)) {
      unresolved.add(path.relative(distDir, file));
      continue;
    }
    const source = fs.readFileSync(file, 'utf8');
    const imports = jsImports(source);
    for (const spec of imports.static) {
      const abs = resolveLocal(distDir, file, spec);
      if (abs && fs.existsSync(abs)) mark(abs, null, path.relative(distDir, file));
    }
    for (const spec of imports.dynamic) {
      const abs = resolveLocal(distDir, file, spec);
      if (!abs) continue;
      const rel = path.relative(distDir, file);
      if (!dynamicEdges.has(rel)) dynamicEdges.set(rel, new Set());
      dynamicEdges.get(rel).add(path.relative(distDir, abs));
    }
  }

  // Everything under _astro/ plus anything reachable that lives elsewhere.
  const candidates = new Set();
  const astroDir = path.join(distDir, '_astro');
  if (fs.existsSync(astroDir)) {
    for (const name of fs.readdirSync(astroDir)) {
      if (JS_FILE_RE.test(name)) candidates.add(path.join(astroDir, name));
    }
  }
  for (const abs of reachable.keys()) if (fs.existsSync(abs)) candidates.add(abs);

  const files = [];
  const totals = Object.fromEntries(CLASSES.map((c) => [c, emptyTotal()]));
  totals.all = emptyTotal();
  const chunks = { three: emptyTotal(), post: emptyTotal() };
  const breaches = [];
  const warnings = [];

  for (const abs of [...candidates].sort()) {
    const rel = path.relative(distDir, abs).split(path.sep).join('/');
    const sizes = compressedSizes(fs.readFileSync(abs));
    const entry = reachable.get(abs);
    const initial = Boolean(entry);
    const isThree = THREE_CHUNK_RE.test(rel);
    const isPost = POST_CHUNK_RE.test(rel);
    const klass = initial ? 'initial' : isThree ? 'three' : isPost ? 'post' : 'other';
    const importers = entry ? [...entry.importers].sort() : [];
    const via = entry ? [...entry.via].sort() : [];
    const notes = [];

    if (initial && (isThree || isPost)) {
      const label = isThree ? '3D chunk' : 'post-processing chunk';
      const by = importers.length ? `statically imported by ${importers.join(', ')}` : `referenced by ${via.join('; ')}`;
      notes.push(`${label} in the initial graph — ${by}`);
      warnings.push({
        kind: isThree ? 'static-3d' : 'static-post',
        file: rel,
        message:
          `${rel} is reachable from the page at load (${by}), so it counts as initial JS. The ${label} ` +
          'must only ever be reached through a dynamic import(), on tier >= lite, once the gallery is in view.',
      });
    }
    if (entry && via.length && !initial) notes.push(via.join('; '));

    addTo(totals[klass], sizes);
    addTo(totals.all, sizes);
    if (isThree) addTo(chunks.three, sizes);
    if (isPost) addTo(chunks.post, sizes);

    files.push({
      file: rel,
      stem: fileStem(rel),
      ...sizes,
      class: klass,
      initial,
      via,
      importers,
      dynamicImports: [...(dynamicEdges.get(rel) || [])].sort(),
      note: notes.join('; '),
    });
  }

  files.sort((a, b) => b.brotli - a.brotli || a.file.localeCompare(b.file));

  const checks = [
    {
      id: 'initial',
      label: 'initial JS (reachable at load)',
      actual: totals.initial.brotli,
      budget: budgets.initialJsBytes,
      key: 'transfer.initialJsBytes',
    },
    {
      id: 'three',
      label: '3D chunk (vendor-three)',
      actual: chunks.three.brotli,
      budget: budgets.threeChunkBytes,
      key: 'transfer.threeChunkBytes',
    },
    {
      id: 'post',
      label: 'post-processing chunk',
      actual: chunks.post.brotli,
      budget: budgets.postprocessingChunkBytes,
      key: 'transfer.postprocessingChunkBytes',
    },
  ].map((c) => ({ ...c, headroom: c.budget - c.actual, ok: c.actual <= c.budget }));

  for (const c of checks) {
    if (c.ok) continue;
    breaches.push({
      kind: `over-budget:${c.id}`,
      actual: c.actual,
      budget: c.budget,
      message:
        `${c.label} is ${formatBytes(c.actual)} brotli (${c.actual} B), over the ${formatBytes(c.budget)} ` +
        `budget (${c.key} = ${c.budget}) by ${formatBytes(c.actual - c.budget)}.`,
    });
  }

  return {
    version: 1,
    generatedAt: new Date().toISOString(),
    dist: distDir,
    entryPages,
    budgets,
    files,
    totals,
    chunks,
    checks,
    unresolved: [...unresolved].sort(),
    warnings,
    breaches,
    ok: breaches.length === 0,
  };
}

// ─── Report ─────────────────────────────────────────────────────────────────

function baselineIndex(baseline) {
  const byStem = new Map();
  for (const f of baseline?.files || []) byStem.set(f.stem || fileStem(f.file), f);
  return byStem;
}

/**
 * The markdown report: one row per file, then the budgets. With a baseline
 * (an earlier `--json`), a delta column is added to both tables.
 * @param {ReturnType<typeof analyzeDist>} report
 * @param {{baseline?: object|null}} [options]
 */
export function formatMarkdown(report, { baseline = null } = {}) {
  const lines = [];
  const withDelta = Boolean(baseline);
  const prevFiles = baselineIndex(baseline);

  lines.push('### Landing bundle budget');
  lines.push('');
  lines.push(`\`${report.dist}\` — ${report.files.length} JS file(s); entry pages: ${report.entryPages.join(', ')}. Sizes are compressed transfer bytes.`);
  lines.push('');
  lines.push(`| file | gzip | brotli |${withDelta ? ' Δ brotli |' : ''} class | note |`);
  lines.push(`| :-- | --: | --: |${withDelta ? ' --: |' : ''} :-- | :-- |`);
  for (const f of report.files) {
    const delta = withDelta ? ` ${formatDelta(f.brotli, prevFiles.get(f.stem)?.brotli)} |` : '';
    lines.push(`| \`${f.file}\` | ${formatBytes(f.gzip)} | ${formatBytes(f.brotli)} |${delta} ${f.class} | ${f.note || ''} |`);
  }
  const all = report.totals.all;
  const allDelta = withDelta ? ` ${formatDelta(all.brotli, baseline?.totals?.all?.brotli)} |` : '';
  lines.push(`| **all files** | **${formatBytes(all.gzip)}** | **${formatBytes(all.brotli)}** |${allDelta} | |`);
  if (withDelta) {
    const currentStems = new Set(report.files.map((f) => f.stem));
    const removed = [...prevFiles.keys()].filter((s) => !currentStems.has(s));
    if (removed.length) lines.push(`| _removed since baseline_ | | |${withDelta ? ' |' : ''} | ${removed.join(', ')} |`);
  }
  lines.push('');
  lines.push(`| budget | brotli |${withDelta ? ' Δ |' : ''} limit | headroom | |`);
  lines.push(`| :-- | --: |${withDelta ? ' --: |' : ''} --: | --: | :-- |`);
  for (const c of report.checks) {
    const prev = baseline?.checks?.find((b) => b.id === c.id)?.actual;
    const delta = withDelta ? ` ${formatDelta(c.actual, prev)} |` : '';
    const headroom = `${c.headroom >= 0 ? '+' : '-'}${formatBytes(Math.abs(c.headroom))}`;
    lines.push(`| ${c.label} | ${formatBytes(c.actual)} |${delta} ${formatBytes(c.budget)} | ${headroom} | ${c.ok ? 'ok' : '**OVER**'} |`);
  }
  lines.push('');
  const perClass = CLASSES.map((k) => `${k} ${report.totals[k].files} file(s) / ${formatBytes(report.totals[k].brotli)}`).join(' · ');
  lines.push(`By class (brotli): ${perClass}.`);
  if (report.unresolved.length) {
    lines.push('');
    lines.push(`Referenced but not found in dist: ${report.unresolved.map((u) => `\`${u}\``).join(', ')}.`);
  }
  if (report.warnings.length) {
    lines.push('');
    lines.push(`**${report.warnings.length} warning(s):**`);
    for (const w of report.warnings) lines.push(`- ${w.message}`);
  }
  if (report.breaches.length) {
    lines.push('');
    lines.push(`**${report.breaches.length} breach(es):**`);
    for (const b of report.breaches) lines.push(`- ${b.message}`);
  } else {
    lines.push('');
    lines.push('All budgets hold.');
  }
  return lines.join('\n');
}

// ─── CLI ────────────────────────────────────────────────────────────────────

export const USAGE = `usage: landing-bundle-budget.mjs [dist-dir] [--budgets <perf-budgets.json>] [--json <path>] [--baseline <path>]

  dist-dir     the built landing (default: apps/landing/dist)
  --budgets    budget file (default: apps/landing/perf-budgets.json)
  --json       write the measurements to this path
  --baseline   an earlier --json to print deltas against
`;

export function parseArgs(argv) {
  const opts = { dist: DEFAULT_DIST, budgets: DEFAULT_BUDGETS_FILE, json: null, baseline: null, help: false };
  const takeValue = (flag, i) => {
    const value = argv[i + 1];
    if (value === undefined || value.startsWith('--')) throw usageError(`${flag} needs a path`);
    return value;
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') opts.help = true;
    else if (arg === '--json') opts.json = path.resolve(takeValue(arg, (i += 1) - 1));
    else if (arg === '--baseline') opts.baseline = path.resolve(takeValue(arg, (i += 1) - 1));
    else if (arg === '--budgets') opts.budgets = path.resolve(takeValue(arg, (i += 1) - 1));
    else if (arg.startsWith('--')) throw usageError(`unknown flag ${arg}`);
    else opts.dist = path.resolve(arg);
  }
  return opts;
}

/**
 * CLI body. Returns an exit code instead of calling process.exit, so the test
 * suite can drive it with a fixture dist and captured output.
 */
export function run({
  argv = process.argv.slice(2),
  env = process.env,
  log = console.log,
  logError = console.error,
} = {}) {
  let opts;
  let budgets;
  let report;
  try {
    opts = parseArgs(argv);
    if (opts.help) {
      log(USAGE);
      return EXIT_OK;
    }
    budgets = readBudgets(opts.budgets);
    report = analyzeDist(opts.dist, budgets);
  } catch (err) {
    if (err && err.code === 'EUSAGE') {
      logError(`::error::landing bundle budget: ${err.message}`);
      logError(USAGE);
      return EXIT_USAGE;
    }
    throw err;
  }

  let baseline = null;
  if (opts.baseline) {
    try {
      baseline = JSON.parse(fs.readFileSync(opts.baseline, 'utf8'));
    } catch (err) {
      logError(`warning: baseline ${opts.baseline} not readable (${err.message}); reporting without deltas`);
    }
  }

  const markdown = formatMarkdown(report, { baseline });
  log(markdown);
  if (env.GITHUB_STEP_SUMMARY) fs.appendFileSync(env.GITHUB_STEP_SUMMARY, `${markdown}\n\n`);

  if (opts.json) {
    fs.mkdirSync(path.dirname(opts.json), { recursive: true });
    fs.writeFileSync(opts.json, `${JSON.stringify(report, null, 2)}\n`);
    log(`\nmeasurements written to ${opts.json}`);
  }

  for (const warning of report.warnings) logError(`::warning::landing bundle budget: ${warning.message}`);
  for (const breach of report.breaches) logError(`::error::landing bundle budget: ${breach.message}`);
  return report.breaches.length ? EXIT_BREACH : EXIT_OK;
}

// Only self-execute as a CLI, so the test suite can import the functions above.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(run());
}
