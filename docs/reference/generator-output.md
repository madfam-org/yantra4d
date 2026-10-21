# Generator output (`variables.json`, GOC-1)

> Boundary: this page documents yantra4d's producer side only. The contract and its JSON Schema
> (`generator-output.schema.json`) are owned by `hyperobjects-spec`; yantra4d keeps no copy.

A **generator instance** is the geometry of one rendered part plus one `variables.json` document. The
document says which cartridge, mode and part produced the geometry, with which inputs, on which engine,
and the sha256 of every file. It carries no material, process, slicer or printer settings: those
belong to the semantic layer.

Code: `apps/api/services/engine/generator_output.py`. Tests: `apps/api/tests/unit/test_generator_output.py`
(golden vectors) and `apps/api/tests/unit/test_generator_output_render_path.py`.

## Where it appears

| Surface | Field |
|---|---|
| `POST /api/render` | `parts[i].sha256`, `parts[i].media_type`, `parts[i].instance_id`, `parts[i].variables_url`; top-level `generator_output: {format_version, complete, variables_sha256}` |
| `POST /api/render-stream` (`stream_protocol` 1.2.0) | the same part fields and `generator_output` on `part_done`; `generator_output` on `complete` |
| Artifact store | `<artifact>.variables.json` next to the artifact, e.g. `gears_preview_9f2c1a0b3d_gear.stl.variables.json` |
| Download | `GET /api/projects/<slug>/download/<format>/<artifact>.variables.json` |

The fields appear on both cache paths: a render-cache entry records the sidecar's key and digests, and
an entry without them counts as a miss while the flag is on. Static parts shipped inside a cartridge are
not generated, so they carry none of the fields.

The sidecar keeps the artifact's extension in its name (`….stl.variables.json`). yantra4d's artifact stem
does not depend on the export format, so the STL, 3MF and STEP renders of one instance share a stem. A
bare `<stem>.variables.json` would therefore be overwritten with another format's geometry list.

## Gates and retention

The sidecar is served under exactly the gates of the artifact it describes:

- `/static/<sidecar>`: the private-project gate, because the name carries the slug.
- The download route: privacy, then `access_control` (`download_<format>`), then the tier's export
  formats. The `<format>` in the URL must match the described artifact.

The sidecar is stored through the same artifact store (fs or S3) and is collected by the same 24-hour GC.
Durable instances belong to the consumer (for example Pravara), not to yantra4d's preview cache.

## Flags (`apps/api/config.py`)

| Flag | Default | Effect |
|---|---|---|
| `RENDER_GENERATOR_OUTPUT` | `true` | Write sidecars and add the envelope fields. When off, the engine parameters are unchanged. |
| `RENDER_INJECT_FULL_PARAMS` | `false` | Inject the manifest default of every declared parameter the caller did not send, giving `complete: true`. When off, such parameters are recorded as `source: "source_default"` with `value: null`, because the kernel uses its own source literal. It stays off until the commons' source and manifest defaults agree; turning it on changes their geometry. |
| `RENDER_MATERIAL_INJECTION` | `true` | Legacy `target_material` → `mat_*` / `thermo_*` injection, which is today's behaviour. Injected values are recorded in `legacy_physical_inputs`, never in `variables`. When off, nothing is injected and `target_material` is stripped from the engine payload. |
| `COMMONS_SHA` | unset | The solid commons commit recorded as `generator.commons.sha`. A git checkout of `projects/` answers for itself. |

## Identity

- `variables_sha256` hashes the `[id, value]` pairs only, so provenance changes do not move it.
- `instance_id` hashes `{cartridge, mode, part, tree_sha256, variables_sha256}`. It does not include the
  build or the kernel, so the same design and inputs keep the same id across deploys.
- `geometry[].sha256` records the exact bytes.
- Canonical JSON normalises integral floats to integers before hashing (GOC-1 v1.0.1 §3.1). The slider
  value `12.0` that yantra4d holds and the `12` that another producer holds therefore hash identically.
- `tree_sha256` (`hyperobjects-tree-v1`) covers the cartridge directory. It does not cover shared
  libraries outside it (`libs/*`); `generator.commons.sha` and `generator.kernel` record those.
- `variables` lists every declared parameter of the cartridge, with no mode scoping (GOC-1 v1.0.1 §4.1).
  `render_mode`, `target_part` and `mode` are engine controls and are never variables.
- yantra4d's render API carries no preset identity, so `source` is `request`, `manifest_default` or
  `source_default`, never `preset`.

Not yet covered: the animations route, git `render-head`, the Studio's in-browser WASM renders, and the
"latest render of the slug" consumers (Cotiza export, analysis, simulate).
