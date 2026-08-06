"""
Duct / Vent Register Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

HVAC transition fittings that bridge the mismatches every duct run hits: a round
branch that has to meet a rectangular register (a "boot"), a 6" trunk that has to
neck down to a 4" take-off, or a wall register in one size feeding a duct in
another. Pick the two port geometries and the fitting morphs between them.

Real dimensions (US residential sheet-metal standards, expressed in mm):
  - Round duct nominal IDs: 4"=101.6, 5"=127.0, 6"=152.4 mm.
  - Rectangular register / boot openings: 4x10", 4x12", 6x10", 6x12"
    (101.6x254.0, 101.6x304.8, 152.4x254.0, 152.4x304.8 mm).
  A register "boot" is the straight variant here: a rectangular outlet lofted to a
  round throat, the pattern sold as a straight register boot.

Watertightness strategy (the fitting is a genuine hollow duct, yet a closed
2-manifold):
  Each transition is a SOLID lofted frustum (outer wall) from which a concentric
  THROUGH lumen is cut end to end. Because the lumen pierces solid material, each
  end face becomes an ANNULUS (a wall-thick ring), not an open circle — so the
  surface (outer wall + two annular rims + inner lumen wall) is one sealed manifold
  with no boundary edges. Both the outer wall and the lumen are built with
  `cq.Solid.makeLoft([wire_bottom, wire_top])`, which lofts arbitrary sections
  (round <-> rounded-rectangle) robustly where Workplane.loft() cannot. Straight
  collars and any flange are unioned as fully overlapping solids, never tangent
  plates. No end is ever left as an open shell (an open tube has boundary loops ->
  not watertight).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Standard port sizes (mm) ─────────────────────────────────────────────────
ROUND_ID = {"4in": 101.6, "5in": 127.0, "6in": 152.4}
RECT_WH = {
    "4x10": (254.0, 101.6),
    "4x12": (304.8, 101.6),
    "6x10": (254.0, 152.4),
    "6x12": (304.8, 152.4),
}


def round_id(name):
    """Round-duct inside diameter (mm), defaulting to 6in."""
    return ROUND_ID.get(name, ROUND_ID["6in"])


def rect_wh(name):
    """Rectangular opening (width, height) in mm, defaulting to 6x10."""
    return RECT_WH.get(name, RECT_WH["6x10"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "round_reducer"))
round_a = str(PARAM(lambda: round_a, "6in"))       # larger / inlet round size
round_b = str(PARAM(lambda: round_b, "4in"))       # smaller / outlet round size
rect_size = str(PARAM(lambda: rect_size, "6x10"))  # register opening
wall = float(PARAM(lambda: wall, 1.8))             # sheet-wall thickness (mm)
length = float(PARAM(lambda: length, 90.0))        # transition length (mm)
collar = float(PARAM(lambda: collar, 20.0))        # straight collar at each end (mm)
corner_r = float(PARAM(lambda: corner_r, 8.0))     # rectangular corner fillet (mm)
flange = bool(PARAM(lambda: flange, True))         # add a mounting flange on the rect face

# Clamp to sane build ranges so extreme UI values still render watertight.
wall = max(1.0, min(wall, 4.0))
length = max(30.0, min(length, 200.0))
collar = max(6.0, min(collar, 40.0))
corner_r = max(0.0, min(corner_r, 20.0))


# ── Cross-section wires (positioned at a given z) ────────────────────────────
def _round_wire(radius, z):
    """A circular wire of `radius`, centered on Z, lying in the plane at height z."""
    return cq.Workplane("XY").workplane(offset=z).circle(radius).val()


def _rrect_wire(w, h, r, z):
    """A rounded-rectangle wire w x h with corner radius r, in the plane at z."""
    hw, hh = w / 2.0, h / 2.0
    rr = max(0.0, min(r, (min(w, h) / 2.0) - 0.2))
    wp = cq.Workplane("XY").workplane(offset=z)
    if rr <= 0.05:
        return wp.rect(w, h).val()
    return (
        wp.moveTo(-hw + rr, -hh)
        .lineTo(hw - rr, -hh)
        .radiusArc((hw, -hh + rr), rr)
        .lineTo(hw, hh - rr)
        .radiusArc((hw - rr, hh), rr)
        .lineTo(-hw + rr, hh)
        .radiusArc((-hw, hh - rr), rr)
        .lineTo(-hw, -hh + rr)
        .radiusArc((-hw + rr, -hh), rr)
        .close()
        .val()
    )


def _section_wire(kind, geom, z, grow):
    """Wire for a section at height z. `grow` (mm) inflates it (wall for outer, 0
    for the lumen). kind 'round' -> geom = radius; 'rect' -> geom = (w, h, r)."""
    if kind == "round":
        return _round_wire(geom + grow, z)
    w, h, r = geom
    return _rrect_wire(w + 2 * grow, h + 2 * grow, r + grow, z)


def _loft(kind_b, geom_b, kind_t, geom_t, z0, z1, grow):
    """Solid lofted between the two sections from z0 to z1 (via cq.Solid.makeLoft)."""
    wb = _section_wire(kind_b, geom_b, z0, grow)
    wt = _section_wire(kind_t, geom_t, z1, grow)
    return cq.Workplane(obj=cq.Solid.makeLoft([wb, wt]))


def _prism(kind, geom, z0, z1, grow):
    """Straight prism of a single section from z0 to z1."""
    if kind == "round":
        return cq.Workplane("XY").workplane(offset=z0).circle(geom + grow).extrude(z1 - z0)
    w, h, r = geom
    ww, hh, rr = w + 2 * grow, h + 2 * grow, r + grow
    base = _rrect_wire(ww, hh, rr, z0)
    return cq.Workplane(obj=cq.Solid.extrudeLinear(base, [], cq.Vector(0, 0, z1 - z0)))


def _build_transition(sec_bot, sec_top):
    """Outer frustum with collars, minus a through lumen -> one watertight solid.
    sec_bot / sec_top are ('round', radius) or ('rect', (w, h, r))."""
    kb, gb = sec_bot
    kt, gt = sec_top
    total = length + 2.0 * collar
    z_bc = collar             # top of bottom collar
    z_tc = collar + length    # bottom of top collar

    # ---- OUTER solid: bottom collar + lofted body + top collar ----
    outer = _prism(kb, gb, 0.0, z_bc, wall)
    outer = outer.union(_loft(kb, gb, kt, gt, z_bc, z_tc, wall))
    outer = outer.union(_prism(kt, gt, z_tc, total, wall))

    # ---- INNER lumen (grow=0): pierces both end faces (overshoot by 1 mm) ----
    inner = _prism(kb, gb, -1.0, z_bc, 0.0)
    inner = inner.union(_loft(kb, gb, kt, gt, z_bc, z_tc, 0.0))
    inner = inner.union(_prism(kt, gt, z_tc, total + 1.0, 0.0))

    solid = outer.cut(inner)

    # ---- Optional flange on the rectangular end ----
    if flange and (kb == "rect" or kt == "rect"):
        if kt == "rect":
            w, h, r = gt
            plate = _prism("rect", (w, h, r), total - 4.0, total, wall + 10.0)
            hole = _prism("rect", (w, h, r), total - 6.0, total + 2.0, 0.0)
        else:
            w, h, r = gb
            plate = _prism("rect", (w, h, r), 0.0, 4.0, wall + 10.0)
            hole = _prism("rect", (w, h, r), -2.0, 6.0, 0.0)
        plate = plate.cut(hole)
        solid = solid.union(plate)

    try:
        solid = solid.clean()
    except Exception:
        pass
    return solid


# ── Part builders (three distinct fittings) ──────────────────────────────────
def build_round_reducer():
    """Round-to-round concentric reducer: big round trunk down to a smaller take-off."""
    ra = round_id(round_a) / 2.0
    rb = round_id(round_b) / 2.0
    if abs(ra - rb) < 1.0:  # keep the loft non-degenerate
        rb = ra - 6.0
    return _build_transition(("round", ra), ("round", rb))


def build_register_boot():
    """Rectangular register opening lofted to a round throat — a straight boot."""
    w, h = rect_wh(rect_size)
    rb = round_id(round_b) / 2.0
    return _build_transition(("rect", (w, h, corner_r)), ("round", rb))


def build_rect_reducer():
    """Rectangular-to-rectangular reducer between two register sizes."""
    w1, h1 = rect_wh(rect_size)
    w2 = max(90.0, w1 - 60.0)
    h2 = max(70.0, h1 - 20.0)
    return _build_transition(
        ("rect", (w1, h1, corner_r)),
        ("rect", (w2, h2, max(4.0, corner_r - 2.0))),
    )


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "register_boot":
    result = build_register_boot()
elif target_part == "rect_reducer":
    result = build_rect_reducer()
else:
    result = build_round_reducer()
