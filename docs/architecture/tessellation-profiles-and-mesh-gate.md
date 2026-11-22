# Tessellation profiles and a mesh gate for the Commons

> **Status: proposal, not built. Awaiting the owner's ruling on the six questions in
> [Rulings requested](#rulings-requested).** Nothing described here exists in the code yet.
> Written 2026-11-22 from the mesh topology audit of 2026-11-21 (35 preview meshes and 17 print
> files measured; the figures below come from it unless a line says otherwise).

## The problem in three facts

1. **Print files are sound but their resolution is nobody's decision.** The CadQuery path, which
   renders 490 of the 512 Commons cartridges, exports with the library's defaults
   ([`cq_runner.py`](../../apps/api/services/engine/cq_runner.py), the `cq.exporters.export(...)`
   calls near the end of `run_cq_script`). Those defaults are a 0.1 linear tolerance that CadQuery
   treats as *relative* to edge size, and a 0.1 rad angular tolerance. Measured, only the angular
   bound acts: every full circle gets 126 segments, whether its radius is 1.35 mm or 45 mm. A
   2.7 mm hole is cut into 126 strips 0.07 mm wide; a 500 mm radius would have a chord error of
   about 0.16 mm (computed, not measured), because nothing bounds the error in millimetres.
2. **The preview is the same fine mesh, cut down afterwards.** The models pipeline renders the
   print mesh and decimates it to 2,500 triangles. 279 of 502 previews were decimated in the last
   full run. Decimation turns a regular 126-segment circle into an uneven one with as few as 18
   segments. Asking the kernel for a coarser, regular mesh instead gave 2,272 and 2,556 triangles
   with 63 to 105 even segments per circle on two ordinary parts.
3. **Nothing checks mesh quality beyond "is it closed".** The Commons CI judges every changed
   cartridge watertight, positive in volume and free of inverted bodies (`_judge_stl` in
   `hyperobjects-spec`, `src/y4d_spec/geometry.py`). It does not look at resolution. Nineteen
   OpenSCAD cartridges ship a fixed `$fn` of 24 to 64 (a 118 mm planter wall printed as 48 flats,
   each 7.7 mm wide), and nothing would stop a twentieth.

## Part 1. Named tessellation profiles for CadQuery

Two profiles, chosen by the render request, each with an absolute chord bound in millimetres and
an angular bound.

| Profile | Linear (absolute) | Angular | Used by | Effect measured on three parts |
|---|---|---|---|---|
| `print` (default) | 0.02 mm | 0.1 rad | every render a person downloads | Not measured at exactly this setting. The 0.02 mm bound is looser than what the angular bound already gives below a radius of about 64 mm, so circular features under that size should come out as today (126 segments); larger ones gain segments. |
| `preview` | 0.01 mm | 0.2 rad | the models pipeline only | 2,272, 2,556 and 5,900 triangles (bearing housing, electronics enclosure, thread capsule); 63 to 159 segments per circle, by radius; chord error at most 0.005 mm |

A coarser preview was also measured: 0.02 mm and 0.35 rad gave 1,484, 1,564 and 3,428 triangles
with 36 to 126 segments. It fits the 2,500-triangle gallery budget on two of the three parts
without any decimation, at the price of visibly fewer segments on small holes.

What building it involves:

- **The request.** A `tessellation` field on the render payload, `print` when absent. The models
  pipeline ([`render_commons_models.py`](../../scripts/dev/render_commons_models.py)) asks for
  `preview`.
- **The export call.** `cq.exporters.export` has no way to say "absolute", so the STL branch
  calls `shape.exportStl(path, linear, angular, ascii=False, relative=False)` directly
  (signature read from CadQuery 2.7.0; the API pins 2.8.0 and it must be confirmed there).
  Assemblies are flattened with `toCompound()` first, as the spec already does. 3MF takes the
  same two numbers through `exporters.export`. The GLB route goes through
  `cascadio.step_to_glb`, which has its own defaults (0.01 mm, 0.5 rad): a third, unnamed
  tessellation today. It should take the profile's numbers too.
- **The cache.** The profile becomes part of the render cache key, next to the engine
  signature, so a preview mesh can never be served as a print file.
- **The spec.** `hyperobjects-spec` mirrors the API's export call on purpose
  (`_export_stl`: "pinning them on one side only would be the change"). The profile numbers
  therefore land in the spec first and the platform reads them from there or pins the same
  values, and the two keystone pins in `ci.yml` and `spec-nightly.yml` move together.
- **OpenSCAD is not covered.** Its resolution is written in each `.scad` file. Replacing fixed
  `$fn` with `$fa`/`$fs` is a change to 19 cartridges in the Commons repository, tracked
  separately.

Costs and risks:

- Changing `print` invalidates every cached render and moves every geometric parity baseline
  whose part has a curved feature above the size where the absolute bound takes over. If the
  owner prefers zero change to print output for now, `print` can be defined as exactly today's
  numbers (0.1 relative, 0.1 rad) and only `preview` introduced; the absolute bound then comes
  later as its own step.
- The `preview` profile changes no print output. It changes every preview mesh, so the gallery
  and the Studio's first view change for all cartridges at the next prerender.
- Three parts is a small sample. Threaded and free-form parts grow under an absolute bound
  (thread capsule: 4,524 triangles today, 5,900 at `preview`), so the simplifier stays as the
  fallback for parts over budget.

## Part 2. A mesh gate in CI

One bar, in the place the existing bar lives: `_judge_stl` in `hyperobjects-spec`. It already
runs for every cartridge a Commons pull request touches and for the whole Commons nightly, and
this repository runs the same check in its `spec-conformance` job.

Checks on the **print export**, per part:

| Check | Fails when | Today |
|---|---|---|
| Closed | any boundary edge | already enforced (watertight) |
| Manifold | any edge shared by more than two triangles | not checked; 0 found in 17 files |
| No zero-area triangles | any triangle with zero area after the vertex merge | not checked; 0 found in 17 files |
| Chord error | a circular feature deviates from its true circle by more than 0.05 mm | not checked; worst measured 0.024 mm (CadQuery 0.006 mm) |
| Segments per circle | a full circle of radius 1 mm or more has fewer than 32 segments | not checked; OpenSCAD files measured at 32 to 65, `$fn = 24` cartridges would fail |
| Positive volume, no inverted body | as today | already enforced |

Opt-out for parts that are faceted on purpose: a manifest block in the shape the parity policy
already uses, with a written reason, for example

```json
"mesh_quality": { "faceted": true, "reason": "Low-poly style: 16-sided corners are the design" }
```

It switches off the chord-error and segment checks for that cartridge only. The closed,
manifold and zero-area checks have no opt-out.

**Never gated: sliver share.** Thin triangles are what every CAD tessellator produces (long
strips on cylinders, fans on flat faces). The audit measured 17 % to 100 % slivers on files
that are watertight and print correctly. The number says nothing about printability, and a
gate on it would fail the whole Commons.

How the two resolution checks would be measured:

- **CadQuery parts:** against the solid itself. Sample each triangle's centroid and edge
  midpoints and take the distance to the B-rep. That is the chord error on any surface, at any
  orientation, with no circle detection. Segment count comes from the kernel's own circular
  edges, matched to the mesh.
- **OpenSCAD parts:** there is no solid to compare with, so circles are fitted to the mesh. The
  audit's fit handled only features aligned with an axis; tilted holes, cones and spheres were
  not counted. The gate would say so in its output instead of passing them silently.

Rollout, so the gate never lands as a wall of red:

1. **Report only**, in the nightly sweep, for two weeks. Publishes how many cartridges would
   fail each check. Expected from the audit: the 19 fixed-`$fn` OpenSCAD cartridges on segments
   or chord error, and the CadQuery cartridges that facet by hand (rugged box, and an unchecked
   list of 59 files that sample curves with `polyline`).
2. **Fix or opt out** those cartridges in the Commons.
3. **Blocking on pull requests**, for the cartridges a pull request touches.
4. **Blocking in the nightly**, once it has been green for a week.

Preview meshes get the same closed and manifold checks as warnings only, in the models
pipeline's own summary. A preview is a picture, not a deliverable.

## Rulings requested

1. **Print profile.** Add the 0.02 mm absolute bound now (re-renders everything, moves parity
   baselines for large curved parts), or keep today's numbers under the name `print` and add the
   bound later?
2. **Preview profile.** 0.01 mm / 0.2 rad (finer, some parts still need decimation for the
   2,500-triangle gallery file) or 0.02 mm / 0.35 rad (fits the gallery budget more often, fewer
   segments on small holes)? Either can be tried on the full Commons in CI before it is fixed.
3. **Who may ask for `preview`.** Only the models pipeline, or any API caller (it is cheaper to
   compute than `print`)?
4. **Gate thresholds.** Chord error at most 0.05 mm and at least 32 segments on full circles of
   radius 1 mm or more: confirm, or change the numbers or the 1 mm floor.
5. **Opt-out.** A manifest `mesh_quality` block with a required reason, as sketched: accepted?
6. **Rollout.** The four steps above, starting report-only: accepted?

## Not verified

- No profile has been run on more than three parts, and `print` at exactly 0.02 mm / 0.1 rad
  has not been run at all.
- The CadQuery signature was read from version 2.7.0; production runs 2.8.0.
- Render time per profile was not measured on the server. Locally, tessellation took 0.01 to
  0.15 s per part; building the solid dominated.
- How many Commons cartridges fail each proposed check is an estimate from a 35-cartridge
  sample and a text search, which is why the rollout starts by measuring.
- 3MF and OBJ exports were not measured by the audit.

[Models pipeline guide](../guides/landing-models-pipeline.md) ·
[Engine architecture](./dual-engine.md) ·
[Verification guide](../guides/verification.md) ·
[Documentation index](../index.md).
