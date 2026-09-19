/**
 * Lighthouse CPU throttling, calibrated to the host that runs the audit.
 *
 * Lighthouse's default `cpuSlowdownMultiplier` of 4 is documented against a
 * high-end desktop with a BenchmarkIndex of 1500–2000 and is meant to emulate a
 * mid-tier phone from there (lighthouse/docs/throttling.md — "if your device's
 * BenchmarkIndex falls on the lower end of its bracket, use a lower multiplier").
 * The ARC runner is not that desktop, and it is not even the same machine twice:
 * ci run 35460027219 (2026-09-19) measured 937–1782 across the nine Lighthouse
 * runs of ONE job — the pods share their node with the e2e shards — and
 * total-blocking-time followed it for the same build: 985 → 974 ms,
 * 1504 → 123 ms, 1782 → 91 ms. At a fixed 4× the TBT gate measures node load.
 *
 * This measures the BenchmarkIndex the way Lighthouse does — its own
 * `computeBenchmarkIndex` page function, in the same Chrome binary launched
 * with the same flags (chrome-launcher, `--headless=new`, the container flags
 * under CI), read through the same CDP client — after the browser has settled
 * and one warm-up pass has been discarded (the first seconds after launch read
 * a third of the steady value), takes the median of a few samples and scales
 * the multiplier so that host speed ÷ multiplier lands where Lighthouse's
 * default puts it:
 *
 *   multiplier = 4 × benchmarkIndex / 1750      clamped to 1–4, one decimal
 *
 * 1750 is the middle of the bracket the default is written for. A host at
 * 1750 gets Lighthouse's own 4×, the runner at ~1300 gets ~3×, and nothing
 * ever gets MORE than the default: the budgets are written against
 * Lighthouse's standard emulation, and above 4× the linear model overshoots —
 * a pod reading 2650 throttled to 6.1× produced 734 and 341 ms of TBT where
 * a pod reading 1740 at 4× produced under 200 for the same build (ci runs
 * 35469373879 and 35461707348, 2026-09-19). Relax on slow hosts, never
 * tighten beyond the standard.
 *
 * Usage (from apps/landing; `npm run lhci` is the second form):
 *   node ../../scripts/ci/landing-lighthouse-cpu.mjs                  measure and print; also appends
 *                                                                     LH_CPU_MULTIPLIER to $GITHUB_ENV when set
 *   node ../../scripts/ci/landing-lighthouse-cpu.mjs -- lhci autorun  measure, then run the command with
 *                                                                     LH_CPU_MULTIPLIER set (exit code passes through)
 *   LH_CPU_MULTIPLIER=4 npm run lhci                                  an explicit value wins; nothing is measured
 * Options: --samples <n> (3)  --anchor <bi> (1750)  --base <x> (4)  --json
 *
 * lighthouserc.cjs reads LH_CPU_MULTIPLIER. Unset — a bare `lhci autorun`, or a
 * host where no Chrome can be launched — means Lighthouse's default 4×, exactly
 * the behaviour before this script existed. Chrome: CHROME_PATH, else the
 * Chromium Playwright installed, the same fallback lighthouserc.cjs applies.
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const DEFAULTS = Object.freeze({
  base: 4,
  anchor: 1750,
  min: 1,
  max: 4,
  samples: 3,
});

/** Median of a list of numbers; NaN for an empty list. */
export function median(values) {
  const sorted = values
    .map(Number)
    .filter((v) => Number.isFinite(v))
    .sort((a, b) => a - b);
  if (sorted.length === 0) return NaN;
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * The multiplier that emulates the same device from this host as Lighthouse's
 * default does from its reference host. Invalid input → the default, never a
 * harsher or softer throttle by accident.
 */
export function multiplierFor(
  benchmarkIndex,
  {
    base = DEFAULTS.base,
    anchor = DEFAULTS.anchor,
    min = DEFAULTS.min,
    max = DEFAULTS.max,
  } = {},
) {
  const bi = Number(benchmarkIndex);
  if (!Number.isFinite(bi) || bi <= 0) return base;
  const clamped = Math.min(max, Math.max(min, (base * bi) / anchor));
  return Math.round(clamped * 10) / 10;
}

/** `--flag value` options, then everything after `--` is the command to run. */
export function parseArgs(argv) {
  const opts = {
    samples: DEFAULTS.samples,
    anchor: DEFAULTS.anchor,
    base: DEFAULTS.base,
    json: false,
    command: [],
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--") {
      opts.command = argv.slice(i + 1);
      break;
    }
    if (arg === "--json") {
      opts.json = true;
      continue;
    }
    const numeric = {
      "--samples": "samples",
      "--anchor": "anchor",
      "--base": "base",
    };
    if (arg in numeric) {
      const value = Number(argv[++i]);
      if (!Number.isFinite(value) || value <= 0)
        throw new Error(`${arg} wants a positive number, got ${argv[i]}`);
      opts[numeric[arg]] =
        arg === "--samples" ? Math.max(1, Math.round(value)) : value;
      continue;
    }
    throw new Error(
      `unknown option ${arg} (options: --samples, --anchor, --base, --json, then -- <command>)`,
    );
  }
  return opts;
}

