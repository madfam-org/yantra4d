"""
Funnel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A hollow funnel: a wide conical mouth tapering into a narrow spout tube. Built as
a single surface of revolution from a closed cross-section profile, so it exports
watertight by construction. Options: an anti-glug vent tube (lets air escape so
liquid pours smoothly), and a nesting rim so funnels stack.

  * "funnel"    — the standard funnel (target_part == "funnel").
  * "long_neck" — an extended, narrower spout for reaching into bottles.

Watertight strategy: revolve ONE closed half-section (outer wall down, across the
spout end, back up the inner bore) a full 360°. A closed profile revolved fully
yields a manifold solid shell — no boolean of two separate solids, no seams.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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
target_part = str(PARAM(lambda: target_part, "funnel"))  # "funnel" | "long_neck"

top_dia     = float(PARAM(lambda: top_dia,    90.0))   # mouth (inlet) diameter
spout_dia   = float(PARAM(lambda: spout_dia,  12.0))   # spout (outlet) OUTER diameter
total_h     = float(PARAM(lambda: total_h,    85.0))   # overall height (cone + spout)
spout_len   = float(PARAM(lambda: spout_len,  30.0))   # straight spout length
wall        = float(PARAM(lambda: wall,        2.0))   # wall thickness
vent        = bool( PARAM(lambda: vent,      False))   # anti-glug vent tube
nesting_rim = bool( PARAM(lambda: nesting_rim, True))  # top rim so funnels stack

# The long-neck variant just runs with a longer, slimmer spout by default.
if target_part == "long_neck":
    spout_len = max(spout_len, 70.0)
    spout_dia = min(spout_dia, 14.0)
    total_h   = max(total_h, spout_len + 45.0)

# ── Clamps (keep the profile valid & the bore open) ──────────────────────────
top_dia   = max(30.0, min(top_dia, 250.0))
wall      = max(1.2, min(wall, 4.0))
# Spout outer must leave a real bore: outer ≥ 2*wall + 2mm.
spout_dia = max(2.0 * wall + 2.0, min(spout_dia, top_dia * 0.6))
spout_len = max(8.0, min(spout_len, 160.0))
total_h   = max(spout_len + 20.0, min(total_h, 300.0))

cone_h = total_h - spout_len               # height of the tapering cone section
r_top_out = top_dia / 2.0                  # outer mouth radius
r_top_in = r_top_out - wall                # inner mouth radius
r_spt_out = spout_dia / 2.0                # outer spout radius
r_spt_in = r_spt_out - wall                # bore radius
r_spt_in = max(0.8, r_spt_in)              # never collapse the bore

# z=0 at the spout OUTLET (bottom); +z up toward the mouth.
z_out = 0.0                                # spout outlet
z_join = spout_len                         # cone/spout junction
z_mouth = total_h                          # top of the mouth


# ── Profile (a closed half cross-section in the XZ half-plane, r ≥ 0) ─────────
def funnel_profile():
    """Closed polyline of (r, z) points. Traversed: up the OUTER wall, across the
    mouth rim, down the INNER wall, across the spout outlet rim — back to start."""
    pts = [
        (r_spt_out, z_out),      # outer spout, at outlet
        (r_spt_out, z_join),     # outer spout, at cone junction
        (r_top_out, z_mouth),    # up the outer cone to the mouth (outer edge)
        (r_top_in, z_mouth),     # across the mouth rim (to inner edge)
        (r_spt_in, z_join),      # down the inner cone to the bore top
        (r_spt_in, z_out),       # down the inner bore to the outlet
    ]
    return pts


def build_shell():
    """Revolve the closed profile 360° about the Z axis → watertight shell."""
    pts = funnel_profile()
    wp = cq.Workplane("XZ").moveTo(pts[0][0], pts[0][1])
    for p in pts[1:]:
        wp = wp.lineTo(p[0], p[1])
    wp = wp.close()
    # Revolve about the global Z (axis start/dir in XZ workplane coords).
    solid = wp.revolve(360.0, (0, 0, 0), (0, 1, 0))
    return solid


def add_nesting_rim(body):
    """A short outward flange at the mouth so funnels stack / hang on a jar."""
    if not nesting_rim:
        return body
    rim_h = min(4.0, wall * 2.0)
    rim = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_mouth - rim_h))
        .circle(r_top_out + wall)
        .circle(r_top_in)
        .extrude(rim_h)
    )
    return body.union(rim)


def add_vent(body):
    """Anti-glug vent: a thin tube alongside the spout that lets air back in so
    liquid pours without gulping. Modeled as a small hollow tube fused to the
    spout, its bore running the spout length."""
    if not vent:
        return body
    vent_out = max(3.0, wall + 2.0)
    vent_in = max(1.0, vent_out - wall)
    off = r_spt_out + vent_out / 2.0 - 0.4   # nestle against the spout, slight overlap
    tube = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(off, 0, z_out))
        .circle(vent_out / 2.0)
        .circle(vent_in / 2.0)
        .extrude(spout_len + 4.0)
    )
    return body.union(tube)


# ── Build ────────────────────────────────────────────────────────────────────
def build():
    body = build_shell()
    body = add_nesting_rim(body)
    body = add_vent(body)
    return body


result = build()
