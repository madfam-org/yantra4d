# Tessellation profiles and a mesh gate for the Commons

> **Status: ruled 2026-11-22 (seven rulings, [below](#rulings-2026-11-22)); being built,
> step 1 of the rollout only (report-only).** What exists and what does not is in
> [Implementation status](#implementation-status). The proposal text after those two
> sections is kept as written on 2026-11-22; where a ruling chose differently, a
> *Ruled* line under the passage says so.
> Figures come from the mesh topology audit of 2026-11-21 (40 preview files
> from 35 cartridges, and 17 print files) unless a line names another source.

## Rulings (2026-11-22)

The owner's answers to the seven questions in [Rulings requested](#rulings-requested):

- **M1 Print profile.** Keep today's numbers (0.1 relative, 0.1 rad) under the name `print`
  for now. Add the 0.02 mm absolute bound later, and only if the report-only gate shows
  CadQuery parts over 0.05 mm. Print output must not change in this work.
- **M2 Preview profile.** 0.02 mm absolute / 0.35 rad. Try it on the whole Commons in CI
  before fixing it, and report the measured triangle counts and how many previews then fit
  the 2,500-triangle gallery budget without decimation. The simplifier stays as the fallback.
- **M3 Who may ask for `preview`.** Only the models pipeline, never a public API caller. The
  profile is part of the render cache key, so a preview mesh can never be served as a print
  file.
- **M4 Gate thresholds.** Chord error at most 0.05 mm; at least 32 segments on full circles
  of radius 1 mm or more. Plus the structural checks of Part 2 (closed, manifold with a clear
  message, no zero-area triangles, no duplicate faces; more than 200,000 triangles is a
  warning). Never gate on sliver share.
- **M5 Faceting drawn into the solid.** A source lint (`polyline` built from sin/cos loops;
  `polygon(n, ...)` with a small `n`) that warns only, never fails. No failing circle-fit
  check on CadQuery output. Separately, the rugged box's holes become round by default in the
  Commons; its low-poly styles stay available as non-default options.
- **M6 Opt-out.** A policy object with a required written reason, per cartridge and
  overridable per mode and part, reported as a note and counted as exempt, never silently
  skipped. It switches off only the chord-error and segment checks. No per-parameter or
  per-preset grain for now.
- **M7 Rollout.** The four steps of Part 2. This work delivers step 1 only: report-only,
  with a spec switch per check (an option or environment variable turning a check from
  warning to failure), publishing how many cartridges would fail each check. Steps 2 to 4
  are later work.

## Implementation status

| Piece | Where | State |
|---|---|---|
| `print` / `preview` profiles (M1, M3) | `apps/api/services/engine/tessellation.py`, `cq_runner.py`, `cadquery_engine.py`, `cq_pool.py`, `render_cache.py`, `render_orchestrator.py`, `apps/worker/render_worker.py` | Built. `print` is the default and calls the exporter exactly as before (byte-identical, `tests/integration/test_tessellation_kernel.py`). `preview` is STL only and honoured only while `ALLOW_PREVIEW_TESSELLATION` is set and `AUTH_ENABLED` is false; any other caller gets 403 `tessellation_not_allowed`. The profile is in the cache key and the artifact name whenever it is not `print`, so print keys and URLs are unchanged. |
| Models pipeline asks for `preview` (M2) | `scripts/dev/render_commons_models.py --tessellation`, `prerender-commons.yml` input `tessellation` (default `preview`) | Built. The committed landing models were not refreshed in this work. |
| Preview measured on the whole Commons (M2) | [Preview profile across the Commons](#preview-profile-across-the-commons) | See that section. |
| Report-only mesh gate (M4–M7) | `hyperobjects-spec` | Not built yet. |
| Spec pins moved together | `ci.yml`, `spec-nightly.yml`, Commons `SPEC_PIN` | Not done yet. |
| Rugged box round by default (M5) | Commons | Not done yet. |
| GLB and 3MF tessellation | — | Unchanged on purpose (M1): print GLB still goes through `cascadio` defaults and 3MF through CadQuery's relative tessellation. |

## Preview profile across the Commons

Not measured yet.

## The problem in three facts

1. **Print files are sound but their resolution is nobody's decision.** The CadQuery path, which
   renders 490 of the 512 Commons cartridges, exports with the library's defaults
   ([`cq_runner.py`](../../apps/api/services/engine/cq_runner.py): `cq.exporters.export(...)` for
   a part, `result.save(...)` for an assembly, both in `run_cadquery_script`). Those defaults are
   a 0.1 linear tolerance that CadQuery treats as *relative* to edge size, and a 0.1 rad angular
   tolerance. In the files measured, plain circles came out at 126 segments whatever their radius
   (1.35 mm to 45 mm), which points to the angular bound being the one that acts; helical and
   free-form surfaces got more (126 to 211 on the thread capsule). A 2.7 mm hole is cut into 126
   strips 0.07 mm wide; a 500 mm radius would have a chord error of about 0.16 mm (computed, not
   measured), because nothing bounds the error in millimetres.
2. **The preview is the same fine mesh, cut down afterwards.** The models pipeline renders the
   print mesh and decimates it to 2,500 triangles. 279 of 502 previews were decimated in the last
   prerender run that produced the previews shipped today (run 35460054814, 2026-09-19; counted
   from the optimizer's log; the runs of 2026-11-22 show 289 of 510).
   Decimation turns a regular 126-segment circle into an uneven one with as few as 18 segments.
   Asking the kernel for a coarser, regular mesh instead gave 2,272 and 2,556 triangles with 63 to
   105 even segments per circle on two ordinary parts; the second is still just over the budget.
3. **Nothing checks mesh resolution.** The Commons CI judges every changed cartridge watertight,
   positive in volume and free of inverted bodies (`_judge_stl` in `hyperobjects-spec`,
   `src/y4d_spec/geometry.py`). It does not look at resolution. Some OpenSCAD cartridges ship a
   fixed `$fn` too coarse for their size: the spiral planter's 118 mm wall is printed as 48 flats,
   each 7.7 mm wide (0.126 mm chord error), the Voronoi coaster at 32 segments on a 50 mm radius
   (0.241 mm), the motor mount's holes at 24. Nothing would stop another.

## Part 1. Named tessellation profiles for CadQuery

Two profiles, chosen by the render request, each with an absolute chord bound in millimetres and
an angular bound.

| Profile | Linear (absolute) | Angular | Used by | Effect measured on three parts |
|---|---|---|---|---|
| `print` (default) | 0.02 mm | 0.1 rad | every render a person downloads | Not measured at exactly this setting. For a circle, the 0.02 mm bound is looser than what the angular bound already gives below a radius of about 64 mm (computed), so small round features should come out as today and larger ones gain segments. Threads and free-form surfaces may change at any size. |
| `preview` | 0.01 mm | 0.2 rad | the models pipeline only | 2,272, 2,556 and 5,900 triangles (bearing housing, electronics enclosure, thread capsule); 63 to 159 segments per circle, by radius; chord error at most 0.005 mm. Note: its linear bound is *tighter* than `print`'s, so above a radius of about 32 mm a preview circle gets more segments than the print file (computed: 149 against 126 at 45 mm, 222 against 157 at 100 mm). |

*Ruled (M1, M2):* `print` keeps today's numbers (0.1 relative, 0.1 rad) for now, and
`preview` is the coarser setting below, 0.02 mm / 0.35 rad.

A coarser preview was also measured: 0.02 mm and 0.35 rad gave 1,484, 1,564 and 3,428 triangles
with 36 to 126 segments. It fits the 2,500-triangle gallery budget on two of the three parts
without any decimation, at the price of visibly fewer segments on small holes, and its linear
bound equals the proposed `print` bound, so with that bound a preview circle is never denser
than the print file (with today's print numbers it is, above a radius of about 64 mm). Large and free-form
parts still grow under either preview setting, which is why the simplifier stays as a fallback.

What building it involves:

- **The request.** A `tessellation` field on the render payload, `print` when absent. The models
  pipeline ([`render_commons_models.py`](../../scripts/dev/render_commons_models.py)) asks for
  `preview`. *Ruled (M3):* only the models pipeline may.
- **STL.** `cq.exporters.export` has no way to say "absolute", so the STL branch calls
  `shape.exportStl(path, linear, angular, ascii=False, relative=False)` directly on a shape: a
  Workplane result is turned into one first (`compound(*result)`, as
  `exporters.export` does internally), and an assembly is flattened with `toCompound()`, as the
  spec already does.
- **3MF needs its own path.** In CadQuery 2.7.0 the 3MF writer tessellates through
  `Shape.mesh()`, which always passes the tolerance as *relative*, and skips the shape when an
  existing triangulation is already at least as fine as asked. Getting an absolute bound into 3MF
  means meshing the shape explicitly with `relative=False` first and then exporting with a
  tolerance no finer than that mesh, so the writer keeps it. Without that, 3MF downloads (offered by all 512
  manifests) would keep today's relative tolerance while STL changed. Separately, the assembly
  branch `result.save(path, "3MF")` raises "Unknown format" in 2.7.0. Neither point has been
  checked on 2.8.0, which production runs.
- **GLB.** The GLB route goes through `cascadio.step_to_glb`, which has its own defaults
  (0.01 mm, 0.5 rad, absolute): a third, unnamed tessellation today. It should take the
  profile's numbers too.
- **The cache.** The profile becomes part of the render cache key, next to the engine
  signature, so a preview mesh can never be served as a print file.
- **The spec.** `hyperobjects-spec` mirrors the API's export call on purpose
  (`_export_stl`: "pinning them on one side only would be the change"). The profile numbers
  therefore land in the spec first and the platform reads them from there or pins the same
  values. Three pins move together: yantra4d's `ci.yml` and `spec-nightly.yml`, and the Commons
  repository's `SPEC_PIN`. One more mismatch has to be settled at the same time: the spec's
  `[geometry]` extra pins CadQuery `>=2.4,<2.8`, so CI judges a re-export made with an older
  CadQuery than the 2.8.0 production uses, never the file a user downloads.
- **OpenSCAD is not covered.** Its resolution is written in each `.scad` file. Replacing fixed
  `$fn` with `$fa`/`$fs` is a change in the Commons repository (19 cartridges render OpenSCAD by
  default, plus the OpenSCAD modes of dual-engine ones), tracked separately.

Costs and risks:

- Changing `print` invalidates every cached render. There are no stored geometry baselines, but
  the geometric parity check compares the CadQuery and OpenSCAD meshes of each part in every run,
  and some per-part tolerances were calibrated to today's CadQuery faceting; those comparisons
  change for any part whose CadQuery mesh changes. If the owner prefers zero change to print
  output for now, `print` can be defined as exactly today's numbers (0.1 relative, 0.1 rad) and
  only `preview` introduced; the absolute bound then comes later as its own step.
- The `preview` profile changes no print output. It changes every CadQuery and graph preview
  (the OpenSCAD and implicit cartridges keep theirs), so the gallery and the Studio's first view
  change for those at the next prerender.
- Three parts is a small sample. Threaded and free-form parts grow under an absolute bound
  (thread capsule: 4,524 triangles today, 5,900 at `preview`), so the simplifier stays as the
  fallback for parts over budget.

## Part 2. A mesh gate in CI

Where it runs: alongside the existing bar in `hyperobjects-spec`, which already renders every
cartridge a Commons pull request touches and sweeps the whole Commons nightly (in the Commons
repository, and again in this repository's `spec-nightly.yml`). The mesh checks below belong in
`_judge_stl`, which sees only the exported mesh; the resolution checks for CadQuery parts need the
solid as well, so they belong one step earlier, in `render_part`, next to the existing B-rep
checks. Whichever mesh oracle the spec is set to (`trimesh`, `geomcore` or both) must measure the
new checks too.

Checks on the **print export**, per part:

| Check | Fails when | Today |
|---|---|---|
| Closed | any boundary edge | already enforced (watertight) |
| Manifold | any edge shared by more than two triangles | already fails, indirectly: such an edge breaks the watertight test, but the message counts boundary edges only and can read "0 boundary edge(s)". The gate adds a clear message. 0 found in 17 files. |
| No zero-area triangles | any triangle with zero area after the vertex merge | not checked; 0 found in 17 files |
| No duplicate faces | the same triangle twice | not checked; 0 found in 17 files |
| Chord error | a circular feature deviates from its true circle by more than 0.05 mm | not checked. Print files: worst 0.024 mm (CadQuery 0.006 mm). OpenSCAD meshes measured through previews: 0.126 mm (spiral planter, 48 segments as in its source; the preview was decimated, which cannot add segments), 0.241 mm (Voronoi coaster, undecimated). |
| Segments per circle | a full circle of radius 1 mm or more has fewer than 32 segments | not checked; OpenSCAD print files measured at 32 to 65; the motor mount's 24-segment holes would fail |
| Positive volume, no inverted body | as today | already enforced |
| Size | more than 200,000 triangles in one part | warning only |

What those two resolution thresholds mean in practice: a 32-segment circle stays within 0.05 mm
up to a radius of about 10 mm, 48 segments up to about 23 mm, 64 up to about 41 mm (computed).
So the gate does not fail every fixed-`$fn` cartridge; it fails the ones whose circles are large
for their segment count, or have fewer than 32. In the audit's sample that is three OpenSCAD
cartridges (motor mount on segments; spiral planter and Voronoi coaster on chord error).

The chord limit also reaches CadQuery if today's tolerance is kept (ruling 1): at 126 segments a
circle exceeds 0.05 mm above a radius of about 161 mm, and the relative bound leaves large
free-form surfaces unbounded. Keeping today's numbers and adopting the 0.05 mm gate together
would fail large CadQuery parts; how many is not known (the audit's sample had no circles that large; the chord error of its large free-form part was not
measured).

**Faceting drawn into the solid.** Some CadQuery cartridges are faceted in the geometry itself,
and their meshes match their solids exactly, so a check that compares the mesh with the solid
passes them. It happens in two ways, and the two possible remedies do not cover the same ground:

- **Polygons.** The rugged box draws every cylindrical feature (holes, corners) as an inscribed
  prism through `wp.polygon(n, …)`: 16-sided at its default style, 8-sided at another.
- **Hand-sampled curves.** 59 cartridges build curves with `polyline` and trigonometry (found by
  text search; gear involutes among them are legitimate).

The remedies:

- the **mesh circle fit** used for OpenSCAD (below), run on CadQuery output too. It catches both
  kinds where the feature is a full circle aligned with an axis, and can fail a cartridge; or
- a **source lint** that flags `polyline` built from `sin`/`cos` loops, and `polygon(n, …)` with
  a small `n`. It is a warning for a person to judge, never a failure, and it sees only the
  patterns it is written for.

**Opt-out** for parts that are faceted on purpose, modelled on how the parity check is exempted
today: a policy object with a required written reason, settable for the cartridge and overridable
per mode and part, reported as a note and counted as exempt, never silently skipped. Faceting is
sometimes chosen by a parameter rather than by mode or part (the rugged box has two low-poly
styles and one round one, for all its modes), so the opt-out may also need to name a parameter
value or preset; the owner decides the grain. The opt-out switches off only the chord-error and
segment checks; the closed, manifold, zero-area and duplicate checks have none.

*Ruled (M5):* the source lint, warning only; no failing circle-fit check on CadQuery output.
*Ruled (M6):* the opt-out as described, per cartridge and overridable per mode and part, with
no per-parameter or per-preset grain for now.

**Never gated: sliver share.** Thin triangles are what every CAD tessellator produces (long
strips on cylinders, fans on flat faces). The audit measured 17 % to 100 % slivers on files that
are watertight. The number says nothing about printability, and a gate on it would fail most of
the measured files.

How the two resolution checks would be measured:

- **CadQuery parts:** against the solid itself. Sample each triangle's centroid and edge
  midpoints and take the distance to the B-rep. That is the chord error on any surface, at any
  orientation, with no circle detection. Segment count comes from the kernel's own circular
  edges, matched to the mesh. (This does not see faceting drawn into the solid; see above.)
- **OpenSCAD parts:** there is no solid to compare with, so circles are fitted to the mesh. The
  audit's fit handled only features aligned with an axis; tilted holes, cones and spheres were
  not counted. The gate would say so in its output instead of passing them silently.

Rollout, so the gate never lands as a wall of red (*ruled, M7: this work delivers step 1
only*):

1. **Report only**, for two weeks. Publishes how many cartridges would fail each check. Expected
   from the audit's sample: a few OpenSCAD cartridges on segments or chord error; the
   hand-faceted CadQuery ones only if the circle fit is run on them (the lint only warns); large
   CadQuery parts if today's tolerance is kept.
2. **Fix or opt out** those cartridges in the Commons.
3. **Blocking on pull requests**, for the cartridges a pull request touches.
4. **Blocking in the nightly sweeps**, once they have been green for a week.

All the lanes run the same `y4d-spec check --render` at the same pin, so a check becomes blocking
everywhere at once unless the spec gains a switch for it (an option or environment variable that
turns a check from warning to failure). Steps 1 and 3 need that switch; at step 4 it can go.

Preview meshes get the same closed and manifold checks as warnings only, in the models
pipeline's own summary. A preview is a picture, not a deliverable.

## Rulings requested

Answered 2026-11-22; see [Rulings](#rulings-2026-11-22). The questions as they were put:

1. **Print profile.** Add the 0.02 mm absolute bound now (re-renders everything and changes the
   CadQuery side of the parity comparisons), or keep today's numbers under the name `print` and
   add the bound later? Keeping today's numbers together with the 0.05 mm gate (ruling 4) would
   fail CadQuery circles above a radius of about 161 mm.
2. **Preview profile.** 0.01 mm / 0.2 rad (more segments; denser than the print file on circles
   above about 32 mm, so more parts still need decimation for the 2,500-triangle gallery file) or
   0.02 mm / 0.35 rad (fits the gallery budget more often, fewer segments on small holes; on
   circles never denser than print if print takes the 0.02 mm bound, denser above about 64 mm if
   it keeps today's numbers)? Either can be tried on the full Commons in CI before it is fixed.
3. **Who may ask for `preview`.** Only the models pipeline, or any API caller? (Not measured
   which costs more: tessellation is a small part of a render, building the solid dominates.)
4. **Gate thresholds.** Chord error at most 0.05 mm and at least 32 segments on full circles of
   radius 1 mm or more: confirm, or change the numbers or the 1 mm floor.
5. **Faceting drawn into the solid.** Catch it with the mesh circle fit on CadQuery output (can
   fail a cartridge; sees axis-aligned full circles), with a source lint for `polyline` + trig and
   small-`n` `polygon` (warning only), both, or not at all for now?
6. **Opt-out.** A policy object with a required reason, per cartridge and overridable per mode
   and part, as described: accepted? And should it also be settable per parameter value or
   preset, for cartridges whose faceting is a style choice?
7. **Rollout.** The four steps above, starting report-only, with a spec switch per check:
   accepted?

## Not verified

- No profile has been run on more than three parts, and `print` at exactly 0.02 mm / 0.1 rad
  has not been run at all.
- CadQuery behaviour was read from version 2.7.0 (the export signature, the relative 3MF
  tessellation, the assembly 3MF error); production runs 2.8.0.
- Render time per profile was not measured on the server. Locally, tessellation took 0.01 to
  0.15 s per part; building the solid dominated.
- How many Commons cartridges fail each proposed check is an estimate from a 35-cartridge
  sample and a text search, which is why the rollout starts by measuring.
- How the geom-core mesh oracle treats an edge shared by more than two triangles was not checked.
- 3MF and OBJ exports were not measured by the audit.

[Models pipeline guide](../guides/landing-models-pipeline.md) ·
[Engine architecture](./dual-engine.md) ·
[Verification guide](../guides/verification.md) ·
[Documentation index](../index.md).
