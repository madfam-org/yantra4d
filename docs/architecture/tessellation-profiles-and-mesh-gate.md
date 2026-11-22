# Tessellation profiles and a mesh gate for the Commons

> **Status: proposal, not built. Awaiting the owner's ruling on the seven questions in
> [Rulings requested](#rulings-requested).** Nothing described here exists in the code yet.
> Written 2026-11-22. Figures come from the mesh topology audit of 2026-11-21 (40 preview files
> from 35 cartridges, and 17 print files) unless a line names another source.

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
   prerender run that completed (run 35460054814, 2026-09-19; counted from the optimizer's log).
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
| `preview` | 0.01 mm | 0.2 rad | the models pipeline only | 2,272, 2,556 and 5,900 triangles (bearing housing, electronics enclosure, thread capsule); 63 to 159 segments per circle, by radius; chord error at most 0.005 mm |

A coarser preview was also measured: 0.02 mm and 0.35 rad gave 1,484, 1,564 and 3,428 triangles
with 36 to 126 segments. It fits the 2,500-triangle gallery budget on two of the three parts
without any decimation, at the price of visibly fewer segments on small holes.

What building it involves:

- **The request.** A `tessellation` field on the render payload, `print` when absent. The models
  pipeline ([`render_commons_models.py`](../../scripts/dev/render_commons_models.py)) asks for
  `preview`.
- **STL.** `cq.exporters.export` has no way to say "absolute", so the STL branch calls
  `shape.exportStl(path, linear, angular, ascii=False, relative=False)` directly. Assemblies are
  flattened with `toCompound()` first, as the spec already does.
- **3MF needs its own path.** In CadQuery 2.7.0 the 3MF writer tessellates through
  `Shape.mesh()`, which always passes the tolerance as *relative* and skips a shape that already
  carries a triangulation. Getting an absolute bound into 3MF means meshing the shape explicitly
  with `relative=False` before writing it. Without that, 3MF downloads (offered by all 512
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
| Manifold | any edge shared by more than two triangles | already fails, indirectly: such an edge breaks the watertight test, but the message calls it a boundary edge. The gate adds a clear message. 0 found in 17 files. |
| No zero-area triangles | any triangle with zero area after the vertex merge | not checked; 0 found in 17 files |
| No duplicate faces | the same triangle twice | not checked; 0 found in 17 files |
| Chord error | a circular feature deviates from its true circle by more than 0.05 mm | not checked. Print files: worst 0.024 mm (CadQuery 0.006 mm). OpenSCAD source meshes, measured through undecimated previews: 0.126 mm (spiral planter), 0.241 mm (Voronoi coaster). |
| Segments per circle | a full circle of radius 1 mm or more has fewer than 32 segments | not checked; OpenSCAD print files measured at 32 to 65; the motor mount's 24-segment holes would fail |
| Positive volume, no inverted body | as today | already enforced |
| Size | more than 200,000 triangles in one part | warning only |

What those two resolution thresholds mean in practice: a 32-segment circle stays within 0.05 mm
up to a radius of about 10 mm, 48 segments up to about 23 mm, 64 up to about 41 mm (computed).
So the gate does not fail every fixed-`$fn` cartridge; it fails the ones whose circles are large
for their segment count, or have fewer than 32. In the audit's sample that is three OpenSCAD
cartridges (motor mount, spiral planter, Voronoi coaster).

**Faceting drawn into the solid.** Some CadQuery cartridges are faceted in the geometry itself:
the rugged box draws its round corners as 16-sided polygons at its default setting, and 59
cartridges sample curves by hand with `polyline` and trigonometry (found by text search; gear
involutes among them are legitimate). Their meshes match their solids exactly, so a check that
compares the mesh with the solid passes them. Catching them takes one of two additions, to be
ruled on:

- a **lint** on the cartridge source that flags `polyline` built from `sin`/`cos` loops, as a
  warning for a person to judge; or
- the **mesh circle fit** used for OpenSCAD (below), run on CadQuery output too.

**Opt-out** for parts that are faceted on purpose, modelled on how the parity check is exempted
today: a policy object with a required written reason, settable for the cartridge and overridable
per mode and part, reported as a note and counted as exempt, never silently skipped. Per part
matters: the rugged box is low-poly only in one of its styles, so a cartridge-wide opt-out would
also hide a regression in its round styles. The opt-out switches off only the chord-error and
segment checks; the closed, manifold, zero-area and duplicate checks have none.

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

Rollout, so the gate never lands as a wall of red:

1. **Report only**, for two weeks. Publishes how many cartridges would fail each check. Expected
   from the audit's sample: a few OpenSCAD cartridges on segments or chord error; the
   hand-faceted CadQuery ones only if the lint or the circle fit above is added.
2. **Fix or opt out** those cartridges in the Commons.
3. **Blocking on pull requests**, for the cartridges a pull request touches.
4. **Blocking in the nightly sweeps**, once they have been green for a week.

All the lanes run the same `y4d-spec check --render` at the same pin, so a check becomes blocking
everywhere at once unless the spec gains a switch for it (an option or environment variable that
turns a check from warning to failure). Steps 1, 3 and 4 need that switch.

Preview meshes get the same closed and manifold checks as warnings only, in the models
pipeline's own summary. A preview is a picture, not a deliverable.

## Rulings requested

1. **Print profile.** Add the 0.02 mm absolute bound now (re-renders everything and changes the
   CadQuery side of the parity comparisons), or keep today's numbers under the name `print` and
   add the bound later?
2. **Preview profile.** 0.01 mm / 0.2 rad (finer, some parts still need decimation for the
   2,500-triangle gallery file) or 0.02 mm / 0.35 rad (fits the gallery budget more often, fewer
   segments on small holes)? Either can be tried on the full Commons in CI before it is fixed.
3. **Who may ask for `preview`.** Only the models pipeline, or any API caller? (Not measured
   which costs more: tessellation is a small part of a render, building the solid dominates.)
4. **Gate thresholds.** Chord error at most 0.05 mm and at least 32 segments on full circles of
   radius 1 mm or more: confirm, or change the numbers or the 1 mm floor.
5. **Faceting drawn into the solid.** Catch it with a source lint (warning), with the mesh circle
   fit on CadQuery output too, or not at all for now?
6. **Opt-out.** A policy object with a required reason, per cartridge and overridable per mode
   and part, as described: accepted?
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
