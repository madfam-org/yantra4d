# Viewer resource ownership

The Studio's [artifact loader](../../apps/studio/src/hooks/render/useWorkerLoader.ts)
owns displayed geometry for the lifetime of one URL/format request. Model and ghost
viewers receive separate mutable geometry, even when they share an STL fetch and
parse. A stress-color or geometry edit in one consumer cannot modify another.

The [STL cache](../../apps/studio/src/lib/stlPayloadCache.ts) retains CPU arrays,
never rendered Three.js objects. Its least-recently-used policy allows at most
16 completed entries and 32 MiB of backing buffers. Hits refresh recency; larger
payloads can still be displayed but are not retained. Byte accounting includes
the whole backing allocation of a typed-array view, counting shared buffers only
once within an entry. Cache identity includes the same-origin bearer identity;
these memory-only keys must never be logged or persisted.

Pending parsing is shared separately and retains the existing 120-second worker
deadline. Clearing or changing a URL releases that consumer's geometry, clears
its retained result and hides old output immediately. An A/B/A transition creates
a new request identity; it cannot resurrect A's disposed object. The singleton
worker remains reusable across consumers and is terminated on a worker error or
deadline, settling all requests attached to that worker.

For GLTF/GLB, each load owns its scene resources. The
[resource helpers](../../apps/studio/src/lib/viewerResources.ts) release temporary
world-space clones after analysis geometry is merged. Request cleanup releases
the merged geometry, loaded geometries, materials, textures and skeletons, with
deduplication for resources shared inside that load. Late results are disposed
instead of being published. Owned image bitmaps are closed; if a caller enables
Three.js's optional global cache, bitmap lifetime belongs to that external cache.
The Studio does not enable it. React render and memoization never allocate GLTF
analysis geometry, so an abandoned render cannot strand those allocations.

These budgets cover completed STL cache retention, **not total browser memory**.
Active consumer copies, concurrent pending loads, network buffers, GLTF assets,
WASM heaps and driver allocations have separate lifetimes. Large individual
models and sustained GPU/heap behavior still require measured device testing.
This loader change does not introduce an artifact-size limit or a concurrency
admission policy.

The animated assembly grid uses a separate
[assembly fetcher](../../apps/studio/src/services/domain/assemblyFetcher.ts), whose
parameter cache is not covered by this budget and still needs an eviction policy.
The [grid](../../apps/studio/src/components/viewer/AnimatedGrid.tsx) owns one clone
per cell and part, reuses it across color/wireframe changes, and disposes it when
the assembly changes or the grid unmounts. Starting a replacement fetch clears
the previous displayed assembly. The source geometry retained by the fetcher
belongs to that cache and is not disposed by the grid. Active grid allocations
still scale with the number of cells and parts; this is not an application-wide
memory bound. [Grid regressions](../../apps/studio/src/components/viewer/AnimatedGrid.test.jsx)
cover rerender reuse, replacement cleanup and unmount cleanup.

Regression evidence lives in the [loader lifecycle tests](../../apps/studio/src/hooks/render/useWorkerLoader.test.js),
[cache-budget tests](../../apps/studio/src/lib/stlPayloadCache.test.js) and
[resource cleanup tests](../../apps/studio/src/lib/viewerResources.test.js).
They cover shared consumers, StrictMode, stale results, 64 model replacements,
1,000 distinct cache insertions, byte/entry limits, world transforms and cleanup.
These are deterministic resource tests, not a production GPU soak measurement.
The [bounded WebGL probe](../../apps/studio/e2e/resource-probe/README.md) separately
measures actual renderer allocation counts across 100 STL/GLB swaps with two
consumers. Its warmed baseline distinguishes renderer-owned textures from
retained model allocations; it remains a small-asset lifecycle check.

[Blank-viewer troubleshooting](../guides/troubleshooting.md#blank-viewer--no-stl)
and [release cache identity](../operations/render-artifact-storage.md#cache-identity-across-releases)
describe the neighboring artifact-delivery contracts.
[README](../../README.md) · [Documentation index](../index.md) ·
[Compact LLM context](../../llms.txt) · [Full LLM context](../../llms-full.txt).

Boundary: reusable platform mechanisms belong here; private operational evidence
follows the [repository boundary](../PUBLIC_REPO_BOUNDARY.md).
