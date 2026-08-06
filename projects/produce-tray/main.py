"""
Egg / Produce Tray — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Stackable trays for storing eggs and produce: a cup array that cradles eggs, a
divided flat tray for produce, and a plain stacking tray. All share one CDG
interface — the cup array (diameter × columns × rows) — and a common stacking lip
so trays nest.

  * "egg_tray"      — an array of round egg CUPS (recesses with a chamfered mouth)
                      that cradle eggs upright, plus a stacking lip.
  * "produce_tray"  — a flat tray divided into a grid of open COMPARTMENTS by
                      interior walls, for berries, tomatoes, small produce.
  * "stacking_tray" — a plain shallow tray with the shared stacking lip, for
                      stacking or as a drip base.

Watertight strategy: solids with pockets CUT in (hollow-by-cut). Cup recesses are
plain cylinders (they tessellate watertight and fast) opening UP through the top
face; a chamfered mouth eases the egg in and is a clean cut cone. Divider walls
and the stacking-lip rim are UNIONED with a small vertical overlap so every
boolean is volumetric (no coincident-face kiss). Fillets are used sparingly and
only on clean blanks. Everything opens up — no trapped voids. No sphere-tangent
unions.

FOOD-CONTACT NOTE: eggs/produce contact the print. Geometry only — food-safe
filament and hygiene are the maker's responsibility (see README).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; parameters injected as bare globals.
  - Access params via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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
cup_dia    = float(PARAM(lambda: cup_dia,    45.0))  # egg-cup diameter (egg ~45mm)
cup_depth  = float(PARAM(lambda: cup_depth,  26.0))  # egg-cup depth (mm)
cols       = int(  PARAM(lambda: cols,          6))  # cups across X
rows       = int(  PARAM(lambda: rows,          2))  # cups across Y
wall       = float(PARAM(lambda: wall,        2.4))  # tray / divider wall (mm)
floor      = float(PARAM(lambda: floor,       2.5))  # tray floor (mm)
stack_lip  = float(PARAM(lambda: stack_lip,   6.0))  # stacking lip height (mm)
compart_h  = float(PARAM(lambda: compart_h,  40.0))  # produce compartment wall height (mm)

target_part = str( PARAM(lambda: target_part, "egg_tray"))  # egg_tray|produce_tray|stacking_tray

# ── Clamps ───────────────────────────────────────────────────────────────────
cup_dia    = max(20.0, min(cup_dia, 90.0))
cup_depth  = max(8.0,  min(cup_depth, 60.0))
cols       = max(1,    min(cols, 8))
rows       = max(1,    min(rows, 8))
wall       = max(1.6,  min(wall, 6.0))
floor      = max(1.6,  min(floor, 8.0))
stack_lip  = max(2.0,  min(stack_lip, 15.0))
compart_h  = max(10.0, min(compart_h, 80.0))

cup_r = cup_dia / 2.0


# ── Helpers ──────────────────────────────────────────────────────────────────
def _cup_cutter(mouth_r, dep, top_z):
    """A cup recess cutter: a cylinder with a chamfered mouth. Opens `over` above
    `top_z` so the cut opens cleanly through the top face. Cylinders tessellate
    watertight and fast (no pole singularity). The chamfer is a short cut cone at
    the mouth that eases an egg in."""
    over = 1.0
    body = cq.Workplane("XY").circle(mouth_r).extrude(dep + over).translate((0, 0, top_z - dep))
    # Chamfer the mouth: a cut cone widening from mouth_r up to mouth_r+ch.
    ch = min(2.0, dep * 0.15)
    if ch > 0.2:
        try:
            cone = (
                cq.Workplane("XY")
                .circle(mouth_r)
                .workplane(offset=ch + over)
                .circle(mouth_r + ch)
                .loft(combine=True)
                .translate((0, 0, top_z - ch))
            )
            body = body.union(cone)
        except Exception:
            pass
    return body


def _tray_blank(tray_w, tray_d, tray_h, do_fillet=True):
    body = cq.Workplane("XY").box(tray_w, tray_d, tray_h, centered=(True, True, False))
    if do_fillet:
        try:
            body = body.edges("|Z").fillet(min(wall * 1.2, 4.0))
        except Exception:
            pass
    return body


def _stack_lip(tray_w, tray_d, base_h):
    """A hollow-prism rim standing on the tray top so trays nest. Outer = tray
    footprint, inner = footprint minus a wall — a real-thickness rim fused with a
    vertical overlap (volumetric union). No fillet on the rim (kept cheap)."""
    ov = 1.0
    outer = cq.Workplane("XY").box(tray_w, tray_d, stack_lip + ov, centered=(True, True, False))
    inner = cq.Workplane("XY").box(
        tray_w - 2.0 * wall, tray_d - 2.0 * wall, stack_lip + ov + 2.0,
        centered=(True, True, False),
    )
    rim = outer.cut(inner)
    return rim.translate((0, 0, base_h - ov))


# ── Part builders ────────────────────────────────────────────────────────────
def build_egg_tray():
    """Array of egg cups in a tray with a stacking lip."""
    cell = cup_dia + wall
    tray_w = cols * cell + wall
    tray_d = rows * cell + wall
    tray_h = floor + cup_depth

    body = _tray_blank(tray_w, tray_d, tray_h)

    # Combined cup cutter (union of all cups), single cut.
    x0 = -(cols - 1) * cell / 2.0
    y0 = -(rows - 1) * cell / 2.0
    cutter = None
    for i in range(cols):
        for j in range(rows):
            x = x0 + i * cell
            y = y0 + j * cell
            c = _cup_cutter(cup_r, cup_depth, tray_h).translate((x, y, 0))
            cutter = c if cutter is None else cutter.union(c)
    if cutter is not None:
        body = body.cut(cutter)

    body = body.union(_stack_lip(tray_w, tray_d, tray_h))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_produce_tray():
    """A flat tray divided into a grid of open compartments by interior walls."""
    cell = cup_dia + wall
    ncx = max(2, cols)
    ncy = max(2, rows)
    tray_w = ncx * cell + wall
    tray_d = ncy * cell + wall
    tray_h = floor + compart_h

    body = _tray_blank(tray_w, tray_d, tray_h)
    cavity = (
        cq.Workplane("XY")
        .box(tray_w - 2.0 * wall, tray_d - 2.0 * wall, compart_h + 1.0, centered=(True, True, False))
        .translate((0, 0, floor))
    )
    body = body.cut(cavity)

    # Interior divider walls rising from the floor (build one combined solid).
    dividers = None
    for i in range(1, ncx):
        x = -tray_w / 2.0 + wall + i * cell - wall / 2.0
        w = (
            cq.Workplane("XY")
            .box(wall, tray_d - 2.0 * wall, compart_h, centered=(True, True, False))
            .translate((x, 0, floor))
        )
        dividers = w if dividers is None else dividers.union(w)
    for j in range(1, ncy):
        y = -tray_d / 2.0 + wall + j * cell - wall / 2.0
        w = (
            cq.Workplane("XY")
            .box(tray_w - 2.0 * wall, wall, compart_h, centered=(True, True, False))
            .translate((0, y, floor))
        )
        dividers = w if dividers is None else dividers.union(w)
    if dividers is not None:
        body = body.union(dividers)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_stacking_tray():
    """A plain shallow tray with the shared stacking lip (drip base / nesting)."""
    cell = cup_dia + wall
    tray_w = max(2, cols) * cell + wall
    tray_d = max(2, rows) * cell + wall
    tray_h = floor + 8.0

    body = _tray_blank(tray_w, tray_d, tray_h)
    cavity = (
        cq.Workplane("XY")
        .box(tray_w - 2.0 * wall, tray_d - 2.0 * wall, tray_h - floor + 1.0, centered=(True, True, False))
        .translate((0, 0, floor))
    )
    body = body.cut(cavity)
    body = body.union(_stack_lip(tray_w, tray_d, tray_h))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "produce_tray":
    result = build_produce_tray()
elif target_part == "stacking_tray":
    result = build_stacking_tray()
else:
    result = build_egg_tray()
