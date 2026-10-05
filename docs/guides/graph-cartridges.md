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

## How a graph is verified

The keystone (`y4d-spec`) renders a `.graph.json` mode by transpiling it with a
byte-identical vendored copy of this engine (`y4d_spec/graph/`, guarded on both sides:
the keystone's `check_graph_sync.py` and this repo's `check_spec_graph_vendor.py`), then
judging the script on the CadQuery path: watertight, body count, B-Rep validity, presets
and frames — the same bar every script cartridge clears.

A graph authored for a cartridge that already has a script is a **golden twin**: declare
it with `graph_file` next to the script, and `y4d-spec check --render --parity` compares
the two at the defaults and at every preset, at the cross-kernel parity bar. The script is
the oracle; it retires only after parity holds (owner decision D5, 2026-10-04).

```json
{ "id": "flat_idler", "scad_file": "main.py", "cq_file": "main.py",
  "graph_file": "idler.graph.json", "parts": ["flat_idler"] }
```

The first golden twin is `solid-hyperobjects/idler-608/idler.graph.json` (three modes,
exact parity at the defaults and all presets).

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
| Profiles | `profile_rect`, `profile_circle`, `profile_polygon`, `profile_polyline` → `extrude` or `revolve` |
| Booleans | `union`, `cut`, `intersect` |
| Transforms | `translate`, `rotate`, `mirror` (keeps the original), `reflect` (the reflection alone) |
| Selection | `select` (a solid chosen by a boolean `when`) |
| Patterns | `pattern_linear`, `pattern_polar` |
| Finishing | `fillet`, `chamfer`, `shell`, `hole` |

A profile feeds exactly **one** node: CadQuery keeps a profile's wires as pending state
that the first `extrude`/`revolve` consumes, so a second consumer would fail at render.
The transpiler refuses it; duplicate the profile node instead.

`profile_polyline` takes `points`, a closed list of 3–256 `[x, y]` pairs on its `plane`
(lines only; arcs and splines are not in the vocabulary yet).

`select` builds **both** inputs and passes one on: a branch that cannot be built fails the
render even when it is not chosen.

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

### Expressions (graph format 1.1)

A float, count or condition input may be an expression instead of a literal:

```json
{
  "version": "1.1.0",
  "parameters": {
    "width":  { "default": 10 },
    "nema":   { "default": "NEMA17", "map": { "NEMA17": 42.3, "NEMA23": 57 } },
    "gusset": { "default": true }
  },
  "derived": [
    { "id": "body_w", "expr": "nema" },
    { "id": "half",   "expr": "width / 2" }
  ],
  "nodes": [
    { "id": "plate", "type": "box", "params": { "w": { "expr": "body_w + 4" }, "h": { "expr": "half" } } }
  ]
}
```

- **The dialect** is the one the manifest constraints already use
  (`apps/studio/src/lib/safeFormula.ts`): numbers, identifiers, `+ - * / %`, comparisons,
  `&& || !`, `?:` and parentheses; no strings, no function calls; at most 256 characters
  and 128 tokens. It has no `min`/`max`, so a clamp is a ternary pair
  (`x < hi ? x : hi`, then `lo > that ? lo : that`). Semantics are JavaScript's and the
  engine mirrors them exactly: `==` is strict, `%` truncates, `&&`/`||` return booleans,
  both sides of `&&`/`||`/`?:` are evaluated, and `/` or `%` by zero is an error.
- **`parameters`** declares, by manifest parameter id, every value an expression reads.
  The render injects the manifest value; `default` is used when nothing is injected. A
  numeric option string such as `"608"` reads as a number; a non-numeric one needs a `map`.
  A declared parameter that no expression reads is an error.
- **`derived`** is an ordered list of named intermediates; each may read parameters and
  earlier derived ids. An unread derived id is an error.
- A node param takes an expression **or** a manifest `binding`, never both. Selector, axis
  and plane params stay literal.
- Expressions are parsed and validated at transpile time and re-emitted from their syntax
  tree; the generated script contains validated literals, variable reads and a fixed set
  of helpers — never the expression's text.

The node catalog marks which params take an expression (`"expr": true`) and publishes the
dialect limits under `expression`.

## Two rules that follow from the security model

The transpiler emits **only** validated literals and bound-parameter reads;
it never interpolates text into code. Two consequences shape authoring:

**Expressions never become code.** Format 1.0 had no expressions at all, so a derived
value had to be its own parameter (the flange's `count` and `angle`). Format 1.1 adds
them (see "Expressions" above) without giving up the property: an expression is parsed
into a syntax tree at transpile time and re-spelled from that tree, so only validated
numbers, declared variable reads and the engine's own helper calls reach the script.

**Structural params are not bindable.** Selectors (`edges`, `face`), `axis` and
`plane` stay literal, so a render-time value can never change the *shape* of
the emitted code — only its numbers. Numeric params bind freely. Pattern
counts are additionally clamped in the generated script, so a slider wired to a
count cannot detonate a boolean loop inside the render worker.

**`revolve` is bounded.** An unbounded revolve exhausted memory during bring-up, so the
node only accepts inputs whose cost and validity are known before the kernel is called:
the angle is in (0, 360] (OCC silently wraps larger angles); the axis (`x`, `y` or `z`,
through the origin) must lie in the profile's plane, checked at transpile time (an axis
normal to the plane yields a zero-volume solid that still reports itself valid); the
profile may not cross the axis; and it may reach at most 1000 mm from the origin (an
engine convention). The result must be a valid solid with positive volume before
anything consumes it. Loft, sweep and text are still absent.

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

