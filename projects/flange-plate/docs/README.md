# Bolt-Circle Flange Plate

A round flange with a centered bore and a polar bolt circle, defined as a node
graph ([`flange.graph.json`](../flange.graph.json)) and compiled server-side by
the graph engine.

## Variants

| Mode | Part | Use |
| :-- | :-- | :-- |
| Drilled Flange | `flange` | Full bolt circle — bolt straight to a motor face, pipe flange or bearing mount |
| Blank Plate | `blank` | Bore only; mark and drill the pattern by hand |

## What it demonstrates

This is the cartridge that exercises the graph vocabulary beyond primitives:

- `profile_circle` → `extrude` — the sketch-then-extrude workflow
- `pattern_polar` — one bolt-hole cutter repeated around the circle, then cut
  from the plate in a single boolean
- `chamfer` on `>Z` — breaks the top edges, including around every hole

## Parameters

All eight controls are manifest **bindings** into node params. `edge_chamfer`
drives both variants' chamfer nodes at once.

**On bolt count and spacing:** the graph format deliberately has no expressions
— every emitted value is a literal or a bound parameter, which is what keeps
the transpiler safe. So `bolt_count` and `bolt_spacing_deg` are independent
controls, and an evenly spaced circle wants `spacing = 360 / count`
(6 holes → 60°, 8 holes → 45°, 4 holes → 90°).

## Interfaces

Declares two CDG interfaces — `bolt_circle` (`bolt_pattern`) and `center_bore`
(`socket`) — so it joins the works-with graph alongside the other cartridges
that speak the same geometry.

## License

CERN-OHL-W-2.0 — see the manifest `attribution` block.