/** apps/landing, where @playwright/test and lighthouse are installed: the cwd when run from there, else by position. */
function landingDir() {
  const cwd = process.cwd();
  if (fs.existsSync(path.join(cwd, "lighthouserc.cjs"))) return cwd;
  return path.resolve(__dirname, "../../apps/landing");
}

/** The Chromium Playwright installed, when there is one — the fallback lighthouserc.cjs uses. */
function playwrightChromium(require) {
  try {
    return require("@playwright/test").chromium.executablePath();
  } catch {
    return undefined;
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * BenchmarkIndex samples from Lighthouse's own page function, in the Chrome
 * Lighthouse will launch, the way Lighthouse launches it. Returns the samples
 * that count; `warmUp` is the discarded first pass, reported for the log.
 */
export async function measureBenchmarkIndex({
  samples = DEFAULTS.samples,
  chromePath,
  settleMs = 1500,
} = {}) {
  const require = createRequire(path.join(landingDir(), "package.json"));
  const chromeLauncher = require("chrome-launcher");
  const puppeteer = require("puppeteer-core");
  const { pageFunctions } = await import(
    pathToFileURL(require.resolve("lighthouse/core/lib/page-functions.js")).href
  );
  const chromeFlags = [
    "--headless=new",
    ...(process.env.CI ? ["--no-sandbox", "--disable-dev-shm-usage"] : []),
  ];
  const chrome = await chromeLauncher.launch({
    chromePath:
      chromePath || process.env.CHROME_PATH || playwrightChromium(require),
    chromeFlags,
  });
  try {
    const browser = await puppeteer.connect({
      browserURL: `http://127.0.0.1:${chrome.port}`,
      defaultViewport: null,
    });
    try {
      const page = await browser.newPage();
      await page.goto("about:blank");
      await sleep(settleMs);
      const warmUp = await page.evaluate(pageFunctions.computeBenchmarkIndex);
      const values = [];
      for (let i = 0; i < samples; i++)
        values.push(await page.evaluate(pageFunctions.computeBenchmarkIndex));
      return {
        values,
        warmUp,
        chromePath:
          chrome.process?.spawnfile ??
          chromePath ??
          process.env.CHROME_PATH ??
          "system Chrome",
      };
    } finally {
      await browser.disconnect();
    }
  } finally {
    await chrome.kill();
  }
}

function appendLine(file, line) {
  if (file) fs.appendFileSync(file, `${line}\n`);
}

async function main(argv) {
  const opts = parseArgs(argv);
  const explicit = Number(process.env.LH_CPU_MULTIPLIER);
  let multiplier;
  let detail;
  let samples = [];
  if (Number.isFinite(explicit) && explicit > 0) {
    multiplier = explicit;
    detail = "LH_CPU_MULTIPLIER set explicitly; nothing measured";
  } else {
    try {
      const measured = await measureBenchmarkIndex({ samples: opts.samples });
      samples = measured.values;
      const bi = median(samples);
      multiplier = multiplierFor(bi, opts);
      detail = `BenchmarkIndex ${samples.map((v) => Math.round(v)).join(" / ")} → median ${Math.round(bi)} (warm-up ${Math.round(measured.warmUp)} discarded); ${opts.base}× assumes ~${opts.anchor}; ${path.basename(String(measured.chromePath))}`;
    } catch (error) {
      multiplier = undefined;
      detail = `could not measure (${error instanceof Error ? error.message.split("\n")[0] : error}); Lighthouse's default ${opts.base}× applies`;
      if (process.env.GITHUB_ACTIONS)
        console.log(
          `::warning title=Lighthouse CPU calibration skipped::${detail}`,
        );
    }
  }
  const line = `Lighthouse CPU throttle: ${multiplier ?? `${opts.base} (default)`}× — ${detail}`;
  console.log(line);
  if (opts.json)
    console.log(
      JSON.stringify({
        multiplier: multiplier ?? null,
        samples,
        anchor: opts.anchor,
        base: opts.base,
      }),
    );
  if (multiplier !== undefined)
    appendLine(process.env.GITHUB_ENV, `LH_CPU_MULTIPLIER=${multiplier}`);
  appendLine(process.env.GITHUB_STEP_SUMMARY, `- ${line}`);

  if (opts.command.length === 0) return 0;
  const env = { ...process.env };
  if (multiplier !== undefined) env.LH_CPU_MULTIPLIER = String(multiplier);
  const child = spawnSync(opts.command[0], opts.command.slice(1), {
    stdio: "inherit",
    env,
  });
  if (child.error) {
    console.error(
      `could not run ${opts.command.join(" ")}: ${child.error.message}`,
    );
    return 1;
  }
  return child.status ?? 1;
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  main(process.argv.slice(2)).then(
    (code) => process.exit(code),
    (error) => {
      console.error(error instanceof Error ? error.message : error);
      process.exit(1);
    },
  );
}
