# Landing models pipeline

How the 3D models on yantra4d.com are produced: from a cartridge in the
commons to the small, meshopt-compressed GLBs the page streams, and the
`manifest.json` that tells the page what exists.

Phase 1 of the landing revamp (plan of record: internal-devops
`docs/strategy/2026-09-18-yantra4d-landing-revamp-plan.md`). The page-side
work — the single WebGL stage, the device tiers, the reader in
`apps/landing/src/lib/models-manifest.ts` — is described there; this guide
covers the asset side.

## The two halves

```
projects/<slug>/            docs/commons-catalog.json
        │                              │
        ▼                              ▼
scripts/dev/render_commons_models.py  ── POST /api/render (LOCAL API) ──▶  apps/landing/public/models/raw/
                                                                                <slug>.glb
                                                                                <slug>.<animation>.<index>.glb
        │
        ▼
scripts/dev/optimize-commons-models.mjs  (npm run models:optimize, from apps/landing)
        │
        ▼
apps/landing/public/models/
    <slug>.lod1.glb                  every cartridge     ≤ 12,288 B, ≤ 2,500 triangles
    <slug>.lod0.glb                  hero cartridges     ≤ 61,440 B, ≤ 25,000 triangles
    <slug>.<animation>.<index>.glb   keyframes           ≤ 61,440 B, ≤ 25,000 triangles
    manifest.json                    v2, see below
```

1. **Render** (`scripts/dev/render_commons_models.py`) asks a local API for
   the default mode of every public cartridge in `docs/commons-catalog.json`
   with `parameters: {}`, plus one render per keyframe of every manifest that
   declares a top-level `animations` array. Multi-part modes are merged into
   one GLB (trimesh). Runs in `.github/workflows/prerender-commons.yml`; it is
   never pointed at `api.yantra4d.com` (the script refuses the host).
2. **Optimize** (`scripts/dev/optimize-commons-models.mjs`) turns each raw GLB
   into the LOD files and writes the manifest. This half needs only Node and
   the landing's devDependencies, so it also runs locally and in tests.

Only the optimized files and the manifest are committed. `raw/` is
gitignored and lives in the workflow's actions/cache between runs.

## What the optimizer does to a mesh

Per input: read → bake every mesh reachable from the scene into **one
world-space triangle soup**, dropping materials, textures, normals, UVs,
colours, skins, cameras, animations and every extension (the page applies its
own material) → **weld** (bitwise) → **simplify** with `MeshoptSimplifier` to
the triangle budget → **quantize** positions to 14 bits
(`KHR_mesh_quantization`) → **meshopt-compress** (`EXT_meshopt_compression`,
level `medium`) → write.

Consequences the page has to know about:

- **Every output carries `POSITION` only** — one mesh, one primitive, no
  material, no normals. three.js's `GLTFLoader` sets `flatShading: true` on
  the material *it* creates when normals are absent; a page material of its own
  must do the same (`new MeshStandardMaterial({ flatShading: true })`) or call
  `geometry.computeVertexNormals()`. CAD parts look right flat-shaded; the
  legacy 2026-03 carousel GLBs were already POSITION-only.
- **Both extensions are `extensionsRequired`.** The loader needs the meshopt
  decoder: `loader.setMeshoptDecoder(MeshoptDecoder)` (`three/examples/jsm/libs/meshopt_decoder.module.js`).
- Geometry is baked in world space; the quantization offset lives on the
  single node's `translation`/`scale`, which every glTF loader applies.
- Outputs are deterministic: same input bytes → same output bytes. No
  timestamps are written into a GLB; the only timestamp is the manifest's
  `generated`, which `--generated <iso>` pins.

### Levels of detail

| File | When | Triangle target | Byte budget |
| :-- | :-- | --: | --: |
| `<slug>.lod1.glb` | every input | `meshes.lod1Triangles` (2,500) | `meshes.lod1Bytes` (12,288) |
| `<slug>.lod0.glb` | `--lod0` selection, and only when it adds triangles over lod1 | `meshes.lod0Triangles` (25,000) | `meshes.lod0Bytes` (61,440) |
| `<slug>.<animation>.<index>.glb` | every keyframe input | `meshes.lod0Triangles` | `meshes.keyframeBytes` (61,440) |

The numbers are the `meshes` block of `apps/landing/perf-budgets.json` — the
one source of truth the CI bundle step, Lighthouse and the e2e assertions also
read. Change them there, never in the script.

Enforcement, in order:

1. The **triangle budget drives the simplifier.** The error bound is loosened
   step by step (`0.001 … 1`, as a fraction of the mesh radius) until the
   target is reached; a mesh already under budget is left intact.
2. If the encoded file is still **over its byte budget**, the triangle target is
   lowered proportionally, a few passes, down to a floor of 64 triangles. The
   report marks such files `byte-capped` (the two dense organic meshes,
   `julia-vase` and `spiral-planter`, land there at lod0).
