# Authoring graph cartridges

A graph cartridge defines its geometry as a **node graph** (`*.graph.json`)
instead of a script. The graph engine compiles it server-side into a sandboxed
CadQuery program, so a graph cartridge gets the same kernel, cache, streaming
progress, export formats and tier gating as a CadQuery one — without anyone
writing Python.

Reference cartridges: [`projects/spacer-block/`](../../projects/spacer-block)
(primitives and bindings) and [`projects/flange-plate/`](../../projects/flange-plate)
(profiles, extrude, polar pattern, a derived `expr` spacing, CDG interfaces).

Contract: [`packages/schemas/graph.schema.json`](../../packages/schemas/graph.schema.json).
Generated node catalog (params, defaults, socket types, limits):
[`packages/schemas/graph-node-catalog.json`](../../packages/schemas/graph-node-catalog.json).

## What is NOT verified yet

**The keystone cannot render a graph.** `y4d-spec`'s `mode_sources()` recognises `.py`,
`.cq` and `.scad` only, so a `.graph.json` mode gets **no render bar**: no watertight
check, no body-count check, no cross-kernel parity, no B-Rep validity gate, and no row in
the nightly sweep. Every other cartridge in the commons clears that bar; the two graph
cartridges do not, and the nightly completeness check now *names* them rather than passing
over them silently.

Concretely, this is why 498 of 500 cartridges carry a `verification` block and the two
missing ones are exactly `flange-plate` and `spacer-block`. The structural gates below
(`compliance_audit.py`, `validate_manifests.py`, the generated node catalog, the
transpiler's own cycle/socket/dangling-ref validation) do run on graphs, so a graph cannot
be malformed — but nothing yet proves the *geometry it emits* is sound.

Closing this is lane **G-SPEC**, the first lane of Wave D in
[`ROADMAP.md`](../../ROADMAP.md#the-node-based-geometry-programme-waves-df-s): until it
lands, authoring more graph cartridges grows unverified surface. Treat the render probe in
"Checking your work" below as mandatory rather than advisory for now — it is currently the
only geometric check a graph cartridge gets.

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

- `version` is `1.x`. The minor version records which features the document
  uses: `1.0` is literals and manifest bindings only, `1.1` adds the
  `{"param": id}` and `{"expr": "..."}` param values below. A `1.0` document
  stays valid — the addition is backwards compatible.
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
manifest parameter (or point at the parameter from the graph with
`{"param": id}` — see [Expressions and parameter references](#expressions-and-parameter-references)):

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

## Expressions and parameter references

A numeric param does not have to be a number. It may also be:

```json
{ "id": "ring", "type": "pattern_polar", "inputs": { "shape": "hole" },
  "params": { "count": { "param": "bolt_count" },
              "angle": { "expr": "360 / bolt_count" } } }
```

- **`{"param": id}`** drives the socket from a manifest parameter, written from
  the graph's side. It is exactly equivalent to a manifest `binding` pointing
  here — use one or the other for a given socket; setting both is an error, not
  a precedence puzzle.
- **`{"expr": "..."}`** computes the socket from manifest parameters.

This is what makes a graph *parametric* rather than a frozen script: before
graph v1.1 a derived dimension had to be its own slider, so `flange-plate`
carried both `bolt_count` and a `bolt_spacing_deg` the author had to keep at
`360 / count` by hand. Now the spacing is derived and cannot be misconfigured.

### The dialect

The same one manifest constraints already use
([`apps/studio/src/lib/safeFormula.ts`](../../apps/studio/src/lib/safeFormula.ts)),
so there is one expression language in the product rather than two:

- arithmetic `+ - * / %`, comparison `< <= > >= == != === !==`,
  boolean `&& || !`, a ternary `c ? a : b`, and parentheses;
- numeric literals (`0.5` and `.25` both parse) and identifiers naming manifest
  parameters;
- **no string literals and no function calls** — the tokenizer has no token for
  a quote, a dot, a bracket or a comma, so `constructor.constructor("x")()`
  fails on the `.` rather than being caught by a denylist;
- capped at **256 characters** and **128 tokens**.

An identifier resolves to a manifest parameter (its default, a preset override,
or the value the request carries). **An unknown identifier or a syntax error is
a hard validation error** — reported when the graph is saved in the editor and
again at transpile time, never degraded into a silent literal.

### What gets emitted

An expression is parsed and type-checked at transpile time, then emitted as
arithmetic over the same `_param(...)` probes a binding emits:

```python
float(_expr_div(_expr_num(360), _expr_num(_param(lambda: bolt_count, 6))))
```

So the value is **recomputed at render time** from the live parameter — moving
the `bolt_count` slider moves the spacing with it. An expression that names no
parameter is folded to a number at transpile time instead, and a graph that uses
no expressions transpiles to exactly the script it always did, byte for byte.

A computed `count` is rounded and clamped to `1..200` in the generated script,
the same guard a bound count already had.

### Two rules that follow from the security model

The transpiler emits **only** validated literals, bound-parameter reads, and
arithmetic it assembled itself from a parsed expression; **no character of the
document is ever interpolated into code**. Two consequences shape authoring:

**Only numeric params can be computed.** `float` and `count` params accept
`{"param": …}` and `{"expr": …}`; the generated node catalog marks them
`"computable": true`.

**Structural params are not bindable.** Selectors (`edges`, `face`), `axis` and
`plane` stay literal, so a render-time value can never change the *shape* of
the emitted code — only its numbers. Numeric params bind freely. Pattern
counts are additionally clamped in the generated script, so a slider wired to a
count cannot detonate a boolean loop inside the render worker.

`revolve` is deliberately absent: an unbounded revolve exhausted memory during
bring-up, and the render worker must not host an operation that can hang a job. A
**bounded** revolve is scheduled in lane G-NODES-2, alongside loft, sweep and text — the
memory bound is the design work, not the operation.

## Wiring the manifest

```json
{
  "project": { "slug": "my-part", "engine": "graph" },
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

Graph cartridges are server-only, and the **engine already says so**: a mode
whose engine resolves to `graph` hits rule 1 of the placement table
(`engine_unsupported:graph`, hard), so no manifest flag is needed and none can
change it. `project.force_backend` in particular is now only a SOFT hint that
applies on a `limited` device -- adding it to a graph cartridge buys nothing.
An author who wants an explicit, readable pin should write the HARD key
`render.server_only: true` instead; see
[Render placement](../reference/manifest.md#render-placement-renderserver_only-vs-projectforce_backend).

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

`validate_manifests.py` treats a `projects/<slug>/` directory that is registered
in `.gitmodules` but has no `project.json` as a FAILURE — on CI that means the
submodule fetch broke, and the run would otherwise "pass" by validating only the
cartridges it could see. Submodules marked `update = none` (the client-private
cartridges) are reported as skipped instead. On a local partial checkout, where
leaving submodules uninitialised is normal, pass
`--allow-uninitialised-submodules` (or set
`VALIDATE_MANIFESTS_ALLOW_UNINITIALISED=1`) to downgrade that failure to a skip:

```bash
python3 scripts/qa/validate_manifests.py --allow-uninitialised-submodules
```

Never set it in CI.

## Tier gating

The graph engine is gated by the `graph_engine` key in
[`apps/api/tiers.json`](../../apps/api/tiers.json) — pro and premium. A guest
render of a graph cartridge returns 403 with a message naming the tier, which
is the expected behaviour, not a bug.
