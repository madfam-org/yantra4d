"""
Planter Wall — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A modular vertical-garden wall: interlocking pocket modules hang on a base rail and clip
to each other on a grid, so a bare wall becomes a living green field. Each pocket holds
soil with drainage; corner modules close the edges; a base rail screws to the wall and
carries the bottom row.

Three parts (dispatched via `target_part`):
  * "pocket_module" — a soil pocket with drainage + side interlocks + a rear rail hook.
  * "corner_module" — a pocket with one solid closed side (finishes a row edge).
  * "base_rail"     — a wall-screw rail with a repeating ledge the bottom pockets hook onto.

The GRID interlock is the shared CDG: a peg on the +X/top edges and a socket on the -X/
bottom edges at a fixed `module_w` pitch, so modules tile into a wall grid. All prismatic
— fast and watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `module_w`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "pocket_module"))  # pocket_module|corner_module|base_rail

module_w  = float(PARAM(lambda: module_w, 120.0))   # module width / grid pitch (mm)
module_h  = float(PARAM(lambda: module_h,  90.0))   # module height (mm)
pocket_d  = float(PARAM(lambda: pocket_d,  70.0))   # pocket depth out from the wall (mm)
wall      = float(PARAM(lambda: wall,       3.0))   # pocket wall thickness (mm)
peg       = float(PARAM(lambda: peg,        8.0))   # interlock peg size (mm)
drain_dia = float(PARAM(lambda: drain_dia,  6.0))   # drainage hole diameter (mm)
screw_dia = float(PARAM(lambda: screw_dia,  4.5))   # rail wall-screw clearance dia (mm)
fit       = float(PARAM(lambda: fit,        0.4))   # interlock clearance (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
module_w  = max(60.0, min(module_w, 300.0))
module_h  = max(50.0, min(module_h, 200.0))
pocket_d  = max(40.0, min(pocket_d, 160.0))
wall      = max(2.0, min(wall, 8.0))
peg       = max(4.0, min(peg, min(20.0, module_h * 0.2)))
drain_dia = max(3.0, min(drain_dia, 14.0))
screw_dia = max(2.5, min(screw_dia, 10.0))
fit       = max(0.1, min(fit, 1.0))

hw = module_w / 2.0


# ── Pocket body (an open-top box tilted back against the wall) ───────────────
def _pocket_body(close_left):
    """A soil pocket: an open-top box whose back sits against the wall (back face at
    y=0, opening up at +Z). Front lower than back so soil is retained. Drainage holes in
    the floor, a rear hook lip to catch a rail/peg, and side interlocks. `close_left`
    makes the -X side a solid closed wall (for a corner module)."""
    depth = pocket_d
    # Outer shell: box with back at y=0, extends to +Y (out from wall).
    outer = cq.Workplane("XY").box(module_w, depth, module_h, centered=(True, False, False))
    # Hollow the soil cavity, leaving walls + a floor.
    cav = (
        cq.Workplane("XY")
        .box(module_w - 2.0 * wall, depth - 2.0 * wall, module_h, centered=(True, False, False))
        .translate((0, wall, wall))
    )
    body = outer.cut(cav)
    # Slope the front top down for an open planting mouth: cut a wedge off the front-top.
    wedge = (
        cq.Workplane("YZ")
        .polyline([(depth, module_h), (depth, module_h * 0.45), (depth - wall * 2.0, module_h)])
        .close()
        .extrude(module_w + 2.0)
        .translate((-hw - 1.0, 0, 0))
    )
    body = body.cut(wedge)
    # Drainage holes in the floor.
    for sx in (-1.0, 1.0):
        drain = (
            cq.Workplane("XY").center(sx * module_w * 0.22, depth * 0.5)
            .circle(drain_dia / 2.0).extrude(wall + 2.0).translate((0, 0, -1.0))
        )
        body = body.cut(drain)
    # Rear hook lip: an inverted lip on the back-top that hangs on a rail ledge.
    hook = (
        cq.Workplane("YZ")
        .polyline([(0, module_h), (0, module_h - peg * 1.6), (-peg, module_h - peg * 0.6), (-peg, module_h)])
        .close()
        .extrude(module_w * 0.6)
        .translate((-module_w * 0.3, 0, 0))
    )
    body = body.union(hook)
    # Side interlocks: a peg on +X, a socket on -X (unless corner closes -X).
    peg_x = (
        cq.Workplane("XY")
        .box(peg, peg * 2.0, peg, centered=(True, True, False))
        .translate((hw + peg / 2.0 - 0.01, pocket_d * 0.35, module_h * 0.4))
    )
    body = body.union(peg_x)
    if close_left:
        # Corner: fill the -X side flush (already walled) and add a decorative closed panel.
        cap = (
            cq.Workplane("XY")
            .box(wall, depth, module_h, centered=(True, False, False))
            .translate((-hw - wall / 2.0 + 0.01, 0, 0))
        )
        body = body.union(cap)
    else:
        socket = (
            cq.Workplane("XY")
            .box(peg + fit, peg * 2.0 + fit, peg + fit, centered=(True, True, False))
            .translate((-hw + (peg + fit) / 2.0 - 0.005, pocket_d * 0.35, module_h * 0.4))
        )
        body = body.cut(socket)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_pocket_module():
    """A standard interlocking soil pocket."""
    return _pocket_body(close_left=False)


def build_corner_module():
    """A pocket with a closed -X side to finish a row edge."""
    return _pocket_body(close_left=True)


def build_base_rail():
    """A wall-screw rail carrying a repeating ledge the bottom pockets hook onto. A flat
    back plate with a forward-projecting ledge and countersunk screw holes at grid pitch."""
    rail_len = module_w * 2.0            # two-module rail unit
    plate_h = module_h * 0.5
    plate = cq.Workplane("XY").box(rail_len, wall + 2.0, plate_h, centered=(True, False, False))
    # Ledge: a horizontal shelf projecting forward near the top for the hook to sit on.
    ledge = (
        cq.Workplane("XY")
        .box(rail_len, peg + wall, wall, centered=(True, False, False))
        .translate((0, 0, plate_h - wall - peg * 0.6))
    )
    # A small upstand so the hook can't slide off forward.
    upstand = (
        cq.Workplane("XY")
        .box(rail_len, wall, peg, centered=(True, False, False))
        .translate((0, peg + wall - wall, plate_h - wall - peg * 0.6))
    )
    body = plate.union(ledge).union(upstand)
    # Screw holes at grid pitch (one per module) with a shallow countersink.
    n = max(2, int(round(rail_len / module_w)) + 1)
    span = rail_len - 2.0 * max(10.0, screw_dia * 2.0)
    step = span / (n - 1)
    for i in range(n):
        x = -span / 2.0 + i * step
        hole = (
            cq.Workplane("XZ").circle(screw_dia / 2.0).extrude(wall + 4.0)
            .translate((x, -1.0, plate_h * 0.5))
        )
        body = body.cut(hole)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "corner_module":
    result = build_corner_module()
elif target_part == "base_rail":
    result = build_base_rail()
else:
    result = build_pocket_module()