## Editing a graph in Studio

Open a `.graph.json` source in the Studio editor and switch the **Text / Graph**
toggle to **Graph**. The text view and the graph view edit the same buffer: every
graph edit is written back as JSON, and the validation panel under the editor
runs the transpiler's rules on every change.

| You want to | Do this |
|---|---|
| Add a node | **Nodes** opens the palette (built from `graph-node-catalog.json`, so a node the engine adds appears with no Studio change). Click a node type, or drag it onto the canvas. |
| Connect | Drag from a node's output handle (right) to an input socket (left). A socket of the wrong type, or a connection that would make a loop, is refused while you drag; the model's `connect()` refuses it again if anything slips through. |
| Disconnect / delete | Select an edge or node and press Delete or Backspace, or use the inspector's unplug and **Delete** buttons. Deleting a bound node also drops its bindings. |
| Edit a node | Select it. The inspector lists its sockets and params. Each numeric param is a **Value** (a literal, checked against its kind as the server checks it), a **Manifest parameter** (a `binding`), or — once the catalog marks it `"expr": true` — an **Expression**. Structural params (selectors, axes, planes) are literal only. |
| Make it a part | In the inspector, **Output part** maps a manifest part id to the selected solid. |
| Find a problem | Nodes with problems are outlined; the socket or param at fault is red. Click an address such as `cut_1.a:` in the validation panel to select that node. |

Node positions are stored in each node's `meta.position`, which the renderer
ignores; moving a node never triggers a render.

### Expressions, declared parameters and derived values (graph 1.1)

When the node catalog marks a param `"expr": true`, the inspector offers an
**Expression** mode: `{"expr": "width / 2 - wall"}` in the
`apps/studio/src/lib/safeFormula.ts` dialect (at most 256 characters / 128
tokens, or whatever the catalog's `expression` block says). The editor evaluates
it with that same function and shows the value as you type.

- Identifiers are **manifest parameter ids**, and a graph must declare each one it
  reads in its top-level `parameters` object. When an expression reads an
  undeclared manifest parameter, the editor offers **Declare**; the declaration's
  fallback default is the manifest's default.
- A **select** parameter with named options (`NEMA17`, `NEMA23`) has no number
  until its declaration has a `map`. The **Parameters** panel asks for one number
  per option; the editor never guesses them.
- **Derived values** are an ordered list of named intermediates
  (`seat_r = b_od / 2 + press_fit / 2`). Each may read declared parameters and the
  derived values above it; the panel lets you add, edit, reorder and remove them.
- A document that uses `parameters` or `derived` is version **1.1**; the editor
  bumps the version when you add the first declaration. A declared id that is not
  in the manifest is shown as a warning.
- As in the engine, a declared parameter or derived value that no expression reads
  is an error, and a node param cannot carry an expression while a manifest
  parameter also binds it; the editor flags both and does not save until they are
  resolved.

### Saving: a fork, never the commons

Graph saves go through the same `PUT /api/projects/<slug>/files/<path>` the text
editor uses, and the server re-validates the document before writing it. The
editor writes only a project whose `project.meta.json` has a `source.type`, and
the server enforces the same rule: every write route, the bindings route
included, answers a commons cartridge with 403 `read_only_cartridge` and writes
nothing into it.

| Project | Graph edits | Manifest bindings | How to keep your work |
|---|---|---|---|
| Your **fork** (`source.type: "fork"`) | Saved and rendered as you edit (debounced), once the document is valid | Saved with the graph through `PUT /api/projects/<slug>/manifest/bindings` | Save (or Ctrl/Cmd+S) |
| An **imported repository** (`"github"`) | Saved and rendered as you edit | Not editable (the route is fork-only) | Save, then commit and push with the Git panel |
| A **commons cartridge** (no `project.meta.json`) | Kept in the editor only — never written | Not editable | **Export .graph.json**, or **Fork to save** (the existing Fork & Edit flow), then propose it to `solid-hyperobjects` as a pull request yourself |

The bindings route is fork-only (an imported repository gets 403 `not_a_fork`)
and can only set or clear `binding` on parameters the fork's
manifest already has; it rejects unknown parameters, unknown body keys and bodies
over 16 KB, checks the merged binding map against every graph source of the
project with the transpiler, and writes the manifest atomically. The graph is
always written before the bindings that point into it.

Preview is the normal render: after a save, the Studio renders the current mode,
so a fork shows the edited part as soon as the save lands. There is no per-node
preview yet (roadmap item G-PREVIEW), and no in-Studio "propose to the commons as
a pull request" flow.

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
