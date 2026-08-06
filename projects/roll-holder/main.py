"""
Paper-Towel / Roll Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Holds a paper-towel (or wrap / tape) roll on a spindle sized to the roll's cardboard
CORE inner diameter (`core_dia`). The spindle is the shared interface — a stepped
plug that centres the roll and lets it spin. Three mounts:

  * "wall_holder"    — a back plate with screw holes; the spindle cantilevers out.
  * "under_cabinet"  — an L-bracket that screws up under a cabinet; spindle hangs
                       down-and-out so the roll tucks beneath the shelf.
  * "counter_stand"  — a weighted disc base with a vertical post + top spindle for
                       one-handed tear-off on the countertop.

Spindle socket geometry (the CDG interface):
  spindle nominal radius = core_dia/2 - clearance      (slides into the core)
  a shoulder step (radius core_dia/2 + shoulder) stops the roll sliding off.
  Spindle root is fused into its mount with an overlap for a watertight boolean.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `core_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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
core_dia   = float(PARAM(lambda: core_dia,   44.0))  # roll CORE inner diameter (mm)
spindle_len = float(PARAM(lambda: spindle_len, 130.0))  # spindle length (mm, roll width)
clearance  = float(PARAM(lambda: clearance,   0.6))  # spindle-to-core slide clearance (mm)
wall       = float(PARAM(lambda: wall,        3.0))  # structural wall thickness (mm)
mount      = str(  PARAM(lambda: mount,    "wall"))  # wall | under-cabinet | countertop-weighted
plate_w    = float(PARAM(lambda: plate_w,    60.0))  # back plate / base width (mm)
post_h     = float(PARAM(lambda: post_h,    180.0))  # counter-stand post height (mm)
screw_dia  = float(PARAM(lambda: screw_dia,   4.5))  # mount screw hole diameter (mm)

target_part = str(PARAM(lambda: target_part, "wall_holder"))  # wall_holder|under_cabinet|counter_stand

# ── Clamps ───────────────────────────────────────────────────────────────────
core_dia = max(20.0, min(core_dia, 80.0))
spindle_len = max(40.0, min(spindle_len, 320.0))
clearance = max(0.2, min(clearance, 1.5))
wall = max(2.0, min(wall, 8.0))
plate_w = max(max(30.0, core_dia + 2.0 * wall), min(plate_w, 160.0))
post_h = max(80.0, min(post_h, 400.0))
screw_dia = max(2.5, min(screw_dia, 8.0))

spindle_r = core_dia / 2.0 - clearance         # slides into the core
shoulder_r = core_dia / 2.0 + wall             # stop flange radius
OV = 1.2                                        # boolean overlap for clean unions


# ── Shared spindle (the CDG socket interface) ────────────────────────────────
def spindle(axis_len, taper_tip=True):
    """A horizontal-along-X spindle (built along +Z here, caller rotates it).

    Stepped: a `shoulder` flange at the base stops the roll, then the nominal
    spindle body slides into the core, with an optional slight tip taper so the
    roll starts easily. Returns a Workplane whose base sits at z=0."""
    # Shoulder flange (short, larger disc) at the base.
    flange = cq.Workplane("XY").circle(shoulder_r).extrude(wall)
    body_len = axis_len - wall
    body = cq.Workplane("XY").circle(spindle_r).extrude(body_len).translate((0, 0, wall - OV))
    sp = flange.union(body)
    if taper_tip:
        # Chamfer the free tip so it enters the core easily (non-fatal).
        try:
            sp = sp.faces(">Z").chamfer(min(spindle_r * 0.5, 2.5))
        except Exception:
            pass
    return sp


def _screw_holes(plate, w, h, thickness, n=2):
    """Cut `n` countersink-free screw holes through a vertical back plate.
    Plate lies in the XZ plane spanning width `w` (X) and height `h` (Z), with the
    given `thickness` along Y at y in [-thickness,0]."""
    r = screw_dia / 2.0
    ys = thickness + 2.0
    xs = w * 0.28
    zs = h * 0.30
    pts = [(-xs, h / 2.0 + zs), (xs, h / 2.0 + zs), (-xs, h / 2.0 - zs), (xs, h / 2.0 - zs)]
    use = pts[:2] if n <= 2 else pts
    for (x, z) in use:
        hole = (
            cq.Workplane("XZ")
            .circle(r)
            .extrude(ys)
            .translate((x, 1.0, z))
        )
        plate = plate.cut(hole)
    return plate


# ── Part builders ────────────────────────────────────────────────────────────
def build_wall_holder():
    """Back plate (XZ) with screw holes; spindle cantilevers out along +Y."""
    plate_h = shoulder_r * 2.0 + wall * 2.0
    plate = (
        cq.Workplane("XZ")
        .box(plate_w, plate_h, wall, centered=(True, False, False))
        .translate((0, 0, 0))
    )
    # Plate occupies y:[0,wall] after this? box on XZ extrudes along Y. Recenter.
    plate = plate.translate((0, -wall, 0))
    plate = _screw_holes(plate, plate_w, plate_h, wall, n=2)

    # Spindle: built along +Z, rotate to point along +Y (out from the wall).
    sp = spindle(spindle_len).rotate((0, 0, 0), (1, 0, 0), -90)
    # Place the spindle centre at the plate centre height, protruding from y=0.
    sp = sp.translate((0, 0, plate_h / 2.0))
    body = plate.union(sp)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_under_cabinet():
    """L-bracket: a horizontal top flange (screws up into a cabinet bottom) and a
    short vertical web from which the spindle hangs down-and-out."""
    top_h = shoulder_r * 2.0 + wall * 2.0
    # Horizontal top flange in XY at the top, spanning plate_w (X) by a depth.
    depth = max(50.0, shoulder_r * 2.0 + wall)
    top = cq.Workplane("XY").box(plate_w, depth, wall, centered=(True, True, False)).translate((0, 0, top_h))
    # Screw holes through the top flange.
    r = screw_dia / 2.0
    for (x, y) in [(-plate_w * 0.3, depth * 0.25), (plate_w * 0.3, depth * 0.25),
                   (-plate_w * 0.3, -depth * 0.25), (plate_w * 0.3, -depth * 0.25)]:
        hole = cq.Workplane("XY").circle(r).extrude(wall + 2.0).translate((x, y, top_h - 1.0))
        top = top.cut(hole)
    # Vertical web at the back edge joining flange down to spindle height.
    web = cq.Workplane("XY").box(plate_w, wall, top_h + wall, centered=(True, True, False)).translate((0, -depth / 2.0 + wall / 2.0, 0))
    bracket = top.union(web)
    # Spindle hangs OUT along +Y at the bottom of the web.
    sp = spindle(spindle_len).rotate((0, 0, 0), (1, 0, 0), -90)
    sp = sp.translate((0, -depth / 2.0 + wall, shoulder_r + wall))
    body = bracket.union(sp)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_counter_stand():
    """Weighted disc base + vertical post + top spindle for countertop use."""
    base_r = plate_w / 2.0
    base_h = wall * 2.5
    base = cq.Workplane("XY").circle(base_r).extrude(base_h)
    try:
        base = base.edges("|Z").fillet(min(3.0, base_r * 0.2))
    except Exception:
        pass
    # Hollow ring under the base to save plastic but keep a heavy rim (weighted).
    pocket = cq.Workplane("XY").circle(base_r - wall * 2.0).extrude(base_h - wall).translate((0, 0, wall))
    base = base.cut(pocket)

    # Vertical post rising from the base centre.
    post = cq.Workplane("XY").circle(wall * 1.6).extrude(post_h).translate((0, 0, base_h - OV))
    stand = base.union(post)

    # Top spindle: cantilevers out along +Y from the post top.
    sp = spindle(spindle_len).rotate((0, 0, 0), (1, 0, 0), -90)
    sp = sp.translate((0, 0, base_h + post_h - shoulder_r - wall))
    body = stand.union(sp)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "under_cabinet":
    result = build_under_cabinet()
elif target_part == "counter_stand":
    result = build_counter_stand()
else:
    result = build_wall_holder()
