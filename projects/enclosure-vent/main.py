"""Enclosure Vent — Ventilation Louvre / Grille Panel (Yantra4D Hyperobject).

Ventilation panels for electronics enclosures: a solid mounting panel with an
airflow cutout pattern and a screw-mount border. Three distinct profile modes:

  * louvre_panel — angled downward-raked louver slats (weather / sight shielded)
    cut through the panel, so air passes but line-of-sight and falling debris do
    not.
  * hex_grille   — a honeycomb of hexagonal through-holes: maximum open area with
    a stiff cell wall (the classic fan grille).
  * slot_vent    — parallel straight slots (obround) — the simplest high-flow
    vent, easy to print without supports.

Watertightness note: a "vent" mesh is still a solid body — the openings are
boolean cuts through a solid panel (each opens front→back, no trapped void). The
whole opening pattern is unioned into ONE cutter and subtracted once (fast +
robust). The panel border is filleted BEFORE cutting.

Sandbox contract (cq_runner.py): `cq`+`math` pre-injected; params bare globals
via PARAM(lambda: name, default); final solid assigned to `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "louvre_panel"))
panel_w     = float(PARAM(lambda: panel_w,  80.0))   # panel width (mm)
panel_h     = float(PARAM(lambda: panel_h,  80.0))   # panel height (mm)
thick       = float(PARAM(lambda: thick,     3.0))   # panel thickness (mm)
border      = float(PARAM(lambda: border,    6.0))   # solid border / frame (mm)
open_size   = float(PARAM(lambda: open_size, 6.0))   # slat gap / hex flat / slot width
rib         = float(PARAM(lambda: rib,       2.0))   # material between openings
louvre_ang  = float(PARAM(lambda: louvre_ang, 30.0)) # louver rake angle (deg)
screw_d     = float(PARAM(lambda: screw_d,   3.2))   # M3 corner screw clearance

panel_w = max(30.0, min(panel_w, 200.0))
panel_h = max(30.0, min(panel_h, 200.0))
thick   = max(2.0, min(thick, 8.0))
border  = max(3.0, min(border, 20.0))
open_size = max(2.0, min(open_size, 20.0))
rib     = max(1.0, min(rib, 8.0))
louvre_ang = max(10.0, min(louvre_ang, 45.0))
screw_d = max(2.0, min(screw_d, 6.0))


def _fillet_safe(wp, selector, radius):
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _panel_blank():
    """Filleted solid panel + corner screw holes; returns (body, field_w,
    field_h) where field_* is the ventable interior span."""
    body = cq.Workplane("XY").box(panel_w, panel_h, thick, centered=(True, True, False))
    body = _fillet_safe(body, "|Z", min(border * 0.6, panel_w / 10.0))
    # Corner screw holes through the border.
    hx = panel_w / 2.0 - border / 2.0
    hy = panel_h / 2.0 - border / 2.0
    holes = None
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            h = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(sx * hx, sy * hy, -1.0))
                .circle(screw_d / 2.0).extrude(thick + 2.0)
            )
            holes = h if holes is None else holes.union(h)
    body = body.cut(holes)
    field_w = panel_w - 2.0 * border
    field_h = panel_h - 2.0 * border
    return body, field_w, field_h


def _obround(wp, length, width):
    """Stadium wire on the current plane (robust vs arc fans)."""
    r = width / 2.0
    straight = max(0.0, length - width)
    return (
        wp.moveTo(-straight / 2.0, r)
        .lineTo(straight / 2.0, r)
        .threePointArc((straight / 2.0 + r, 0), (straight / 2.0, -r))
        .lineTo(-straight / 2.0, -r)
        .threePointArc((-straight / 2.0 - r, 0), (-straight / 2.0, r))
        .close()
    )


# ── louvre_panel ─────────────────────────────────────────────────────────────
def build_louvre_panel():
    """Angled louver slats cut through the panel. Each slat is an obround slot
    cut on a raked plane so the opening is shielded from straight-on sight/rain.
    Cutters are rectangular prisms rotated about X and swept through the panel."""
    body, field_w, field_h = _panel_blank()

    slat_pitch = open_size + rib
    n = max(1, min(120, int(field_h / slat_pitch)))
    slot_len = field_w
    # Extra length so the raked cut passes fully through the thickness.
    over = thick / math.tan(math.radians(louvre_ang)) + 4.0
    y0 = -((n - 1) * slat_pitch) / 2.0
    cutter = None
    for i in range(n):
        cy = y0 + i * slat_pitch
        c = (
            cq.Workplane("XZ")
            .center(0, 0)
        )
        c = _obround(c, slot_len, open_size)
        c = (
            c.extrude(thick + over)
            .translate((0, -(thick + over) / 2.0, 0))
            .rotate((0, cy, 0), (1, cy, 0), louvre_ang)
            .translate((0, cy, thick / 2.0))
        )
        cutter = c if cutter is None else cutter.union(c)
    if cutter is not None:
        body = body.cut(cutter)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── hex_grille ───────────────────────────────────────────────────────────────
def build_hex_grille():
    """A honeycomb of hexagonal through-holes on a staggered grid."""
    body, field_w, field_h = _panel_blank()

    flat = open_size                      # hex across-flats
    # Cap the cell count so a large panel with tiny holes cannot explode the
    # boolean (each hex is a separate union). If needed, widen the effective
    # pitch until the grid fits the budget — the pattern stays uniform.
    max_cells = 600
    eff = 1.0
    while True:
        col_pitch = (flat + rib) * eff
        row_pitch = (flat + rib) * math.sqrt(3.0) / 2.0 * eff
        ncols = max(1, int(field_w / col_pitch))
        nrows = max(1, int(field_h / row_pitch))
        if ncols * nrows <= max_cells or eff > 6.0:
            break
        eff *= 1.25
    hexr = flat / math.sqrt(3.0)          # circumradius (point-to-centre)
    x0 = -((ncols - 1) * col_pitch) / 2.0
    y0 = -((nrows - 1) * row_pitch) / 2.0

    cutter = None
    for r in range(nrows):
        stagger = (col_pitch / 2.0) if (r % 2) else 0.0
        for c in range(ncols):
            cx = x0 + c * col_pitch + stagger
            cy = y0 + r * row_pitch
            if abs(cx) > field_w / 2.0 - flat * 0.4:
                continue
            hexcut = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(cx, cy, -1.0))
                .polygon(6, 2.0 * hexr)
                .extrude(thick + 2.0)
            )
            cutter = hexcut if cutter is None else cutter.union(hexcut)
    if cutter is not None:
        body = body.cut(cutter)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── slot_vent ────────────────────────────────────────────────────────────────
def build_slot_vent():
    """Parallel straight (obround) slots — simple high-flow, print-friendly."""
    body, field_w, field_h = _panel_blank()

    slot_pitch = open_size + rib
    n = max(1, min(120, int(field_h / slot_pitch)))
    slot_len = field_w
    y0 = -((n - 1) * slot_pitch) / 2.0
    cutter = None
    for i in range(n):
        cy = y0 + i * slot_pitch
        c = cq.Workplane("XY").transformed(offset=cq.Vector(0, cy, -1.0))
        c = _obround(c, slot_len, open_size).extrude(thick + 2.0)
        cutter = c if cutter is None else cutter.union(c)
    if cutter is not None:
        body = body.cut(cutter)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "hex_grille":
    result = build_hex_grille()
elif target_part == "slot_vent":
    result = build_slot_vent()
else:
    result = build_louvre_panel()
