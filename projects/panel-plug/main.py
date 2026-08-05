"""
Panel / Blind Grommet & Plug — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A snap-in plug that fills an unused knockout hole in a panel or enclosure. The
body passes through the hole; a flange caps the top face; a snap ring/lip below
the panel retains it. The snap groove is sized to `panel_t` so the flange and
lip clamp the panel between them.

Three types, dispatched by `target_part`:
  - blind_plug   : a solid closed plug (blanks the hole).
  - cable_grommet: a plug with a central cable bore `cable_dia` (edge-protecting
                   grommet for a wire run).
  - vented_plug  : a plug with radial slots for airflow.

Snap fit: the lip must flex to pass the hole, so printed clearance matters —
`snap_fit` sets the lip engagement and `hole_fit` the shank clearance;
tolerance_by_material is declared.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `hole_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr. Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
hole_dia   = float(PARAM(lambda: hole_dia,   20.0))   # knockout hole diameter
panel_t    = float(PARAM(lambda: panel_t,     2.0))   # panel thickness (snap grip)
hole_fit   = float(PARAM(lambda: hole_fit,    0.3))   # shank-to-hole clearance (per side)
snap_fit   = float(PARAM(lambda: snap_fit,    1.2))   # snap-lip radial engagement
flange_w   = float(PARAM(lambda: flange_w,    3.0))   # flange overhang past the hole
flange_t   = float(PARAM(lambda: flange_t,    2.0))   # flange thickness (cap height)
cable_dia  = float(PARAM(lambda: cable_dia,   8.0))   # grommet cable bore
vents      = int(  PARAM(lambda: vents,          6))  # vented-plug slot count
wall       = float(PARAM(lambda: wall,        2.0))   # grommet/plug wall thickness

target_part = str(PARAM(lambda: target_part, "blind_plug"))

# Geometry derived from the knockout.
hole_r = hole_dia / 2.0
shank_r = hole_r - max(0.0, hole_fit)             # body slips through the hole
flange_r = hole_r + max(0.5, flange_w)            # cap overhangs the hole
snap_r = shank_r + max(0.3, snap_fit)             # lip catches under the panel
shank_h = panel_t + flange_t                      # body spans panel + a little
lip_h = max(1.2, min(2.5, panel_t * 0.9))         # snap lip height


# ── Shared plug body (flange + shank + snap lip) ─────────────────────────────
def plug_body():
    """Build the retaining structure: top flange (z:[0,flange_t]), a shank down
    through the panel, and a barbed snap lip on the underside."""
    # Flange cap.
    flange = cq.Workplane("XY").cylinder(flange_t, flange_r).translate((0, 0, flange_t / 2.0))
    try:
        flange = flange.edges(">Z").chamfer(min(0.8, flange_t * 0.4))
    except Exception:
        pass

    # Shank passing through the hole (hangs below the flange).
    shank = (
        cq.Workplane("XY")
        .cylinder(shank_h, shank_r)
        .translate((0, 0, -shank_h / 2.0))
    )

    body = flange.union(shank)

    # Snap lip: a barb whose max radius = snap_r at the panel underside, tapering
    # to shank_r at its lower tip so it can flex inward on insertion.
    lip_top_z = -panel_t                # engages just under the panel
    lip_bot_z = lip_top_z - lip_h
    lip = (
        cq.Workplane("XY")
        .workplane(offset=lip_bot_z)
        .circle(shank_r)                # narrow tip (leads into the hole)
        .workplane(offset=lip_h)
        .circle(snap_r)                 # wide catch (grips under the panel)
        .loft(combine=True)
    )
    body = body.union(lip)
    return body


# ── Blind plug ───────────────────────────────────────────────────────────────
def build_blind_plug():
    """Solid closed plug. Hollow the underside from the lip tip upward so the
    snap lip can flex on insertion and to save material (leaves `wall` all round;
    the flange stays a closed cap so the hole is truly blanked)."""
    body = plug_body()
    inner_r = shank_r - wall
    depth = shank_h + lip_h - flange_t - wall
    if depth > 0.5 and inner_r > 0.8:
        cav = (
            cq.Workplane("XY")
            .cylinder(depth, inner_r)
            .translate((0, 0, -(panel_t + lip_h) + depth / 2.0))
        )
        body = body.cut(cav)
    return body


# ── Cable grommet ────────────────────────────────────────────────────────────
def build_cable_grommet():
    body = plug_body()
    # Central through-bore for the cable, with a top lead-in chamfer.
    c_r = min(cable_dia / 2.0, shank_r - 1.0)
    bore = (
        cq.Workplane("XY")
        .cylinder(flange_t + shank_h + lip_h + 4.0, c_r)
        .translate((0, 0, flange_t - (flange_t + shank_h + lip_h + 4.0) / 2.0))
    )
    body = body.cut(bore)
    try:
        body = body.faces(">Z").chamfer(min(1.0, c_r * 0.5))
    except Exception:
        pass
    return body


# ── Vented plug ──────────────────────────────────────────────────────────────
def build_vented_plug():
    body = plug_body()
    # Radial ventilation slots cut through the flange + shank top.
    n = max(2, vents)
    slot_w = max(1.5, flange_r * 0.16)
    slot_len = flange_r * 1.1
    for k in range(n):
        ang = 360.0 / n * k
        slot = (
            cq.Workplane("XY")
            .box(slot_len, slot_w, flange_t + panel_t + 2.0, centered=(False, True, True))
            .translate((0, 0, flange_t - (flange_t + panel_t) / 2.0))
            .rotate((0, 0, 0), (0, 0, 1), ang)
        )
        # Keep a solid centre column so the plug stays one piece.
        body = body.cut(slot.translate((max(3.0, shank_r * 0.35) * math.cos(math.radians(ang)),
                                        max(3.0, shank_r * 0.35) * math.sin(math.radians(ang)), 0)))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cable_grommet":
    result = build_cable_grommet()
elif target_part == "vented_plug":
    result = build_vented_plug()
else:
    result = build_blind_plug()
