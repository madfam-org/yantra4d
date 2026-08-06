"""
Bottle / Can Koozie Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A sleeve / adapter that fits a small can or bottle into a larger cup holder, and
insulates it. Two parts:
  - "sleeve"  : a straight or tapered sleeve. Inner bore holds the vessel; outer
                wall can taper (different top vs bottom diameter) to wedge into a
                holder or match a tumbler shape.
  - "adapter" : steps a small-diameter vessel up to a larger holder diameter — the
                bore matches the vessel (inner dia) and the outside matches the
                holder (outer dia); an optional base closes the bottom.

Diameters are given as the VESSEL inner diameter and the HOLDER outer diameter, so
the interface is dimensionally real: the printed bore = vessel dia + fit clearance,
and the outside = holder dia − fit clearance.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
inner_dia   = float(PARAM(lambda: inner_dia,   66.0))   # vessel (can/bottle) dia (mm)
outer_dia   = float(PARAM(lambda: outer_dia,   90.0))   # holder / cup-holder dia (mm)
height      = float(PARAM(lambda: height,      95.0))   # sleeve height (mm)
taper       = float(PARAM(lambda: taper,        6.0))   # top-vs-bottom dia change (mm)
wall        = float(PARAM(lambda: wall,         3.0))   # min wall thickness (mm)
fit_clear   = float(PARAM(lambda: fit_clear,    0.5))   # bore/outside fit clearance (mm)
base        = bool( PARAM(lambda: base,        True))   # closed insulating base
base_th     = float(PARAM(lambda: base_th,      3.0))   # base thickness (mm)

target_part = str(PARAM(lambda: target_part, "sleeve"))  # sleeve | adapter

# ── Clamp for sane, watertight geometry ──────────────────────────────────────
inner_dia = max(30.0, inner_dia)
# Outer must be at least inner + 2*wall so the wall is real.
outer_dia = max(outer_dia, inner_dia + 2.0 * wall + 2.0)
height = max(20.0, height)
wall = max(1.2, min(wall, (outer_dia - inner_dia) / 2.0 - 0.5))
fit_clear = max(0.0, min(fit_clear, wall - 0.5))
base_th = max(1.0, min(base_th, height - 2.0))
# Taper can't remove more than most of the wall at the narrow end.
max_taper = max(0.0, (outer_dia - inner_dia) - 1.0)
taper = max(0.0, min(taper, max_taper))

# ── Real interface radii ─────────────────────────────────────────────────────
# Bore holds the vessel: vessel dia + clearance for a slip fit.
bore_r = (inner_dia + fit_clear) / 2.0
# Outside meets the holder: holder dia − clearance so it drops in.
out_r = (outer_dia - fit_clear) / 2.0


# ── Helpers ──────────────────────────────────────────────────────────────────
def _tube(r_out_bottom, r_out_top, r_bore, h, base_closed, base_h):
    """A (optionally tapered) round tube. Outer radius goes from r_out_bottom at
    z=0 to r_out_top at z=h (a cone frustum if they differ). A straight cylindrical
    bore of radius r_bore is cut; if base_closed, the bore starts at base_h."""
    if abs(r_out_top - r_out_bottom) < 0.05:
        outer = cq.Workplane("XY").circle(r_out_bottom).extrude(h)
    else:
        outer = (
            cq.Workplane("XY")
            .circle(r_out_bottom)
            .workplane(offset=h)
            .circle(r_out_top)
            .loft(combine=True)
        )
    bore_z = base_h if base_closed else -1.0
    bore_h = (h - base_h) + 2.0 if base_closed else h + 2.0
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, bore_z))
        .circle(r_bore)
        .extrude(bore_h)
    )
    return outer.cut(bore)


def build_sleeve():
    """Straight or tapered sleeve. The outer radius tapers by `taper`/2 from bottom
    to top (narrower at the top), keeping a full wall at the bottom."""
    r_bottom = out_r
    r_top = max(bore_r + wall, out_r - taper / 2.0)
    body = _tube(r_bottom, r_top, bore_r, height, base, base_th)
    # Soften the top rim for lip comfort; non-fatal.
    try:
        body = body.edges(">Z").fillet(min(wall * 0.3, 1.0))
    except Exception:
        pass
    return body


def build_adapter():
    """Steps a small vessel up to a larger holder: a cylindrical body whose bore
    matches the vessel and whose outside matches the holder, with an optional base
    that closes the bottom so the vessel rests on it. Straight outside (a true
    diameter-stepping adapter), independent of `taper`."""
    body = _tube(out_r, out_r, bore_r, height, base, base_th)
    # A short lead-in chamfer at the top of the bore eases insertion.
    try:
        body = body.edges(">Z").fillet(min(wall * 0.3, 1.0))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "adapter":
    result = build_adapter()
else:
    result = build_sleeve()
