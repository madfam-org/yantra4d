"""
Laptop / Monitor Riser — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A riser that lifts a laptop or monitor to eye / airflow height on two side
panels or four corner posts, with a cable pass-through at the back and space
underneath to slide a keyboard. Three modes (dispatched by `target_part`):

  * "riser"        — a flat top platform on legs (the general desk riser).
  * "monitor_stand"— taller and on a narrower, deeper-set base for a monitor.
  * "laptop_stand" — a top platform tilted for typing, with ventilation slots
                     cut through it for laptop airflow.

Leg style is selectable: two solid side panels or four corner posts.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `plat_w`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


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
height      = float(PARAM(lambda: height,      95.0))    # clearance under the platform (mm)
plat_w      = float(PARAM(lambda: plat_w,     260.0))    # top platform width (mm)
plat_d      = float(PARAM(lambda: plat_d,     240.0))    # top platform depth (mm)
plat_t      = float(PARAM(lambda: plat_t,       6.0))    # platform thickness (mm)
leg_t       = float(PARAM(lambda: leg_t,        6.0))    # leg / panel thickness (mm)
leg_style   = str(  PARAM(lambda: leg_style, "solid_sides"))  # solid_sides | posts
cable_slot  = bool( PARAM(lambda: cable_slot,  True))    # cable pass-through at the back
cable_w     = float(PARAM(lambda: cable_w,     60.0))    # cable slot width (mm)
vents       = bool( PARAM(lambda: vents,       True))    # ventilation slots in the top
kbd_slot    = bool( PARAM(lambda: kbd_slot,    True))    # keep the underside open for a keyboard
tilt        = float(PARAM(lambda: tilt,         6.0))    # laptop-stand top tilt (deg)

target_part = str(  PARAM(lambda: target_part, "riser"))  # riser | monitor_stand | laptop_stand

# ── Clamps / mode-driven proportions ─────────────────────────────────────────
plat_t = max(3.0, min(plat_t, 20.0))
leg_t  = max(3.0, min(leg_t, 20.0))
height = max(30.0, min(height, 250.0))
plat_w = max(80.0, plat_w)
plat_d = max(80.0, plat_d)
cable_w = max(10.0, min(cable_w, plat_w - 4.0 * leg_t))
tilt   = max(0.0, min(tilt, 15.0))
if leg_style not in ("solid_sides", "posts"):
    leg_style = "solid_sides"

# Monitor stand: taller, narrower footprint (legs pulled inboard) for a monitor
# base that sits behind the keyboard.
if target_part == "monitor_stand":
    height = max(height, 110.0)


# ── Helpers ──────────────────────────────────────────────────────────────────
def platform(w, d, t):
    """Flat top plate, centred in X/Y, base at z=0."""
    return cq.Workplane("XY").box(w, d, t, centered=(True, True, False))


def side_panels(w, d, h, inset):
    """Two full side panels (left & right), each a slab in the YZ direction,
    standing from z=0 to z=h. `inset` pulls them in from the platform edge."""
    x = w / 2.0 - inset - leg_t / 2.0
    panel = cq.Workplane("XY").box(leg_t, d, h, centered=(True, True, False))
    left = panel.translate((-x, 0, 0))
    right = panel.translate((x, 0, 0))
    return left.union(right)


def corner_posts(w, d, h, inset, post):
    """Four square corner posts from z=0 to z=h."""
    dx = w / 2.0 - inset - post / 2.0
    dy = d / 2.0 - inset - post / 2.0
    pts = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]
    legs = None
    for (px, py) in pts:
        leg = (
            cq.Workplane("XY")
            .box(post, post, h, centered=(True, True, False))
            .translate((px, py, 0))
        )
        legs = leg if legs is None else legs.union(leg)
    return legs


def make_legs(w, d, h, inset):
    """Legs per the selected style; top at z=h."""
    if leg_style == "posts":
        post = max(leg_t * 2.5, 12.0)
        return corner_posts(w, d, h, inset, post)
    return side_panels(w, d, h, inset)


def cable_cutter(w, d, at_z):
    """A slot cut into the BACK edge of the platform for cable pass-through."""
    return (
        cq.Workplane("XY")
        .box(cable_w, leg_t * 3.0 + 6.0, plat_t + 4.0, centered=(True, True, False))
        .translate((0, d / 2.0, at_z - 2.0))
    )


def vent_cutter(w, d, at_z):
    """A row of long ventilation slots through the platform (airflow for a
    laptop sitting on top). Cut all the way through the plate."""
    slots = None
    n = 5
    slot_w = max(6.0, w * 0.045)
    span = w * 0.6
    step = span / (n - 1)
    slot_len = d * 0.45
    for i in range(n):
        sx = -span / 2.0 + i * step
        s = (
            cq.Workplane("XY")
            .box(slot_w, slot_len, plat_t + 4.0, centered=(True, True, False))
            .translate((sx, -d * 0.05, at_z - 2.0))
        )
        slots = s if slots is None else slots.union(s)
    return slots


def soften(body):
    r = min(2.0, leg_t * 0.3)
    try:
        body = body.edges("|Z").fillet(r)
    except Exception:
        pass
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_riser(w, d, h, inset, add_vents=False, top_tilt=0.0):
    """Generic platform-on-legs builder shared by all three modes."""
    legs = make_legs(w, d, h, inset)

    if top_tilt > 0.05:
        # A wedge top whose upper face slopes down toward the front (typing tilt).
        top = _tilt_top(w, d, h, add_vents, top_tilt)
    else:
        top = platform(w, d, plat_t).translate((0, 0, h))
        if cable_slot:
            top = top.cut(cable_cutter(w, d, h))
        if add_vents and vents:
            top = top.cut(vent_cutter(w, d, h))

    body = legs.union(top)

    # When kbd_slot is off on solid sides, close the underside with a back rail
    # so it is a cubby; when on, leave the underside open for a keyboard.
    if (not kbd_slot) and leg_style == "solid_sides":
        rail = (
            cq.Workplane("XY")
            .box(w - 2.0 * inset, leg_t, h * 0.5, centered=(True, True, False))
            .translate((0, d / 2.0 - inset - leg_t / 2.0, 0))
        )
        body = body.union(rail)

    return soften(body)


def _tilt_top(w, d, h, add_vents, tilt_deg):
    """Build the top plate as a wedge so its upper face slopes down toward the
    front by `tilt_deg` degrees (a typing angle), then apply cuts. Watertight by
    construction (a solid extruded profile)."""
    rise = d * math.tan(math.radians(tilt_deg))
    # Side profile in the XZ-equivalent (Y depth, Z height): thicker at the back.
    pts = [
        (-d / 2.0, 0.0),
        (d / 2.0, 0.0),
        (d / 2.0, plat_t),
        (-d / 2.0, plat_t + rise),
    ]
    wedge = (
        cq.Workplane("YZ")
        .polyline(pts)
        .close()
        .extrude(w)
        .translate((-w / 2.0, 0, h))  # extrude runs 0→w in +X; recentre on X=0
    )
    if cable_slot:
        wedge = wedge.cut(cable_cutter(w, d, h))
    if add_vents and vents:
        wedge = wedge.cut(vent_cutter(w, d, h))
    return wedge


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "monitor_stand":
    # Narrower, deeper-set legs; taller clearance for a monitor base.
    result = build_riser(plat_w * 0.85, plat_d, height, inset=plat_w * 0.10)
elif target_part == "laptop_stand":
    # Tilted top with ventilation for a laptop.
    result = build_riser(plat_w, plat_d, height, inset=leg_t + 2.0,
                         add_vents=True, top_tilt=max(tilt, 4.0))
else:
    result = build_riser(plat_w, plat_d, height, inset=leg_t + 2.0)
