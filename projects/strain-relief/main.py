"""
Strain Relief — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Strain reliefs and bend limiters for cable exits: they clamp the cable and spread the
bend load where a cable leaves a plug, enclosure, or panel, so the conductors don't
fatigue and snap. Sized by cable diameter and a panel/mount interface.

Three parts (dispatched via `target_part`):
  * "grommet_relief" — a snap-in panel grommet: a bushing with a rear flange and a snap
                       ridge that trap a panel, plus a strain-rib cable bore that grips.
  * "clamp_relief"   — a two-screw saddle clamp that pinches the cable against a mount
                       foot (the classic cordgrip / P-clamp).
  * "bend_limiter"   — a flexible ribbed sleeve (a tapering stack of rib rings around the
                       cable bore) that limits the minimum bend radius at the exit.

The cable BORE + snap flange is the shared CDG. Bodies are prismatic / annular / lofted —
fast and watertight (the ribbed sleeve is a loft of stepped circles, not a boolean stack).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cable_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "grommet_relief"))  # grommet_relief|clamp_relief|bend_limiter

cable_dia  = float(PARAM(lambda: cable_dia,   8.0))   # cable outer diameter (mm)
grip       = float(PARAM(lambda: grip,        0.6))   # bore undersize per side (soft grip) (mm)
panel_t    = float(PARAM(lambda: panel_t,     3.0))   # panel thickness the grommet snaps into (mm)
panel_hole = float(PARAM(lambda: panel_hole, 16.0))   # panel hole diameter (mm)
wall       = float(PARAM(lambda: wall,        3.0))   # body wall thickness (mm)
bolt_dia   = float(PARAM(lambda: bolt_dia,    4.0))   # clamp screw clearance dia (mm)
bend_r     = float(PARAM(lambda: bend_r,     28.0))   # min bend radius the limiter enforces (mm)
segments   = int(  PARAM(lambda: segments,     7))    # bend-limiter rib count

# Clamp inputs to sane ranges so extreme UI values still build watertight.
cable_dia  = max(2.0, min(cable_dia, 30.0))
grip       = max(0.0, min(grip, 1.5))
panel_t    = max(1.0, min(panel_t, 8.0))
panel_hole = max(cable_dia + 4.0, min(panel_hole, 40.0))
wall       = max(2.0, min(wall, 8.0))
bolt_dia   = max(2.5, min(bolt_dia, 8.0))
bend_r     = max(10.0, min(bend_r, 80.0))
segments   = max(3, min(segments, 14))

bore_r = max(0.8, cable_dia / 2.0 - grip)      # gripping bore radius


# ── Shared: an annular tube (fast, watertight, no boolean between two solids) ─
def _tube(o_r, i_r, h, z0=0.0, n=64):
    """An annular tube (outer o_r, inner i_r, height h) built from a single annular
    cross-section extrude — no cut between two solids."""
    o = [(o_r * math.cos(2.0 * math.pi * k / n), o_r * math.sin(2.0 * math.pi * k / n)) for k in range(n)]
    i = [(i_r * math.cos(2.0 * math.pi * k / n), i_r * math.sin(2.0 * math.pi * k / n)) for k in range(n)]
    return (
        cq.Workplane("XY").polyline(o).close().polyline(i).close()
        .extrude(h).translate((0, 0, z0))
    )


# ── Grommet relief (snap-in panel bushing) ───────────────────────────────────
def build_grommet_relief():
    """A snap-in bushing: an outer barrel sized to the panel hole with a rear flange and a
    snap ridge that trap the panel between them, and a strain-rib cable bore that grips
    the jacket. The snap ridge sits one panel-thickness past the flange so it clicks in."""
    body_or = panel_hole / 2.0 - 0.2         # slides into the panel hole
    total_h = panel_t + wall * 2.0 + 6.0
    body = _tube(body_or, bore_r, total_h)
    # Rear flange (bigger than the hole) stops it going through.
    body = body.union(_tube(body_or + wall + 2.0, bore_r, wall, z0=0.0))
    # Snap ridge: a raised ring at (flange + panel_t) so the panel is trapped.
    body = body.union(_tube(body_or + 1.4, body_or - 0.2, 2.2, z0=wall + panel_t))
    # Strain ribs: two internal narrowing rings that pinch the cable jacket.
    for zoff in (total_h - 6.0, total_h - 3.0):
        body = body.union(_tube(bore_r + 1.6, max(0.6, bore_r - 0.4), 1.4, z0=zoff))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Clamp relief (two-screw saddle) ──────────────────────────────────────────
def build_clamp_relief():
    """A saddle clamp: a foot plate with two bolt holes and a saddle block with a grooved
    cable channel and strain ribs that bite the jacket (the classic cordgrip)."""
    body_l = cable_dia + 4.0 * wall + 2.0 * bolt_dia + 12.0
    body_w = cable_dia + 2.0 * wall
    block_h = cable_dia / 2.0 + wall + 3.0
    foot = cq.Workplane("XY").box(body_l, body_w, wall, centered=(True, True, False))
    saddle = cq.Workplane("XY").box(cable_dia + 2.0 * wall, body_w, block_h, centered=(True, True, False))
    # Cable groove: a half-cylinder channel along X at the top of the saddle.
    groove = (
        cq.Workplane("YZ").circle(bore_r + grip).extrude(body_l + 2.0)
        .translate((-(body_l) / 2.0 - 1.0, 0, block_h))
    )
    body = foot.union(saddle).cut(groove)
    # Strain ribs across the groove (raised rings that bite the jacket).
    for xr in (-cable_dia * 0.3, 0.0, cable_dia * 0.3):
        body = body.union(
            cq.Workplane("YZ").circle(bore_r + grip - 0.8).extrude(1.2)
            .translate((xr - 0.6, 0, block_h))
        )
    # Two bolt holes through the foot flanking the saddle.
    for s in (-1.0, 1.0):
        x = s * (cable_dia / 2.0 + wall + bolt_dia * 0.9)
        body = body.cut(
            cq.Workplane("XY").center(x, 0.0).circle(bolt_dia / 2.0)
            .extrude(block_h + 2.0).translate((0, 0, -1.0))
        )
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Bend limiter (ribbed flexible sleeve) ────────────────────────────────────
def build_bend_limiter():
    """A flexible ribbed sleeve: a tapering stack of rib rings around the cable bore, with
    a mount collar at the base. Each rib is a fat annular tube and each neck a thin one, so
    the sleeve flexes at the necks but bottoms out to enforce a minimum bend radius. Built
    as a UNION of annular tubes (a loft through sharply-alternating radii is far too slow in
    OCC). The rib count is capped so even the densest request stays fast."""
    length = min(bend_r * 1.6, 120.0)
    peak = bore_r + wall + 3.0
    neck = bore_r + wall
    n_r = min(segments, 8)                       # cap for speed (union cost scales with count)
    seg = length / n_r
    body = _tube(peak + wall, bore_r, wall * 1.5, z0=0.0)   # base mount collar
    for i in range(n_r):
        frac = 1.0 - 0.5 * i / max(1, n_r - 1)
        rp = neck + (peak - neck) * frac
        body = body.union(_tube(rp, bore_r, seg * 0.55, z0=i * seg))              # fat rib
        body = body.union(_tube(neck, bore_r, seg * 0.5, z0=i * seg + seg * 0.5))  # thin neck
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "clamp_relief":
    result = build_clamp_relief()
elif target_part == "bend_limiter":
    result = build_bend_limiter()
else:
    result = build_grommet_relief()
