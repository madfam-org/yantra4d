# Vendored: the hyperobject graph core

This is a **vendored copy** of the kernel-neutral graph core of RFC 0067 (owner ruling
G-2, 2026-11-20): graph format 1.2, typed sockets, the expression dialect, validation,
declarations with i18n label keys, licence and provenance, the node-pack interface and the
`script` node contract. The **canonical source** is the keystone,
`madfam-org/hyperobjects-spec` › `src/hyperobject_graph/`; the contract is that repo's
`docs/GRAPH_CORE.md`.

Do **not** hand-edit anything under `src/hyperobject_graph/` — change the keystone and
re-vendor. The package is stdlib-only and imports nothing outside itself, so this
directory is the whole dependency.

This is the mirror of the graph **engine**, which is canonical here
(`apps/api/services/engine/graph_engine.py`) and vendored into the keystone. The engine is
the solid node pack; the core is what every pack (solid here, soft in Fashion Cabinet,
sheet in Pliego) shares.

## Drift guard (both directions)

- `scripts/qa/check_graph_core_vendor.py` (blocking in `ci.yml`): every vendored file's
  sha256 equals `src/hyperobject_graph/core.lock.json`, and the lock lists exactly the
  vendored files. An edit here goes red.
- `scripts/qa/check_graph_core_vendor.py --spec` (in `spec-conformance` and
  `spec-nightly`, where the keystone is installed at `SPEC_PIN`): the installed keystone's
  `core.lock.json` equals the vendored one. A core change in the keystone goes red here
  at the next pin move until the copy is refreshed. A pin that predates the core stands
  the comparison down in one line.

## Re-vendoring

```sh
# from a checkout with both repos side by side:
rm -rf packages/hyperobject-graph/src/hyperobject_graph
cp -R ../hyperobjects-spec/src/hyperobject_graph packages/hyperobject-graph/src/
find packages/hyperobject-graph -name __pycache__ -prune -exec rm -rf {} +
shasum -a 256 packages/hyperobject-graph/src/hyperobject_graph/core.lock.json
# → put that digest and the keystone commit in CANONICAL_LOCK_SHA256 / CANONICAL_COMMIT
#   at the top of scripts/qa/check_graph_core_vendor.py, in the same commit
python3 scripts/qa/check_graph_core_vendor.py
```

`core.lock.json` comes with the copy; there is no `--update` here, because the lock is
the keystone's statement of what it published, and the guard pins that lock's own digest
so a copy and its lock cannot be edited together. Moving `SPEC_PIN` is its own step.
Until `SPEC_PIN` reaches a keystone that carries the core (`5516b052` or later), the
`--spec` direction stands down in one line; the pinned lock digest is what holds the
copy in the meantime.

Once a shared MADFAM Python registry exists, replace this copy with a plain dependency on
the keystone and delete the guard, as `packages/commons-sandbox/VENDORED.md` says for the
sandbox core.
