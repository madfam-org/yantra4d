# Bounded WebGL resource probe

Run from `apps/studio` with Node22 and installed dependencies:

```sh
npx vite --config e2e/resource-probe/vite.config.js --host 127.0.0.1 --port 5186 --strictPort
```

Open `http://127.0.0.1:5186/e2e/resource-probe/index.html` in a WebGL-capable
browser and choose **Run 100 model swaps** after the renderer baseline appears.
Reload the page for a new run. The isolated entry point generates synthetic box
STL/GLB assets locally and uses the actual artifact hook, STL worker, GLTF loader
and React Three Fiber canvas. It does not call the render API, write manifests or
add an entry point to the production build.

Two plain boxes first warm the renderer, then unmount. After five frames the
probe records its empty geometry/texture baseline; renderer-owned allocations
may persist without being an asset leak. It then alternates 100 distinct STL/GLB
URLs with two simultaneous consumers, sampling after both consumers load and
five frames render. Each model has a15-second settling deadline that latches a
failure. Final unmount must return geometry and texture counts to the measured
baseline, with no context loss, and active geometry must stay at two throughout.

Save the visible report and a screenshot with browser/version, tested revision
and timestamp. A failed count is evidence to investigate, not a reason to raise
the budget. This is a small-asset lifecycle probe: it does not measure byte-level
GPU memory, texture-heavy scenes, large models, animation grids, browser/WASM
rendering or a production soak. Run the separate deterministic cache/lifecycle
tests as well; see the [ownership contract](../../../../docs/architecture/viewer-resource-ownership.md).

Boundary: this reusable synthetic probe belongs to the platform repository;
private production evidence follows the [repository boundary](../../../../docs/PUBLIC_REPO_BOUNDARY.md).