3. Anything still over budget is listed. **`--strict` makes that exit 1**; the
   files are written either way — nothing is ever silently dropped. Without
   `--strict` it is a warning.

`lod0` is skipped when lod1 already holds every triangle the raw render had
(a second, byte-identical file under another name would help nobody); the
manifest then simply carries no `lod0` for that slug.

`--lod0` accepts `all`, `hero`, `none` or a comma-separated list. The default
is `all` for ≤ 40 inputs and `hero` above that. `hero` is
`apps/landing/models.hero.json` (a JSON array of slugs, or `{ "slugs": [...] }`)
when that file exists, else every manifest under `projects/*` with an
`animations` array (20 cartridges at the time of writing).

## The manifest (v2)

`apps/landing/public/models/manifest.json`, stable key order, sorted by slug:

```json
{
  "version": 2,
  "generated": "2026-09-19T06:11:04Z",
  "generator": "scripts/dev/optimize-commons-models.mjs",
  "source": { "kind": "legacy-glb", "commons_pin": "f2c578f78037c37f0f29fe0571b946aeeb45bc0f" },
  "budgets": { "lod1Bytes": 12288, "lod0Bytes": 61440, "lod1Triangles": 2500, "lod0Triangles": 25000, "keyframeBytes": 61440 },
  "models": [
    {
      "slug": "gridfinity",
      "size": 3896,
      "lod1": { "file": "gridfinity.lod1.glb", "bytes": 3896, "triangles": 772 }
    },
    {
      "slug": "motor-mount",
      "size": 4732,
      "lod1": { "file": "motor-mount.lod1.glb", "bytes": 4732, "triangles": 972 },
      "lod0": { "file": "motor-mount.lod0.glb", "bytes": 41234, "triangles": 18877 },
      "frames": [
        { "animation": "nema-sweep", "index": 0, "file": "motor-mount.nema-sweep.0.glb", "bytes": 30112, "triangles": 12000 }
      ]
    }
  ]
}
```

| Field | Meaning |
| :-- | :-- |
| `version` | `2`. The 2026-03 `prerender-carousel.sh` manifest had no version and only `generated` + `models[].{slug,size}`. |
| `generated` | ISO-8601, second precision. `--generated <iso>` overrides it (tests, byte-comparing two runs). |
| `generator` | Always `scripts/dev/optimize-commons-models.mjs`. |
| `source.kind` | `render-api` when the inputs came from `raw/`; `legacy-glb` when the legacy uncompressed `public/models/<slug>.glb` files were the inputs. |
| `source.commons_pin` | The 40-hex commit the `projects` submodule had checked out, or `null` when it cannot be read. `--commons-pin <sha>\|none` overrides it. |
| `budgets` | The `meshes` block of `perf-budgets.json`, minus its `_comment`. |
| `models[].slug`, `models[].size` | **Kept on every entry**: v1 readers key on `slug` and `size` (`ProjectGalleryContainer` builds its "has a model" set from `models.map(m => m.slug)`). `size` is the byte count of the smallest file the entry offers. |
| `models[].lod1` | `{ file, bytes, triangles }`. Present for every cartridge that had a base render. |
| `models[].lod0` | Same shape; optional (see above). |
| `models[].frames[]` | `{ animation, index, file, bytes, triangles }`, sorted by animation then index; optional. |

Files are addressed relative to the manifest (`/models/<file>` on the site).

## Running it locally

Prerequisites: `npm ci` in `apps/landing` (the optimizer resolves
`@gltf-transform/*` and `meshoptimizer` from there) and, for `--lod0 hero`,
the commons submodule (`git submodule update --init --depth 1 projects`).

```bash
cd apps/landing

# Over a raw/ directory produced by the render half:
npm run models:optimize -- --strict --clean --lod0 hero

# Drift lane: exit 3 when the committed files differ from what the inputs produce.
npm run models:optimize -- --check

# The first run ever (no raw/ directory): the 21 legacy public/models/<slug>.glb
# files are the inputs. --clean removes each legacy file once its lod1 exists.
npm run models:optimize -- --lod0 all --clean --strict
```

Flags: `--in <dir>` (default `public/models/raw`), `--out <dir>` (default
`public/models`), `--lod0 …`, `--strict`, `--check`, `--clean`,
`--generated <iso>`, `--commons-pin <sha>|none`, `--budgets <file>`,
`--quiet`. Exit codes: `0` ok · `1` over budget under `--strict` · `2` usage
or nothing to do · `3` `--check` drift · `4` an input could not be processed
(the others were still written).

`--check` reuses the on-disk manifest's `generated` value, so only content
counts as drift; with `--clean` it also reports files a `--clean` run would
remove. `--clean` retires `*.lod*.glb` / keyframe files that no longer have an
input, and the legacy `<slug>.glb` once its lod1 exists — only when the legacy
file was the input.

