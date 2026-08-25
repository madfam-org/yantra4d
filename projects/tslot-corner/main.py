"""
T-Slot Corner Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Corner joiners for aluminium T-slot extrusion (2020 / 2040 / OpenBuilds).
The bracket bolts INTO the extrusion's T-slots with M5 fasteners (via drop-in
tee-nuts), so the interface geometry is the real 20 mm module grid and the M5
clearance hole spacing that lands one bolt in each slot, centred 10 mm from the
extrusion corner.

Extrusion table (module = face pitch, slot = channel opening, screw = fastener):
  2020 → 20 mm module, 6 mm slot, M5      2040 → 20 mm module (40 mm wide face)
  3030 → 30 mm module, 8 mm slot, M6      4040 → 40 mm module, 8 mm slot, M8
The bolt lands on the slot centre-line, i.e. module/2 from the extrusion edge.

Modes (dispatched via `target_part`):
  * "corner_2way"  — a flat right-angle plate (two legs) with one M5 hole per
                     leg; the workhorse inside-corner brace.
  * "corner_gusset"— the two-way plate reinforced with a triangular web rib
                     spanning the inner angle, for load-bearing frames.
  * "corner_3way"  — a solid cubic corner block joining THREE extrusions meeting
                     at a vertex (X, Y, Z), one counter-bored M5 per arm.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>) — no globals()/eval/getattr.
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


# ── Extrusion table (module, slot opening, fastener clearance) ───────────────
EXTRUSIONS = {
    "2020": {"module": 20.0, "slot": 6.0, "bolt": 5.5},
    "2040": {"module": 20.0, "slot": 6.0, "bolt": 5.5},
    "3030": {"module": 30.0, "slot": 8.0, "bolt": 6.6},
    "4040": {"module": 40.0, "slot": 8.0, "bolt": 9.0},
}


def extr_spec(key):
    k = str(key).strip().lower().replace("series", "").replace(" ", "")
    return EXTRUSIONS.get(k, EXTRUSIONS["2020"])


# ── Parameters ───────────────────────────────────────────────────────────────
series       = str(  PARAM(lambda: series,      "2020"))   # 2020|2040|3030|4040
thickness    = float(PARAM(lambda: thickness,     6.0))    # bracket plate thickness (mm)
leg_len      = float(PARAM(lambda: leg_len,      30.0))    # length of each leg (mm)
width        = float(PARAM(lambda: width,        20.0))    # bracket width across the face (mm)
bolt_dia     = float(PARAM(lambda: bolt_dia,      0.0))    # override M-clearance (0 = from table)
fillet_r     = float(PARAM(lambda: fillet_r,      3.0))    # inner/outer corner fillet (mm)

target_part = str(PARAM(lambda: target_part, "corner_2way"))  # corner_2way|corner_gusset|corner_3way


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = extr_spec(series)
module = spec["module"]
bolt_d = bolt_dia if bolt_dia > 0.1 else spec["bolt"]
bolt_d = max(2.5, min(bolt_d, 12.0))

thickness = max(3.0, min(thickness, 12.0))
# Width can't be wider than the extrusion face nor thinner than the bolt head.
width = max(bolt_d + 6.0, min(width, module * 2.0))
# Leg must be long enough to seat a bolt centred at module/2 from the corner.
leg_len = max(module * 0.75 + bolt_d, min(leg_len, 120.0))
fillet_r = max(0.0, min(fillet_r, min(width, leg_len) * 0.3))

bolt_off = module / 2.0                 # bolt centre = slot centre-line from edge
head_d = bolt_d * 1.9                    # M5 socket-cap head ~9.5 for 5 mm bolt
head_depth = min(thickness * 0.5, bolt_d * 0.6)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _cbore_z(body, points, z_top, through_h):
    """Counter-bored M-holes drilled DOWN from z_top (‑Z through the plate)."""
    if not points:
        return body
    shaft = (
        cq.Workplane("XY")
        .pushPoints(points)
        .circle(bolt_d / 2.0)
        .extrude(-(through_h + 1.0))
        .translate((0, 0, z_top + 0.5))
    )
    body = body.cut(shaft)
    cbore = (
        cq.Workplane("XY")
        .pushPoints(points)
        .circle(head_d / 2.0)
        .extrude(-(head_depth + 0.01))
        .translate((0, 0, z_top + 0.01))
    )
    return body.cut(cbore)


def _hole_x(body, points, x_face, through_len):
    """M-holes bored along +X from the y-z face at x=x_face (for 3-way arms)."""
    if not points:
        return body
    cutter = (
        cq.Workplane("YZ")
        .pushPoints(points)
        .circle(bolt_d / 2.0)
        .extrude(-(through_len + 1.0))
        .translate((x_face + 0.5, 0, 0))
    )
    return body.cut(cutter)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_two_way(with_gusset=False):
    """Right-angle plate: a horizontal leg (+X) and a vertical leg (+Z) sharing a
    corner block at the origin. One counter-bored M-hole in each leg, landing on
    the slot centre-line. Optional triangular web across the inner angle."""
    t = thickness
    # Horizontal leg: a slab lying in the XY plane, extruded up by t.
    horiz = (
        cq.Workplane("XY")
        .box(leg_len, width, t, centered=(False, True, False))
    )
    # Vertical leg: a slab standing in the YZ/XZ plane, extruded up in +Z.
    vert = (
        cq.Workplane("XY")
        .box(t, width, leg_len, centered=(False, True, False))
    )
    body = horiz.union(vert)

    if with_gusset:
        # Triangular web spanning the inner angle in the XZ plane, full width.
        web = min(leg_len - 2.0, module * 1.5)
        rib = (
            cq.Workplane("XZ")
            .workplane(offset=width / 2.0)
            .polyline([(t, t), (web, t), (t, web)])
            .close()
            .extrude(-width)
        )
        body = body.union(rib)

    # Outer-corner fillet on the far vertical spine edges (|Y edges of the block).
    if fillet_r > 0.05:
        try:
            body = body.edges("|Y and >X").fillet(min(fillet_r, t * 0.49))
        except Exception:
            pass

    # Bolt in the horizontal leg (drilled down through its top face at z=t).
    hpt = [(bolt_off, 0.0)]
    body = _cbore_z(body, hpt, t, t)
    # Bolt in the vertical leg (bored along +X at x=t, centred at z=bolt_off).
    vpt = [(0.0, bolt_off)]   # (y, z) on the YZ face
    body = _hole_x(body, vpt, t, t)
    return body


def build_three_way():
    """A cubic corner block with three arms along +X, +Y, +Z, each an extension
    that bolts to one extrusion. One M-hole bored down each arm's outer face."""
    t = thickness
    cube = max(width, module) * 0.9
    cube = min(cube, module * 1.6)
    arm_w = min(width, cube)

    # Central cube at the origin corner.
    body = cq.Workplane("XY").box(cube, cube, cube, centered=(False, False, False))
    # Arms: rectangular prisms extending each axis beyond the cube.
    arm_x = cq.Workplane("XY").box(leg_len, arm_w, t, centered=(False, False, False))
    arm_y = (
        cq.Workplane("XY")
        .box(arm_w, leg_len, t, centered=(False, False, False))
    )
    arm_z = (
        cq.Workplane("XY")
        .box(t, arm_w, leg_len, centered=(False, False, False))
    )
    body = body.union(arm_x).union(arm_y).union(arm_z)

    if fillet_r > 0.05:
        try:
            body = body.edges("|Z and >X and >Y").fillet(min(fillet_r, t * 0.49))
        except Exception:
            pass

    # X-arm bolt: drilled down (−Z) through the arm top at z=t.
    body = _cbore_z(body, [(cube + bolt_off, arm_w / 2.0)], t, t)
    # Y-arm bolt: drilled down (−Z) through the arm top at z=t.
    body = _cbore_z(body, [(arm_w / 2.0, cube + bolt_off)], t, t)
    # Z-arm bolt: bored along +X into the arm at x=t, centred (y=arm_w/2, z=cube+bolt_off).
    body = _hole_x(body, [(arm_w / 2.0, cube + bolt_off)], t, t)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "corner_3way":
    result = build_three_way()
elif target_part == "corner_gusset":
    result = build_two_way(with_gusset=True)
else:
    result = build_two_way(with_gusset=False)
