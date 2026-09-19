#!/usr/bin/env node
/**
 * Keep the landing's thumbnails within their transfer budget.
 *
 * `apps/landing/public/projects/<slug>.webp` is what every gallery card and the
 * still-tier strip load (lazily) — on a full scroll they are most of the still
 * tier's bytes. A handful were shipped as PNG (one at 387 KB) or as 640×640
 * WebPs over 60 KB, which alone pushed the still tier past its full-scroll
 * budget. This script:
 *
 *   1. converts every `.png` to a `.webp` sibling and removes the PNG (the
 *      generator prefers the `.webp` sibling — see resolveThumbnail);
 *   2. re-encodes any `.webp` above `images.thumbnailBytes` (perf-budgets.json)
 *      — first capping the width at `images.thumbnailMaxWidth`, then lowering
 *      the quality step by step — until it fits, and reports what it did;
 *   3. with `--check`, changes nothing and exits 1 when a PNG remains or any
 *      `.webp` is over budget (the CI lane).
 *
 * `sharp` is resolved from apps/landing/node_modules (Astro already depends on
 * it), so nothing new is installed. Run from anywhere:
 *
 *   node scripts/dev/optimize-landing-thumbnails.mjs [--check] [--dir <public/projects>]
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const DEFAULT_REPO = path.resolve(__dirname, '..', '..');

export const EXIT_OK = 0;
export const EXIT_OVER_BUDGET = 1;
export const EXIT_USAGE = 2;

/** Quality ladder: start where WebP still looks like a render, stop before it looks like a JPEG from 2003. */
const QUALITIES = [78, 72, 66, 60, 54];

export function loadBudgets(repo = DEFAULT_REPO) {
  const file = path.join(repo, 'apps', 'landing', 'perf-budgets.json');
  const budgets = JSON.parse(fs.readFileSync(file, 'utf8'));
  const images = budgets.images ?? {};
  return {
    thumbnailBytes: images.thumbnailBytes ?? 40960,
    thumbnailMaxWidth: images.thumbnailMaxWidth ?? 640,
  };
}

function loadSharp(repo) {
  const require = createRequire(path.join(repo, 'apps', 'landing', 'package.json'));
  return require('sharp');
}

/** Files that need attention, without touching anything. */
export function audit(dir, budgets) {
  const entries = fs.existsSync(dir) ? fs.readdirSync(dir) : [];
  const pngs = entries.filter((f) => f.toLowerCase().endsWith('.png')).sort();
  const webps = entries.filter((f) => f.toLowerCase().endsWith('.webp')).sort();
  const over = webps
    .map((f) => ({ file: f, bytes: fs.statSync(path.join(dir, f)).size }))
    .filter((e) => e.bytes > budgets.thumbnailBytes);
  const total = webps.reduce((s, f) => s + fs.statSync(path.join(dir, f)).size, 0);
  return { pngs, webps, over, total };
}

/**
 * Encode `input` to `output` under the byte budget. Returns the row for the
 * report; `fits` false means even the last rung was too big (file still written
 * at the smallest size reached, so the page has *something*, and `--check` will
 * keep failing until someone looks at that render).
 */
export async function encodeUnderBudget(sharp, input, output, budgets) {
  const image = sharp(input);
  const meta = await image.metadata();
  const width = meta.width && meta.width > budgets.thumbnailMaxWidth ? budgets.thumbnailMaxWidth : undefined;
  let best = null;
  for (const quality of QUALITIES) {
    const buf = await sharp(input).resize({ width, withoutEnlargement: true }).webp({ quality, effort: 6 }).toBuffer();
    best = { buf, quality };
    if (buf.length <= budgets.thumbnailBytes) break;
  }
  fs.writeFileSync(output, best.buf);
  return { quality: best.quality, bytes: best.buf.length, fits: best.buf.length <= budgets.thumbnailBytes, resizedTo: width ?? null };
}

export async function run({ argv = process.argv.slice(2), repo = DEFAULT_REPO, log = console.log } = {}) {
  const check = argv.includes('--check');
  const dirArg = argv.indexOf('--dir');
  const dir = dirArg !== -1 ? path.resolve(argv[dirArg + 1]) : path.join(repo, 'apps', 'landing', 'public', 'projects');
  if (!fs.existsSync(dir)) {
    log(`no such directory: ${dir}`);
    return EXIT_USAGE;
  }
  const budgets = loadBudgets(repo);
  const before = audit(dir, budgets);

  if (check) {
    log(`thumbnails: ${before.webps.length} webp, ${Math.round(before.total / 1024)} KB total, budget ${budgets.thumbnailBytes} B per file`);
    for (const p of before.pngs) log(`  PNG still present: ${p}`);
    for (const o of before.over) log(`  over budget: ${o.file} ${o.bytes} B`);
    return before.pngs.length || before.over.length ? EXIT_OVER_BUDGET : EXIT_OK;
  }

  const sharp = loadSharp(repo);
  const rows = [];
  for (const png of before.pngs) {
    const input = path.join(dir, png);
    const output = path.join(dir, png.replace(/\.png$/i, '.webp'));
    const from = fs.statSync(input).size;
    const r = await encodeUnderBudget(sharp, input, output, budgets);
    fs.unlinkSync(input);
    rows.push({ file: path.basename(output), from, ...r, action: 'png→webp' });
  }
  for (const o of before.over) {
    const file = path.join(dir, o.file);
    const tmp = `${file}.tmp`;
    const r = await encodeUnderBudget(sharp, file, tmp, budgets);
    fs.renameSync(tmp, file);
    rows.push({ file: o.file, from: o.bytes, ...r, action: 'recompressed' });
  }
  const after = audit(dir, budgets);
  log('| file | action | before | after | quality | width | fits |');
  log('| :-- | :-- | --: | --: | --: | --: | :-- |');
  for (const r of rows) {
    log(`| ${r.file} | ${r.action} | ${r.from} | ${r.bytes} | ${r.quality} | ${r.resizedTo ?? 'kept'} | ${r.fits ? 'ok' : 'STILL OVER'} |`);
  }
  log(`total webp: ${Math.round(before.total / 1024)} KB → ${Math.round(after.total / 1024)} KB; pngs: ${before.pngs.length} → ${after.pngs.length}; over budget: ${before.over.length} → ${after.over.length}`);
  return after.pngs.length || after.over.length ? EXIT_OVER_BUDGET : EXIT_OK;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(await run());
}
