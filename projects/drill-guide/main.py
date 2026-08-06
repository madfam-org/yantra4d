"""
Drill Guide / Bushing Jig — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A jig that guides a drill bit (or a press-fit steel bushing) to repeatable hole
positions on a workpiece. A solid guide block carries one or more full-depth
bores at the chosen diameter; an optional registration lip (fence) hangs below
one edge so the jig drops onto a workpiece edge and indexes off it.

Three patterns, dispatched by `target_part`:
  - linear_guide : a single row of bores at `pitch`, `holes` count.
  - grid_guide   : a rectangular rows×cols array of bores.
  - edge_guide   : bores set back a fixed distance from the fence edge, with a
                   registration lip that references the workpiece edge.

Bushing note: FDM/SLA holes print undersize. For a press-fit steel drill
bushing, oversize `hole_dia` by the printer's hole-shrinkage (typ. +0.1–0.3 mm);
`bushing_fit` exposes that per-side allowance.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `hole_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr — they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
hole_dia    = float(PARAM(lambda: hole_dia,     6.0))   # drill / bushing bore Ø
bushing_fit = float(PARAM(lambda: bushing_fit,  0.2))   # per-side oversize for press-fit bushing
block_thick = float(PARAM(lambda: block_thick, 12.0))   # guide block thickness (bushing length)
wall        = float(PARAM(lambda: wall,         5.0))   # material around each bore
pitch       = float(PARAM(lambda: pitch,       25.0))   # centre-to-centre hole spacing
holes       = int(  PARAM(lambda: holes,          4))   # holes in a linear row
rows        = int(  PARAM(lambda: rows,           3))   # grid rows
cols        = int(  PARAM(lambda: cols,           3))   # grid cols
edge_offset = float(PARAM(lambda: edge_offset, 15.0))   # bore setback from fence edge
fence       = bool( PARAM(lambda: fence,       True))   # registration lip on edge guide
fence_h     = float(PARAM(lambda: fence_h,      8.0))   # fence lip drop below block
fence_t     = float(PARAM(lambda: fence_t,      4.0))   # fence lip thickness

target_part = str(  PARAM(lambda: target_part, "linear_guide"))

# Effective bore diameter (bushing press-fit gets oversize on radius).
bore_dia = hole_dia + 2.0 * max(0.0, bushing_fit)
bore_r = bore_dia / 2.0
# Cell footprint each hole needs (bore + surrounding wall on both sides).
cell = bore_dia + 2.0 * max(1.0, wall)


# ── Helpers ──────────────────────────────────────────────────────────────────
def bore_column(depth):
    """A full-depth cylindrical cutter, base at z=0, tall enough to punch through."""
    return (
        cq.Workplane("XY")
        .circle(bore_r)
        .extrude(depth + 2.0)
        .translate((0, 0, -1.0))
    )


def punch(block, centres, depth):
    """Cut a vertical bore at every (x, y) centre through the block."""
    for (x, y) in centres:
        block = block.cut(bore_column(depth).translate((x, y, 0)))
    return block


def slab(w, d, h):
    """Block centred in X/Y, base at z=0, corners softened for handling."""
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    r = min(cell * 0.25, min(w, d) / 2.0 - 0.5, 3.0)
    if r > 0.3:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


# ── Linear guide ─────────────────────────────────────────────────────────────
def build_linear_guide():
    n = max(1, holes)
    span = (n - 1) * pitch
    w = span + cell
    d = cell
    body = slab(w, d, block_thick)
    centres = [(-span / 2.0 + i * pitch, 0.0) for i in range(n)]
    return punch(body, centres, block_thick)


# ── Grid guide ───────────────────────────────────────────────────────────────
def build_grid_guide():
    nr = max(1, rows)
    nc = max(1, cols)
    span_x = (nc - 1) * pitch
    span_y = (nr - 1) * pitch
    w = span_x + cell
    d = span_y + cell
    body = slab(w, d, block_thick)
    centres = []
    for r in range(nr):
        for c in range(nc):
            centres.append((-span_x / 2.0 + c * pitch, -span_y / 2.0 + r * pitch))
    return punch(body, centres, block_thick)


# ── Edge guide (with registration fence) ─────────────────────────────────────
def build_edge_guide():
    n = max(1, holes)
    span = (n - 1) * pitch
    w = span + cell
    # Depth: room for the setback plus wall behind the bore line.
    d = edge_offset + bore_r + max(1.0, wall)
    body = slab(w, d, block_thick)

    # Fence edge is the -Y face; bores sit edge_offset in from it.
    y_line = -d / 2.0 + edge_offset
    centres = [(-span / 2.0 + i * pitch, y_line) for i in range(n)]
    body = punch(body, centres, block_thick)

    # Registration lip hanging below the -Y edge to hook the workpiece edge.
    if fence and fence_h > 0.1:
        lip = (
            cq.Workplane("XY")
            .box(w, fence_t, fence_h, centered=(True, True, False))
            .translate((0.0, -d / 2.0 + fence_t / 2.0, -fence_h))
        )
        body = body.union(lip)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "grid_guide":
    result = build_grid_guide()
elif target_part == "edge_guide":
    result = build_edge_guide()
else:
    result = build_linear_guide()
