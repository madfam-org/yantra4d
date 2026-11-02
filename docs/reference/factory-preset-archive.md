# Factory preset archive (draft 0.1)

`scripts/dev/render_commons_presets.py` is an opt-in local batch producer for
`factory-preset-archive/0.1`. It does not change the landing page's default/keyframe
renderer, call a render API, publish assets or move a commons pin. This is a draft
producer/consumer integration format, not a ratified keystone schema. Factory manifests
are unsigned; entry_digest is a cache identity, not a cryptographic signature or authentication.

It evaluates trusted public CadQuery modes through the existing sandboxed
`cq_runner.py`, produces a GLB and WebP for every selected preset, and copies any
matching committed source SVG projections. Other engines explicitly fail in this
first producer. Run in the existing native geometry environment with CadQuery,
commons-sandbox, trimesh, numpy, Pillow and matplotlib installed.

```sh
python scripts/dev/render_commons_presets.py build \
  --projects-root /path/to/solid-hyperobjects \
  --pin FULL_LOWERCASE_40_CHARACTER_COMMIT \
  --slugs disc-media \
  --preset standard-optical-disc-dvd-120mm \
  --out /path/to/preset-archive
python scripts/dev/render_commons_presets.py check \
  --out /path/to/preset-archive --pin FULL_LOWERCASE_40_CHARACTER_COMMIT
```

The optional `--projects-root` defaults to the normal public `projects/` submodule;
an override permits an isolated, reviewed commons checkout before the platform
adopts its pin. The checkout must have the expected public commons origin, match
the full supplied commit and be clean. Rendering uses a temporary `git archive`
export of that commit, excluding ignored or untracked helper files. The script
checks source identity again after evaluation. Output must be outside that frozen
source checkout. This is a trusted offline batch tool, not an arbitrary uploaded
code execution endpoint or an additional OS isolation boundary.

Without `--preset`, every declared preset plus `archetype-default` is requested.
`kind: fold_state` entries are counted separately and skipped because they assert
no product identity; zero eligible presets fails. The preset's `mode` wins over
the manifest's first mode; `--mode` explicitly overrides it. Every declared mode
part must produce a nonempty mesh. A missing/failed part fails that preset rather
than silently publishing incomplete geometry. No arbitrary caller overrides or
multiple parameter instances under one preset key are introduced here.

## Identity and parameters

`manifest.json` contains:

```json
{
  "schema": "factory-preset-archive/0.1",
  "factory": "solid",
  "entries": [{
    "key": "solid/slug/preset",
    "slug": "slug",
    "preset": "preset",
    "mode": "mode",
    "status": "rendered",
    "source": {
      "commons": "solid-hyperobjects",
      "repository": "https://github.com/madfam-org/solid-hyperobjects",
      "pin": "full 40-character commit",
      "tree": "full git tree id",
      "manifest_sha256": "sha256",
      "files": [{"path": "slug/main.py", "sha256": "sha256"}],
      "source_sha256": "digest of source files list",
      "params": {"requested_override": 1}
    },
    "resolved_parameters": {"requested_override": 1, "other_default": 2},
    "frame": {"units": "m", "up_axis": "Y", "handedness": "right"},
    "parts": ["actual-part-id"],
    "part_results": [],
    "geometry_sha256": "digest of native part observations",
    "engine_fingerprint": "runtime fingerprint",
    "runtime": {},
    "entry_digest": "source/parameters/mode/parts/runtime/frame digest",
    "assets": {
      "glb": {"path": "relative/model.glb", "sha256": "sha256", "bytes": 1, "frame": {}},
      "webp": {"path": "relative/preview.webp", "sha256": "sha256", "bytes": 1, "frame": {}}
    },
    "provenance": {}
  }],
  "coverage": {"requested": [], "rendered": [], "failed": [], "skipped_fold_state": []}
}
```

This abbreviated example illustrates fields, not a valid artifact fixture.
`source.params` is the original preset's requested overrides. `resolved_parameters`
is the complete injection passed to each part after manifest defaults and the
shared API type/bounds rules: sliders clamp, numeric select options retain their
native numeric type, and checkboxes become 0/1. Unknown, non-finite or rejected
parameters fail. `target_part` is injected separately from the actual mode part ID.
Consumers must retain both requested and resolved values and must not claim the
requested value was evaluated when normalization changed it.

The key is unique within one archive. Source commit, mode, requested/resolved
parameters, part IDs, source file hashes, runtime fingerprint and frame all enter
the cache digest. Mere file existence never makes an asset current. A rebuild
writes the selected cohort's manifest; it does not merge other previous cohorts.
Different frozen source cohorts can be consumed as separate archives.

## Frames, parts and evidence

Native geometry is millimetres, right handed, Z up. GLB vertices are explicitly
converted to metres, right handed, Y up with no recentering:

```text
x' = 0.001x
 y' = 0.001z
 z' = -0.001y
```

The entry and GLB asset record carry the full row-major 4×4 matrix, its column-vector
convention, source units and source up axis. GLB scene nodes preserve actual mode
part IDs. A 100 mm source extent becomes 0.1 m; native bounds remain in `part_results`
under `bounds_mm`. The WebP is the existing native mesh rasterizer's framed image,
with pixel/presentation metadata; its image dimensions are not physical dimensions.

Optional `assets.svg` identifies the first matching committed projection;
`assets.projections[]` contains all views with source paths and SHA256. These files
are copied byte for byte, never synthesized. Their auto-scaled SVG user units are
presentation units. Their status is `committed-source-only`: this batch does not
rerender them, and their source view-specific overrides are not recorded by the
existing projection tool. Their exact parameter parity is therefore unverified.
Do not infer millimetres or CAD equality from their SVG page size or filename.

Provenance carries the source preset's own kind, source statement, registry facts,
standard-part record and archetype fallbacks when present. A family render remains
a canonical parametric construction, even when a named preset uses published
measurements. It does not establish a historical product likeness, authentic
trade dress, complete manufacturing detail, package interior, retention or fit.
Historical SKU/reference URIs belong to the consuming caller and are not inferred
from a family slug or preset name.

## Integrity and verification scope

Each asset stores raw-byte SHA256 and length. Source hashes cover the cartridge's
committed files; the full repository commit/tree pins the broader source snapshot.
Native part observations record STL digest, bounds, face count and watertightness.
Those observations do not constitute a fabrication or physical fit check.

Runtime identity hashes the actual batch, thumbnail, runner, parameter-normalizer
and sandbox source files, package versions and installed distribution RECORD
metadata. Its scope is explicit: it is not an OS/container lock or a full hash of
all installed dependency binaries. A source pin alone is not runtime closure.
Collection digests use compact sorted-key UTF-8 JSON without NaN; asset digests
always hash raw bytes. Consumers should check the exact source tuple and asset
hashes and preserve the producer's recorded runtime scope.

`check` verifies recorded identity/cache-digest consistency, all selected preset/part
coverage, required GLB/WebP presence and every asset's length/hash/path containment.
It never reruns a generator or audits SVG geometry. Missing/stale assets fail;
an incomplete manifest fails even if its successful entries are valid. Exit 0 is a
complete selected archive; exit 2 is setup/integrity failure; exit 3 is one or more
render failures. A failure report records its preset key and cause without
publishing that entry as success.

Tests cover full-pin mismatch, dirty source, typed preset parameters, mode/part
coverage, missing/stale artifacts, source/runtime/parameter changes, and a real GLB
round-trip proving 100 mm→0.1 m, Z→Y and part-name preservation. Native smoke renders
remain separate evidence from the synthetic-producer orchestration tests.
