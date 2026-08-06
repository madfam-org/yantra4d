"""
Gauge Pod — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Mounts a round aftermarket gauge (boost, oil, AFR, voltage…) in the cabin. The
gauge drops into a standard 52 mm or 60 mm bore; three mounting styles put that
bore where you want it:

  * "vent_pod"    — a body that clips into an air-vent with two sprung tabs.
  * "pillar_pod"  — an A-pillar pod whose gauge face is raked toward the driver.
  * "surface_pod" — a low adhesive-mount puck for a dash or console surface.

The 52/60 mm gauge bore is the Common Denominator Geometry — every pod presents
the identical socket so any standard gauge seats in any mounting style.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `gauge_dia`).
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


# ── Gauge standard table ─────────────────────────────────────────────────────
# The two ubiquitous aftermarket gauge sizes. `bore` is the socket diameter
# (nominal + a printable seating clearance); `depth` is a typical gauge body
# depth the pod cups.
GAUGE_TABLE = {
    "52mm": {"bore": 52.5, "depth": 30.0},
    "60mm": {"bore": 60.5, "depth": 32.0},
}


def gauge_spec(key):
    """Look up a gauge size, tolerant of ints/floats and stray spacing."""
    k = str(key).strip().lower().replace(" ", "")
    if k in ("52", "52.0", "52mm"):
        k = "52mm"
    elif k in ("60", "60.0", "60mm"):
        k = "60mm"
    return GAUGE_TABLE.get(k, GAUGE_TABLE["52mm"])


# ── Parameters ───────────────────────────────────────────────────────────────
gauge_dia    = str(  PARAM(lambda: gauge_dia,   "52mm"))  # "52mm" | "60mm"
wall         = float(PARAM(lambda: wall,          3.0))   # pod wall thickness
face_ring    = float(PARAM(lambda: face_ring,     4.0))   # front bezel ring width
back_depth   = float(PARAM(lambda: back_depth,   34.0))   # overall cup depth for the gauge

rake_deg     = float(PARAM(lambda: rake_deg,     22.0))   # pillar_pod face rake toward driver
pillar_h     = float(PARAM(lambda: pillar_h,     70.0))   # pillar_pod body height

vent_tab_w   = float(PARAM(lambda: vent_tab_w,   18.0))   # vent clip tab width
vent_tab_len = float(PARAM(lambda: vent_tab_len, 26.0))   # vent clip tab reach

base_pad     = float(PARAM(lambda: base_pad,     10.0))   # surface_pod adhesive flange width

target_part  = str(  PARAM(lambda: target_part, "vent_pod"))
# "vent_pod" | "pillar_pod" | "surface_pod"


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = gauge_spec(gauge_dia)
bore_r = spec["bore"] / 2.0
wall = max(1.6, wall)
face_ring = max(1.5, min(face_ring, bore_r - 2.0))
back_depth = max(spec["depth"] * 0.6, back_depth)
outer_r = bore_r + wall


# ── Shared helper: gauge cup (round socket body with retaining bezel) ─────────
def gauge_cup(depth):
    """A round cup that holds the gauge: outer cylinder (radius outer_r) of the
    given depth, hollowed to the gauge bore from the FRONT (+Z) but stopping on a
    thin floor. A front bezel lip (width `face_ring`) narrows the top opening so
    the gauge face is captured. Watertight solid."""
    outer = (
        cq.Workplane("XY")
        .circle(outer_r)
        .extrude(depth)
    )
    # Main gauge bore: open at the top, floored at z=wall.
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall))
        .circle(bore_r)
        .extrude(depth)  # overshoots the top → clean open socket
    )
    cup = outer.cut(bore)

    # Bezel lip: re-add a thin ring at the very front that reaches inward by
    # `face_ring`, capturing the gauge face. Built as a ring solid unioned back.
    lip_r = max(1.0, bore_r - face_ring)
    lip_h = min(3.0, depth * 0.15)
    lip_ring_outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, depth - lip_h))
        .circle(bore_r)
        .extrude(lip_h)
    )
    lip_ring_inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, depth - lip_h - 0.5))
        .circle(lip_r)
        .extrude(lip_h + 1.0)
    )
    cup = cup.union(lip_ring_outer.cut(lip_ring_inner))
    return cup


# ── vent_pod ──────────────────────────────────────────────────────────────────
def build_vent_pod():
    """Gauge cup with two sprung clip tabs on the back to grab an air-vent."""
    cup = gauge_cup(back_depth)

    # Two tabs extend rearward (−Y) from the cup at ±X, each with a barb bump so
    # they compress into a vent slot. Modelled as solid fins (watertight).
    body = cup
    for sign in (-1.0, 1.0):
        base_x = sign * (outer_r - wall * 0.5)
        tab = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(base_x, -outer_r + 1.0, back_depth * 0.35))
            .box(max(2.0, wall * 0.8), vent_tab_len, vent_tab_w,
                 centered=(True, False, True))
        )
        barb = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(base_x + sign * wall * 0.6,
                                          -outer_r + 1.0 - vent_tab_len * 0.7,
                                          back_depth * 0.35))
            .box(wall * 1.2, 4.0, vent_tab_w * 0.7, centered=(True, True, True))
        )
        body = body.union(tab.union(barb))
    return body


# ── pillar_pod ────────────────────────────────────────────────────────────────
def build_pillar_pod():
    """A tall pod for the A-pillar: a raked mounting body with the gauge cup
    tilted toward the driver by `rake_deg`."""
    spine_w = outer_r * 1.4
    spine = (
        cq.Workplane("XY")
        .box(spine_w, wall * 4.0, pillar_h, centered=(True, True, False))
    )
    try:
        spine = spine.edges("|Z").fillet(min(6.0, spine_w / 2.0 - 1.0))
    except Exception:
        pass

    # Gauge cup, tilted about X (degrees) and lifted to the top of the spine.
    cup = gauge_cup(back_depth)
    rake = max(0.0, min(rake_deg, 45.0))
    cup = (
        cup.rotate((0, 0, 0), (1, 0, 0), -rake)
        .translate((0, wall * 2.0, pillar_h - 6.0))
    )
    return spine.union(cup)


# ── surface_pod ───────────────────────────────────────────────────────────────
def build_surface_pod():
    """A low adhesive-mount puck: the gauge cup on a wide flat flange for a dash
    or console surface."""
    cup = gauge_cup(back_depth)
    flange = (
        cq.Workplane("XY")
        .circle(outer_r + max(4.0, base_pad))
        .extrude(wall)
    )
    try:
        flange = flange.edges(">Z").fillet(min(2.0, wall * 0.5))
    except Exception:
        pass
    return flange.union(cup)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pillar_pod":
    result = build_pillar_pod()
elif target_part == "surface_pod":
    result = build_surface_pod()
else:  # "vent_pod"
    result = build_vent_pod()