The report table (before/after bytes, triangles, budget status) goes to stdout
and, when `$GITHUB_STEP_SUMMARY` is set, to the job summary as Markdown.

### Rendering locally (optional)

The render half needs the backend the way the nightly audit runs it — Redis,
`python app.py` and `apps/worker/render_worker.py`; the API never renders
inline — gated as the top tier so CadQuery cartridges are allowed:

```bash
redis-server --daemonize yes --save "" --appendonly no
cd apps/api
AUTH_ENABLED=false HARNESS_TIER=premium RATE_LIMIT_ENABLED=false PORT=5000 python app.py &
YANTRA4D_BACKEND_PATH=$PWD AUTH_ENABLED=false python ../worker/render_worker.py &
cd ../..
python3 scripts/dev/render_commons_models.py --slugs gridfinity,motor-mount --jobs 2
```

`HARNESS_TIER` is read at `apps/api/config.py` line 94 and honoured only while
`AUTH_ENABLED` is false (docs/AUTH.md § Harness tier). The driver refuses any
`*.yantra4d.com` host: production is never a render farm.

The driver is incremental: `raw/.render-index.json` records, per slug, a hash
of the cartridge directory (docs and images excluded) plus the engine
fingerprint (`/api/health`'s OpenSCAD detail, the CadQuery version, and
whatever `--engine-fingerprint` adds); a slug whose hash and files are present
is skipped, `--force` re-renders anyway, `--hash-only` prints the combined
digest. Keyframes interpolate numeric parameters linearly from `from_state` to
`to_state` over `frames` (integers stay integers, as in the API's own flipbook
route); booleans and strings switch at the midpoint. Unlike
`/api/projects/<slug>/animations/<id>/render`, `t` is not eased — the
manifest's `easing` is for the player's timing.

`raw/` sits under `apps/landing/public/`, which Astro copies verbatim into
`dist/`: delete or move it before a local `astro build` you intend to deploy.

## The workflow

`.github/workflows/prerender-commons.yml` — monthly (the 1st, 06:00 UTC) and
on `workflow_dispatch` with:

| Input | Default | Effect |
| :-- | :-- | :-- |
| `open_pr` | `false` | Commit `apps/landing/public/models` to `chore/commons-models-<run>` and open a PR (`peter-evans/create-pull-request`). |
| `slugs` | *(empty = whole catalog)* | Render only these, `--force`d. A limited run never passes `--clean` to the optimizer, so the other cartridges' LODs stay. |
| `lod0` | `hero` | Passed straight to the optimizer's `--lod0`. |

What it does, on `madfam-runners-blue` (ADR-010), 120 min budget:

1. Checks out with `submodules: true` + `MADFAM_BOT_PAT` (the public commons
   comes in; the `update = none` client mounts stay out), sets up Python 3.12
   and Node 22.
2. Installs OpenSCAD, Redis and the backend exactly as `ci.yml`'s `e2e` job
   does, then starts Redis, `python app.py` (`AUTH_ENABLED=false`,
   `HARNESS_TIER=premium`, `RATE_LIMIT_ENABLED=false`) and the render worker,
   waiting on `/api/health` for both.
3. Computes the cache key: the digest of every cartridge directory folded with
   the engine fingerprint (`openscad --version` + `hashFiles` of
   `apps/api/requirements.txt`, the sandbox lock, `apps/api/services/engine/**`,
   `apps/worker/**`). Restores `raw/` from `actions/cache` (`restore-keys`
   fall back to the newest previous render), renders what changed with four
   requests in flight, and saves the cache even when a render failed.
4. Runs the optimizer with `--strict` (and `--clean` on a full run).
5. Always uploads `apps/landing/public/models` (without `raw/`) as the
   `commons-models-<run>` artifact; uploads the backend/worker logs on failure.
6. With `open_pr`, opens the PR. The org setting "Allow GitHub Actions to
   create and approve pull requests" is off, so this needs `DISPATCH_TOKEN`;
   until it is provisioned the step explains itself in the job summary and the
   branch (and the artifact) are still there to open by hand.
7. A failed render or a `--strict` failure turns the run red **after** the
   upload and the PR, so a single broken cartridge never hides the other 501.

Two caveats worth knowing before dispatching it:

- The API has one render worker and a 120 s per-part wait
  (`RENDER_PART_WAIT_TIMEOUT_SECONDS`), so with four requests in flight a slow
  cartridge can time out its neighbours; the driver retries those with
  backoff. Running several workers would need the worker to drop its
  single-replica assumption first.
- A cartridge that fails and has no raw file from a previous run gets no LODs,
  and a full run's `--clean` retires any it had. The summary lists every
  failure; check it before merging the PR.
