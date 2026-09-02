# Browser Audit suite (`23-browser-audit`)

The only E2E suite that runs against a **real backend with no API mocks**
(`test.use({ mockAPIs: false })`): real manifests, real OpenSCAD/CadQuery
renders, real downloads, real axe passes. Everything else under `e2e/tests/`
mocks the API, and the default browser projects exclude this directory via
`testIgnore` in `playwright.config.js`.

Specs: `gridfinity.spec.js`, `custom-msh.spec.js`, `tablaco.spec.js`
(client-private), `cross-cutting.spec.js`, `responsive.spec.js` (375×812).
Shared helpers: `audit-helpers.js`.

## How it runs in CI

`.github/workflows/e2e-audit.yml`, nightly at 03:00 UTC on
`madfam-runners-blue`. **No Docker** — since PR #76 the whole harness is
started directly on the runner, the same shape as `ci.yml`'s `e2e` job:

1. `apt-get install openscad redis-server`, `pip install -r apps/api/requirements.txt`
2. `redis-server --daemonize yes --port 6379`
3. `python app.py` on `:5000` (`AUTH_ENABLED=false`, `RATE_LIMIT_ENABLED=false`
   — ~80 serial real renders from one client would otherwise trip the render
   quota, `PROJECTS_DIR=$GITHUB_WORKSPACE/projects`)
4. `python apps/worker/render_worker.py`. **The API never renders inline**:
   `/api/render` enqueues to Redis and waits for the worker's pub/sub reply,
   answering 503 "Render worker unavailable" until the worker's heartbeat is in
   Redis. A backend with no worker cannot render at all.
5. `npm run build` + Playwright's own `webServer`: `vite preview --port 5173`,
   whose `/api` and `/static` proxy to `:5000` is inherited from
   `server.proxy` in `vite.config.js`.
6. `npx playwright test --project=audit` — serial (`fullyParallel: false`,
   `workers: 1` in CI), 180 s per test.

A failure in steps 1–5 is a **harness** failure: it stops at a job-summary
annotation and is deliberately not posted to the `e2e-audit-failure` tracking
issue, which only ever hears about test results.

## How to run it locally

You need OpenSCAD, Redis, the API and the render worker. `./scripts/dev/dev.sh`
starts the API and the Studio but **neither Redis nor the worker**, so start
those yourself:

```bash
redis-server --daemonize yes --port 6379

cd apps/api
REDIS_URL=redis://localhost:6379 PROJECTS_DIR="$PWD/../../projects" \
  AUTH_ENABLED=false RATE_LIMIT_ENABLED=false PORT=5000 python app.py &

YANTRA4D_BACKEND_PATH="$PWD" REDIS_URL=redis://localhost:6379 \
  PROJECTS_DIR="$PWD/../../projects" python ../worker/render_worker.py &

# Both of these must be true or every spec skips itself:
curl -s localhost:5000/api/health | python3 -m json.tool | grep -A2 -E 'openscad|render_worker'

cd ../studio && npx playwright test --project=audit
```

Locally `webServer` runs `dev.sh` instead of `vite preview` and reuses an
existing server on `:5173`.

## Skip helpers — per group and per test

- `skipIfNoBackend(request, testInfo, requiredSlugs = PUBLIC_AUDIT_SLUGS)` in
  `beforeAll` skips the whole **describe** when the backend is unreachable,
  `checks.openscad.ok` is false, or a required cartridge is not served. It also
  records the backend's live project list.
- `hasProject(slug)` / `skipUnlessProject(test, slug)` skip a **single test**
  with a stated reason.
- `PUBLIC_AUDIT_SLUGS` = `gridfinity`, `custom-msh` — in every checkout.
  `PRIVATE_AUDIT_SLUGS` = `tablaco` — a client-private `update = none`
  submodule, absent from a normal checkout, present only when the workflow is
  dispatched with `include_private_projects=true` (`MADFAM_BOT_PAT`). Its specs
  report SKIPPED with that reason rather than failing on a 404.

