# Yantra4D — Landing

Astro marketing site for yantra4d.com, with React islands for the interactive
sections (the 3D carousel and the project gallery).

```bash
npm install
npm run dev       # Astro dev server on http://localhost:4321
npm run build     # Static build to dist/
npm run preview   # Preview the build
npm run lint      # ESLint
npm test          # Vitest
```

## `src/data/projects.ts` is GENERATED — do not edit it by hand

The gallery is driven by `src/data/projects.ts`, which is generated from the
cartridge manifests (`projects/<slug>/project.json`) by
[`scripts/dev/generate-landing-projects.mjs`](../../scripts/dev/generate-landing-projects.mjs)
and committed. Regenerate it with:

```bash
npm run gen:projects        # from apps/landing
```

Two things follow from it being generated rather than maintained:

- **It needs a complete checkout.** The generator refuses to write (exit 2) when
  any public `projects/*` submodule in `.gitmodules` has no `project.json` on
  disk, because a partial checkout is exactly how the committed list went 328
  entries against a 495-cartridge commons. Run
  `git submodule update --init projects/` first. The two `update = none`
  submodules (the client-private `tablaco` pair) are *expected* to be absent and
  never count as an incomplete checkout.
- **Private cartridges are excluded, on both the signals the backend uses** —
  `access_control.view == "private"` in the manifest and the `PRIVATE_PROJECTS`
  env var, the same comma-separated shape the backend Deployment sets. The
  built-in list is a floor, not a default an empty env var can clear.
  `project.unlisted` is untouched: unlisted means "not in API listings but
  reachable by URL", which is not private.

Where it is checked:

| Lane | What it does |
| :-- | :-- |
| `ci.yml` → `manifest-validation` | `--check` fails the PR when the committed file no longer matches the manifests. It is the only job whose checkout is complete enough to judge the file — the `landing` job checks out no submodules at all. |
| `deploy.yml` → `build-landing` | **Regenerates** rather than checks, so the deployed gallery is correct by construction. Fail-closed: no `--allow-partial`, so a bad checkout stops the deploy instead of publishing a truncated commons. |

The committed file is therefore a fallback for local dev and for the
submodule-less landing CI job, not the source of truth.

## Quality gates

Phase 1 of the landing revamp is a set of gates, not a feature: three
independent measurements of the built site, every threshold read from
**[`perf-budgets.json`](./perf-budgets.json)** — the one source of truth. A
budget is changed there and nowhere else; the gates cannot disagree with each
other. They fail against today's gallery by design (the initial JavaScript is
roughly nine times its budget); Phase 2 is the gallery that fits them.

| Gate | Command (from `apps/landing`) | What it measures | Reads from `perf-budgets.json` |
| :-- | :-- | :-- | :-- |
| Bundle budget | `npm run build && npm run budget` | Brotli (and gzip) transfer size of every `dist/_astro/*.js`. `initial` = every script the two entry pages request at load — `<script src>`, `<link rel="modulepreload">`, each island's `component-url`/`renderer-url` — plus their **static** import closure; a dynamic `import()` is not an edge. The 3D chunk (`vendor-three.*`) and the post-processing chunk are checked by name; a 3D chunk that is statically reachable counts as initial and is called out with a warning naming its importers. | `transfer.initialJsBytes`, `transfer.threeChunkBytes`, `transfer.postprocessingChunkBytes` |
| Playwright | `npm run build && npm run test:e2e` | In a real Chromium, against `astro preview` of the same dist: the tier contract (`tier.spec.ts`), transfer and runtime budgets (`budget.spec.ts`), axe (`a11y.spec.ts`), still/full parity (`parity.spec.ts`). Three profiles: `desktop-full` (`?tier=full`), `mobile-lite` (Pixel 5, `?tier=lite`), `still` (reduced motion, no override — the page must reach `still` on its own signals). | `transfer.*`, `runtime.maxWebglContexts`, `runtime.maxLongTaskMs` |
| Lighthouse CI | `npm run build && npm run lhci` | Mobile Lighthouse, three runs per URL (`/index.html?tier=full`, `/index.html`, `/en/index.html?tier=full`), median run asserted: category scores, plus resource-size and timing budgets generated from the budgets file at load time (`lighthouserc.cjs`). | `lighthouse.*`, `transfer.initialJsBytes` (script), `transfer.initialPageBytes` (total), `vitals.lcpMs.mobile`, `vitals.tbtMs`, `vitals.cls` |

In CI (`ci.yml` → `landing`) all three run after the build, each one even when
an earlier gate has failed, and the Playwright report and `.lighthouseci/`
are uploaded as artifacts when the job is red.

### Running them locally

```bash
npm run build                 # the gates measure dist/, never the dev server
npm run budget                # exit 1 on a breach; --json out.json, --baseline prev.json for deltas
npm run test:e2e              # starts `astro preview` on 127.0.0.1:4321, or reuses one already running
npx playwright test --project=still e2e/tier.spec.ts   # one profile, one spec
npx playwright show-report    # the HTML report of the last run
npm run lhci                  # writes .lighthouseci/*.html|json; open the .html for the waterfall
```

Lighthouse launches its own Chrome. `lighthouserc.cjs` points it at the
Chromium that Playwright installed (`npx playwright install chromium`) when
`CHROME_PATH` is unset; set it explicitly to measure with another build:

```bash
export CHROME_PATH="$(node -e "console.log(require('@playwright/test').chromium.executablePath())")"
```

Playwright starts the preview itself, through `e2e/preview-server.mjs` —
Astro's preview via its JS API, because the Astro 7 CLI daemonises
`astro preview` under an agent shell (Claude Code, Cursor, …) and a daemon is
not a process Playwright's `webServer` can own. It reuses whatever already
answers on the port; if you started `npm run preview` by hand, `astro preview
status` / `astro preview stop` manage that one. Every 3D profile pins `?tier=`
on purpose: headless Chrome is classified `still` by user agent, and the WebGL
probe would demote it again on software rendering.

### Reading a failure

- **Bundle budget** prints a markdown table (file, gzip, brotli, class, note),
  then the three budgets with headroom, then one `::error::` line per breach.
  A `::warning::` (and a `note` in the table) naming the importers of the 3D
  chunk means some load-time script imports it statically, so its bytes count
  as initial — the fix is a dynamic `import()`, not a bigger budget. The same
  table is appended to the GitHub step summary.
- **Playwright** puts the evidence in the assertion message: the transfer
  tests list every offending request with its encoded size (the preview server
  speaks gzip, so figures run ~10 % above the brotli budgets — the strict
  side); the long-task test lists every long task with its start time; the axe
  test lists rule, impact, help URL and the first node targets, and attaches
  minor/moderate findings as annotations instead of failing on them; the
  parity test diffs the h1/h2 text and the digits found in `#hyper-commons`
  and `#cdg-section`. A `scrollThrough: footer not reached` error means the
  page's main thread was too busy to reach the footer in 150 s — a finding in
  itself (a phone viewport of today's un-paged gallery is a 177,000 px page).
- **Lighthouse CI** prints one block per failed assertion (URL, audit id,
  expected vs. actual). `resource-summary:script:size` is the load-time script
  transfer, `largest-contentful-paint` / `total-blocking-time` /
  `cumulative-layout-shift` are the vitals in the budgets file; the category
  scores are the `lighthouse` block. Open the matching `.html` in
  `.lighthouseci/` for the audit details.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**. See the [LICENSE](../../LICENSE) file for more details.
