# Authoring graph cartridges

A graph cartridge defines its geometry as a **node graph** (`*.graph.json`)
instead of a script. The graph engine compiles it server-side into a sandboxed
CadQuery program, so a graph cartridge gets the same kernel, cache, streaming
progress, export formats and tier gating as a CadQuery one — without anyone
writing Python.

Reference cartridges: [`projects/spacer-block/`](../../projects/spacer-block)
(primitives and bindings) and [`projects/flange-plate/`](../../projects/flange-plate)
(profiles, extrude, polar pattern, CDG interfaces).

Contract: [`packages/schemas/graph.schema.json`](../../packages/schemas/graph.schema.json).
Generated node catalog (params, defaults, socket types, limits):
[`packages/schemas/graph-node-catalog.json`](../../packages/schemas/graph-node-catalog.json).

## The shape of a graph

```json
{
  "version": "1.0.0",
  "units": "mm",
  "nodes": [
    { "id": "outline", "type": "profile_circle", "params": { "r": 45 } },
    { "id": "plate", "type": "extrude", "inputs": { "profile": "outline" }, "params": { "height": 8 } },
    { "id": "bore", "type": "cylinder", "params": { "r": 12, "h": 400 } },
    { "id": "drilled", "type": "cut", "inputs": { "a": "plate", "b": "bore" } }
  ],
  "outputs": { "flange": "drilled" }
}
```

- Every node has a unique `id` (a plain identifier) and a `type`.
- `inputs` reference other nodes **by id**. Connectivity is stored once, here —
  there is no separate edge list to keep in sync.
- `outputs` maps a **part id** to the node that produces it. Part ids
  correspond to `parts[].id` in the manifest; the renderer selects one per
  request. Every output must be a solid.

## Node vocabulary

Nodes produce either a **solid** or a **profile** (a 2D sketch that only
`extrude` consumes). The transpiler enforces socket types, so wiring a profile
where a solid belongs fails at validation rather than at render.

| Group | Nodes |
|-------|-------|
| Solids | `box`, `cylinder`, `sphere` |
| Profiles | `profile_rect`, `profile_circle`, `profile_polygon` → `extrude` |
| Booleans | `union`, `cut`, `intersect` |
| Transforms | `translate`, `rotate`, `mirror` |
| Patterns | `pattern_linear`, `pattern_polar` |
| Finishing | `fillet`, `chamfer`, `shell`, `hole` |

The catalog file is generated from the engine itself, so it is always the
accurate list — including each param's kind, default and whether it can be
bound. Regenerate it with:

```bash
python3 scripts/qa/generate_graph_catalog.py
```

CI fails if the committed catalog drifts from the engine.

## Wiring parameters

A graph's own values are defaults. To expose a control, add a `binding` to a
manifest parameter:

```json
{
  "id": "plate_radius",
  "type": "slider",
  "default": 45.0, "min": 15.0, "max": 120.0, "step": 1.0,
  "binding": "outline.r",
  "label": { "en": "Plate radius (mm)", "es": "Radio de la placa (mm)" }
}
```

`binding` is `"nodeId.param"`, or a **list** of them when one control should
drive several nodes at once — the flange's `edge_chamfer` drives the chamfer on
both variants:

```json
"binding": ["flange.distance", "blank.distance"]
```

Each node param may be driven by at most one manifest parameter.

## Two rules that follow from the security model

The transpiler emits **only** validated literals and bound-parameter reads;
it never interpolates text into code. Two consequences shape authoring:

**There are no expressions.** A derived value must be its own parameter. A
polar pattern therefore exposes both `count` and `angle` rather than computing
`360 / count`, and the cartridge documents that an even circle wants
`spacing = 360 / count`. This is a deliberate trade: no expression evaluator
means no evaluator to escape.

**Structural params are not bindable.** Selectors (`edges`, `face`), `axis` and
`plane` stay literal, so a render-time value can never change the *shape* of
the emitted code — only its numbers. Numeric params bind freely. Pattern
counts are additionally clamped in the generated script, so a slider wired to a
count cannot detonate a boolean loop inside the render worker.

`revolve` is deliberately absent: an unbounded revolve exhausted memory during
bring-up, and the render worker must not host an operation that can hang a job.

## Wiring the manifest

```json
{
  "project": { "slug": "my-part", "engine": "graph", "force_backend": true },
  "modes": [
    { "id": "main", "scad_file": "part.graph.json", "engine": "graph",
      "parts": ["flange"], "label": { "en": "Flange", "es": "Brida" },
      "estimate": { "base_units": 1, "formula": "per_part" } }
  ],
  "export_formats": ["stl", "3mf", "step", "glb", "gltf", "obj"]
}
```

The engine is inferred from the `.graph.json` extension, so `"engine": "graph"`
is optional but worth stating. `export_formats` at the **top level** is
required by the metadata gate — omit it and `compliance_audit.py --strict`
fails and the studio format selector stays hidden.

Graph cartridges are backend-only: there is no browser path, so set
`force_backend: true`.

## Checking your work

Render both variants through the real pipeline before committing:

```bash
python3 - <<'EOF'
import json, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, "apps/api")
from services.engine.graph_engine import transpile
doc = json.load(open("projects/my-part/part.graph.json"))
script = Path(tempfile.gettempdir()) / "probe.py"
script.write_text(transpile(doc, {}, "part.graph.json"))
out = "/tmp/probe.stl"
r = subprocess.run([sys.executable, "apps/api/services/engine/cq_runner.py",
                    str(script), out, json.dumps({"target_part": "flange"}), "stl"],
                   capture_output=True, text=True, timeout=240)
print("rc:", r.returncode, "bytes:", Path(out).stat().st_size if Path(out).exists() else 0)
print(r.stdout[-400:] if r.returncode else "")
EOF
```

Then the gates CI will run:

```bash
python3 scripts/qa/compliance_audit.py --strict
python3 scripts/qa/validate_manifests.py
python3 scripts/qa/generate_commons_catalog.py
python3 scripts/qa/check_licenses.py
```

## Tier gating

The graph engine is gated by the `graph_engine` key in
[`apps/api/tiers.json`](../../apps/api/tiers.json) — pro and madfam. A guest
render of a graph cartridge returns 403 with a message naming the tier, which
is the expected behaviour, not a bug.