Pass the slugs a group actually needs. Requiring a private cartridge in a
default `beforeAll` skips the entire audit for everyone.

## Conventions

- **`PROJECT_NAME` const per spec**, read from `projects/<slug>/project.json`
  — not from memory. `gridfinity` declares `"Gridfinity"`; the "Extended" name
  now belongs only to its three `(OpenSCAD Extended)` modes.
- **The Long Render Warning is handled once, not dismissed repeatedly.** The
  studio auto-generates on load and pops that modal whenever the estimate
  exceeds the cartridge's threshold (normal for gridfinity's cadquery `bin`,
  ~2 min). Radix renders it over a pointer-event-blocking overlay, so every
  later click waits out its full actionability budget instead of landing — that
  is how run #166 burned 180 s three times in `toggleLanguage()`.

  One-shot dismissals were not enough: the studio re-arms its debounced
  auto-generate on every param/preset settle and every mode switch, so the modal
  comes back and run #167 lost four more tests to it (the post-load settle,
  `selectMode()` twice, the mobile sheet trigger). So:

  - `goToRealProject()` cancels the one already up — the axe audits reach the
    page through `page.evaluate`, which is neither an action nor an assertion
    and so never triggers a handler. Since #82 that one-shot finds nothing (an
    automatic render is skipped with a toast and opens no dialog), so it runs on
    a short budget as a safety net. It then
    registers `autoCancelRenderWarning(page)`, a `page.addLocatorHandler()` on
    `[role="alertdialog"]` that cancels it before **every** later action.
    Registered once per page, uncapped, `noWaitAfter`. Order matters: arming it
    before that one-shot would make the handler race `dismissRenderWarning()`
    for the same Cancel button.
  - **A test that WANTS the dialog must take the handler off first**, via
    `expectRenderWarning(page)` — it removes the handler and returns the dialog
    locator. `clickGenerateWithWarning()` and `triggerAndWaitRender()` already
    call it, so every user-initiated Generate is covered; call it yourself
    before any new code that confirms the modal. Otherwise the handler cancels
    the very dialog you are about to confirm and "Render Anyway" lands on a
    detached button.
  - The handler stays off for the rest of that test (the `page` fixture is
    per-test, so nothing leaks); a later `goToRealProject()` re-arms it.
  - `dismissRenderWarning(page, …)` still works and is still used — its click is
    now failure-tolerant, since the handler may cancel the dialog first.

  After the quiet-autogenerate change (automatic renders no longer open the
  modal; user-initiated ones still do) the handler simply never fires, and
  `expectRenderWarning()` still hands the manual dialog to its caller. Nothing
  here needs revisiting.
- **The harness must be able to render.** `AUTH_ENABLED=false` alone does not
  unlock the render path: `_effective_tier()` grants the top tier only with auth
  off **and** Flask debug on, so this job was gated as `guest` — and guest may
  not use the CadQuery engine (`apps/api/tiers.json`), which is what
  gridfinity's default `bin` mode is. Run #168 had every gridfinity render
  refused with a 403 and the studio answered with its **upgrade prompt**. The
  workflow now sets `HARNESS_TIER=madfam` (docs/AUTH.md, "Harness tier"), which
  the API honours only while auth is off.

  That upsell is a second `[role="alertdialog"]` and is deliberately **not**
  auto-cancelled — its button reads "Maybe Later", which the handler above does
  not match, because clicking it away would hide a real entitlement gate and let
  render tests pass having rendered nothing. Instead
  `assertNoUpgradePrompt(page)` fails fast by name; it runs inside
  `waitForRenderDone()` and `clickGenerateWithWarning()`, so a future tier
  regression is reported in one line instead of a 180 s timeout.
