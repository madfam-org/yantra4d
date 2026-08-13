# Sim4D extraction record

**Decision (2026-08-13):** Sim4D is stripped for parts into this repository and
then archived. MADFAM maintains one repo. This document records what was taken,
what was deliberately left behind, and how to retrieve anything left.

Source: `madfam-org/sim4d` @ `cd116386e22c758c26d06286a7dfd7fd0cd2f8fb` — the
`main` HEAD frozen by archiving. The audit was performed at `8780dd85` (last
substantive commit, 2026-07-04); the only change between the two is a
Dependabot config consolidation, so no code went unexamined.

Archiving a GitHub repository makes it read-only, not invisible: it stays
clonable, so nothing recorded here is lost, only frozen. Checked before
archiving — no open pull requests, no open issues, and the single leftover
branch (`docs/truthful-status`) differs from `main` only by a reverted
Dependabot config, its documentation commit having already landed.

## Why extraction rather than integration

Three parallel audits found sim4d to be a parts bin, not a product: the default
studio build renders an empty viewport (the working three.js renderer is a dead
import), `packages/viewport` is `export {}` behind a 702-line README describing
an API that does not exist, every FEA/CFD opcode dispatches to a handler that
was never written, and CI was failing on 20 of 20 recent runs. `sim4d.com`
resolves to a parking IP and serves nothing, so there were no users to migrate.

What was real: the graph document model, a clean DAG evaluator, a genuine
OCCT 7.8 wasm build, the node editor UX, a Yjs collaboration server, and a 2D
constraint solver.

## Extracted

| From sim4d | Now lives at | Notes |
| :-- | :-- | :-- |
| `.bflow.json` document format | `packages/schemas/graph.schema.json` | Renamed `.graph.json`, version 1.x actually enforced. Sim4d stamped a version nothing read and had no migration path. |
| Node vocabulary (`nodes-core` concepts) | `apps/api/services/engine/graph_engine.py` | Reimplemented as a transpiler vocabulary with typed sockets. Generated for clients into `packages/schemas/graph-node-catalog.json`. |
| `GraphManager` (engine-core) | `apps/studio/src/lib/graph/graphDocument.ts` | Ported algorithms: mutation, dirty/downstream propagation, cycle detection, validation, serialization. See deviations below. |
| Graph evaluation model | `apps/api/services/engine/graph_engine.py` | Server-side: graphs compile to sandboxed CadQuery. Sim4d's `WorkerAPI` seam is unnecessary when one kernel does the work. |

### Deliberate deviations from the sim4d originals

- **One representation of connectivity.** Sim4d stored edges twice — an
  `edges[]` array *and* per-node `inputs` — synchronised by hand on every
  mutation. Our format stores connectivity once, in `inputs`; the UI derives
  edges. One representation cannot disagree with itself.
- **Loading validates.** Sim4d's `fromJSON` was a bare `JSON.parse`, so a
  malformed graph failed later and somewhere else. Ours validates on parse and
  reports every problem at once.
- **Iterative cycle detection.** The original recursed per node; ours uses an
  explicit stack so a deep chain cannot overflow.
- **No silent fake geometry.** Sim4d's DAG engine caught a missing OCCT and
  returned echo objects shaped like geometry, so a broken kernel looked like a
  working one. Not carried over — the server fails loudly.
- **The `isolated-vm` scripting path was not ported.** It is a static top-level
  import of a native Node module inside engine-core; it breaks browser bundling
  and we have no use for in-graph scripting.

## Deliberately left behind

Retrievable from the archived repo at the SHA above. Left because porting dead
code costs maintenance, coverage and clarity for value we cannot yet use.

| Part | State in sim4d | Why not now |
| :-- | :-- | :-- |
| `packages/collaboration` | Real: ~7.4k LOC, genuine Yjs CRDT, Express/Socket.IO server, Dockerfile — but 88 typecheck errors, `dist/` never built, disabled by default in production | The best candidate to return. Multi-user graph editing needs a node editor first (Phase 2) and a paying reason (white-label tenants). |
| `packages/constraint-solver` | Real: Newton-Raphson with finite-difference Jacobian, 2D sketch constraints, the repo's most substantive test | Has no consumer anywhere in sim4d and no sketcher UI. Retrieve when we build sketch-based authoring. |
| `packages/engine-occt` wasm + build | OCCT 7.8 vendored, build script functional as of Nov 2025. Shipped binaries expose only primitives, booleans, fillet/chamfer, tessellate; the full 26-operation surface (`extrude`, `revolve`, `importSTEP`, `exportSTEP`) exists in an orphaned 33 MB `occt_geometry.wasm` with no loader | Client-side B-Rep is Phase 3 and may never be needed: the server already has the full kernel. The binding source is `cpp/occt_bindings.cpp:932-973` and the build script is `scripts/build-occt.sh` if we revisit. |
| `packages/nodes-core` generated tree | 886 generated node definitions imported; only about a dozen evaluate against implemented opcodes | Overwhelmingly dispatch to opcodes that do not exist. Our vocabulary is small and every node is verified to produce real geometry. |
| `packages/version-control` | No `package.json`, no `index.ts`, zero importers; a real graph diff/merge fragment inside 31 unimplemented interfaces | The diff/merge algorithms may be worth salvaging into the Git panel later. |
| `apps/studio`, `apps/marketing` | React 18 / ReactFlow 11 / zustand 4 against our React 19 studio | Yantra4D's shell is the product. Phase 2 builds a fresh canvas; sim4d's interaction patterns are the reference, not its code. |
| Simulation nodes (FEA/CFD/modal) | Elaborate typed definitions dispatching to opcodes with no handler anywhere | There is no simulation compute in sim4d. Shipping these would violate the honest-labelling rule that already governs our FEA-proxy copy. |

## Licensing

Sim4D was MPL-2.0 with **zero** files carrying the "Incompatible With Secondary
Licenses" marker, so its code combines into this AGPL-3.0 repository cleanly
(MPL-2.0 §3.3). MADFAM holds 100% of the copyright — `git shortlog -sn --all`
shows no external contributor has ever committed and there is no CLA — so
ported files are simply relicensed AGPL-3.0 on ingestion, with provenance noted
in the file header.

Obligations that do **not** transfer, because the corresponding code was not
taken: OCCT's LGPL-2.1 notice and source-availability duty (the vendored tree
stays in the archived repo), CuraEngine LGPL-3.0 (never shipped compiled), and
`@madfam/geom-core` Apache-2.0. They return if the wasm build is ever extracted.

## Retrieving something later

```bash
git clone https://github.com/madfam-org/sim4d
cd sim4d && git checkout cd116386e22c758c26d06286a7dfd7fd0cd2f8fb
```

Treat that repository's prose as unverified: its `.enclii.yml` describes a
product that does not exist, its README badges point at a dead GitHub org, and
its node counts disagree with each other by an order of magnitude. Verify any
claim against the code before relying on it.
