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

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**. See the [LICENSE](../../LICENSE) file for more details.

## Device tiers, budgets, and the data the page binds

The landing renders one of three experiences, decided **before first paint**:

| Tier | Who gets it | What ships |
|---|---|---|
| `still` | no WebGL2 / software renderer, `prefers-reduced-motion`, Save-Data, crawlers, very small devices, no-JS | posters + HTML; **zero 3D bytes** |
| `lite` | phones, few cores, little memory | one light 3D scene, DPR 1 |
| `full` | everything else (unknown signals never demote) | the 3D stage |

- `src/lib/tier-core.js` is the pure classifier. It is evaluated **twice on purpose**:
  as a module (islands, tests) and inline in `<head>` (`tier-inline.js` appended by
  `tier-bootstrap.ts`, injected by `BaseLayout.astro`). `src/lib/tier.test.ts` pins both
  evaluations to the same table.
- `src/lib/tier.ts` settles the tier right before any 3D could load (WebGL probe with
  `failIfMajorPerformanceCaveat`; it can only demote) and stores a measured or chosen tier
  in `localStorage['y4d.landing_tier.v1']`. `?tier=still|lite|full` overrides for QA and is
  never stored. `TierToggle.astro` is the visible "Lite mode" control.
- `<html data-tier="still">` is the markup default, so no JavaScript means no 3D.

**Budgets** live in `perf-budgets.json` — the one source the CI bundle step, Lighthouse CI,
the Playwright suite and the mesh pipeline read. Vendor chunks are named in
`astro.config.mjs` (`vendor-react`, shared; `vendor-three`, dynamic) so they can be measured.

**Data the page binds but does not own** is committed under `src/data/snapshots/` and read
at build time — the build never calls a network:

```bash
node scripts/dev/generate-landing-projects.mjs --refresh-snapshots   # api.yantra4d.com graph/families + fashioncabi.net catalog
```

`fc-consumers.json` (the FC→Y4D hardware-bridge back-edge) is vendored by hand from the
fashion-cabinet repository; its `_comment` says how. The generator turns the snapshots into
extra `COMMONS_STATS` figures (`softCartridges`, `crossLinks`, …) and `apps/api/tiers.json`
into `TIER_FACTS`; a missing snapshot yields `null` and the component hides that card.

**No figure is typed into copy.** `src/test/locale-figures.test.ts` fails when a locale
string carries a digit that is neither a `{placeholder}` bound to generated data nor an
entry in `src/locales/figure-allowlist.json` with a written reason (standards, dimensions,
file formats). Counts, prices and percentages about the product belong in generated data.

**The gallery** is server-rendered first (`ProjectGallery.astro` + `ProjectCard.astro`, 24
cards). `CommonsGallery.tsx` (client:visible) fetches `/data/<lang>/commons.json` only on the
first search, filter or "show more", and lazy-imports `ProjectCarousel3D` only on tier ≥ lite.
`src/lib/models-manifest.ts` reads `public/models/manifest.json` in its v1 and v2 shapes.