- **Drain the render queue between groups.** One worker serves the whole suite,
  and nothing else ever empties its queue: the Studio does not cancel an
  in-flight render when the page is navigated away or closed, so every test that
  leaves mid-render abandons work the worker must still finish. Run #171 had
  **zero** cancel calls in 40 minutes; custom-msh's failing assembly test renders
  every part and serial-mode re-ran it three times, and gridfinity's first render
  test then timed out at 180 s four render requests deep without ever reaching
  the front of the queue — a queueing failure that reads as a render failure.
  `drainRenderQueue(request, reason)` runs in each spec's `afterAll` and in
  `afterEach` after a failed test (which is when work gets abandoned), logs the
  worker's `queue depth` before and after, and never throws. `waitForRenderDone`
  puts the same figure in its timeout message, so starvation reads as
  starvation.
- **Name the failure, do not inherit it.** Two assertion helpers run inside the
  shared helpers so a product-side problem is reported as itself instead of as
  whatever is missing afterwards: `assertNoUpgradePrompt(page)` (tier gate) and
  `assertStudioLoaded(page, slug)` (the manifest error screen, which replaces
  the whole app — run #170 reported it only as "wanted 5 mode tabs, found 0").
  Neither dismisses anything.
- **Find a project by searching for it.** The commons is 500+ cartridges and
  `ProjectsView` pages at 60 sorted by name, so a card for a specific slug is
  almost never on the first page. Fill the searchbox with the slug — the slug is
  in the server-side haystack — rather than scrolling the pager.
- **`sidebar.selectModeByLabel(label)`** for a mode whose id is not a substring
  of its label — `selectMode('baseplate_scad')` cannot find "Baseplate
  (OpenSCAD Extended)".
- **`triggerAndWaitRender()` proves a render by evidence.** It edits the slider,
  then requires either the Generate button observed **disabled** or the render
  console text **changing**; it confirms the Long Render Warning when one
  appears, clicks Generate explicitly when the app started no render on its own
  (a short estimate, a cached value, or the quiet-autogenerate path), and throws
  when neither signal was ever seen. Do not "simplify" it back into dismiss +
  wait: answering a dialog that no longer appears and then waiting on a button
  that was never disabled passes without any render happening.
- **Assert what is on screen.** `App.tsx` used to mount its desktop and mobile
  trees at the same time (`hidden lg:flex` / `lg:hidden`), so
  `locator('canvas').first()` and `[role="tab"]` counts picked up permanently
  hidden elements — four canvases on a phone, three of them in display:none
  subtrees. #81 mounts only the tree on screen, so the duplicates are gone, but
  keep `.filter({ visible: true })`: it says what the assertion means, it costs
  nothing when nothing is hidden, and the mobile controls sheet still mounts a
  second copy of the sidebar's contents while it is open. Scope mode tabs to
  `[role="tablist"][aria-label="Mode selection"]` — the sidebar's
  Design/View/BOM/Export tablist comes first in the DOM.

## When a cartridge changes its modes or presets

Update the expectation to the new fact and **name the fact in-line** (a comment
citing `project.json`), exactly as the current specs do — "5 modes in
project.json: bin + baseplate (cadquery) and cup, baseplate_scad, lid". Never
loosen an assertion to make it pass: a `toHaveCount(5)` relaxed to
`toBeGreaterThan(0)`, or a name match widened to `/.*/,` is a test that has
stopped auditing anything. If the cartridge is wrong, fix the cartridge.

## Known upstream cartridge bug — gridfinity presets

Five gridfinity presets — `battery_holder_scad`, `small_bin_scad`,
`tool_drawer_scad`, `screw_organizer_scad`, `pen_cup_scad` — declare
`"mode": "cup_scad"`, which is **not** one of the manifest's five mode ids
(`bin`, `baseplate`, `cup`, `baseplate_scad`, `lid`; the OpenSCAD bin is
`cup`). Applying one strands the studio on an unknown mode and no `width_units`
row ever renders. The suite therefore asserts on "Standard Lid (2×1)"
(`lid_std_scad`, mode `lid`) instead — the same shape of assertion on a preset
whose mode exists. **The fix belongs upstream in the gridfinity cartridge**, not
in this suite; when it lands, the preset test can move back to Battery Holder.
