"""
Phone / Tablet Stand — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An angled desk stand that cradles a phone or tablet in a slot tilted to a
comfortable viewing angle, with a front lip that catches the device and a cable
slot at the bottom so it can charge while docked. Three modes (dispatched by
`target_part`):

  * "stand"      — a one-piece wedge / easel: a solid triangular prism with a
                   tilted device slot and a catch lip.
  * "adjustable" — a two-part set: a base with several angle notches plus a
                   separate prop leg that seats in whichever notch you choose.
  * "dock"       — a stand with a routed cable channel from the back through to
                   the device slot, plus a raised back support wall.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `device_t`).
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
device_t    = float(PARAM(lambda: device_t,    11.0))   # device thickness = slot width (mm)
angle       = float(PARAM(lambda: angle,        60.0))   # view angle from horizontal (deg)
width       = float(PARAM(lambda: width,       100.0))   # stand width across the device (mm)
lip_h       = float(PARAM(lambda: lip_h,        12.0))   # front catch-lip height (mm)
depth       = float(PARAM(lambda: depth,        75.0))   # base depth (front-to-back, mm)
height      = float(PARAM(lambda: height,       70.0))   # overall stand height (mm)
wall        = float(PARAM(lambda: wall,          4.0))   # slot / body wall thickness (mm)
cable_slot  = bool( PARAM(lambda: cable_slot,   True))   # cable slot at the bottom of the rest
cable_w     = float(PARAM(lambda: cable_w,      16.0))   # cable slot width (mm)

target_part = str(  PARAM(lambda: target_part, "stand"))  # stand | adjustable | dock

# ── Clamps / derived values ──────────────────────────────────────────────────
angle   = max(35.0, min(angle, 80.0))          # keep a sane, printable lean
device_t = max(3.0, min(device_t, 40.0))
width   = max(40.0, width)
wall    = max(2.5, min(wall, 10.0))
lip_h   = max(4.0, min(lip_h, device_t * 3.0 + 20.0))
depth   = max(40.0, depth)
height  = max(35.0, height)
cable_w = max(6.0, min(cable_w, width - 2.0 * wall))

ang = math.radians(angle)
# Horizontal run of the incline for the given height (how far back the top leans).
run = height / max(math.tan(ang), 0.30)


# ── Helpers ──────────────────────────────────────────────────────────────────
def wedge_prism(w, run_x, h, extra_base):
    """A right-triangle prism extruded across width `w` (along Y).

    Cross-section in the XZ plane: a base of length (run_x + extra_base) at z=0,
    rising to a vertical back edge of height `h`. The hypotenuse is the resting
    face that leans back at `angle`. Returns a solid Workplane, base at z=0,
    centred in Y."""
    base_len = run_x + extra_base
    pts = [
        (0.0, 0.0),
        (base_len, 0.0),
        (extra_base, h),   # top of the back edge, offset so the back is vertical
        (0.0, h),
    ]
    return (
        cq.Workplane("XZ")
        .polyline(pts)
        .close()
        .extrude(w)
        .translate((0, w / 2.0, 0))  # centre across Y (extrude went -Y)
    )


def rest_slot_cutter(w, slot_w, over=60.0):
    """A tilted rectangular channel that the device sits in, cut into the
    resting face. `slot_w` is the device thickness. Long enough to pass fully
    through the body (`over`)."""
    slot = (
        cq.Workplane("XZ")
        .rect(slot_w, over, centered=(True, False))
        .extrude(w + 20.0)
        .translate((0, (w + 20.0) / 2.0, 0))
    )
    # Rotate about Y so the channel leans at the viewing angle, then slide the
    # slot onto the resting face near the front lip.
    slot = slot.rotate((0, 0, 0), (0, 1, 0), -(90.0 - angle))
    return slot


def build_stand():
    """One-piece easel wedge with a tilted device slot and a front catch lip."""
    body = wedge_prism(width, run, height, wall + device_t + 6.0)

    # Device slot: a channel of width `device_t` set back from the front edge,
    # tilted to the viewing angle. Position it so a `wall`-thick lip remains in
    # front of it to catch the device.
    slot_x = wall + device_t / 2.0
    slot = rest_slot_cutter(width, device_t)
    # place the (centred-at-origin) tilted slot so its front wall sits at slot_x
    slot = slot.translate((slot_x + device_t, 0, -2.0))
    body = body.cut(slot)

    # Trim the catch lip down to `lip_h` so tall devices clear it visually and
    # the front is not a full-height wall.
    if lip_h < height:
        clip = (
            cq.Workplane("XY")
            .box(device_t + 2.0 * wall + 4.0, width + 4.0, height,
                 centered=(True, True, False))
            .translate((wall + device_t / 2.0, 0, lip_h))
        )
        body = body.cut(clip)

    # Cable slot: a notch through the base directly under the device rest.
    if cable_slot:
        body = body.cut(_cable_cutter(slot_x))

    body = _soften(body)
    return body


def _cable_cutter(slot_x):
    """A slot cut up through the base under the device rest so a charging cable
    can drop straight down behind the phone."""
    return (
        cq.Workplane("XY")
        .box(device_t + 4.0, cable_w, wall * 3.0 + 4.0,
             centered=(True, True, False))
        .translate((slot_x + 2.0, 0, -2.0))
    )


def build_adjustable():
    """Two-part set rendered together: a base tray with a stepped ramp of angle
    notches, plus a separate prop leg placed beside it. The leg's foot seats in
    any notch to change the lean."""
    base_len = depth
    base_h = max(10.0, wall * 2.0 + 4.0)

    # Base slab with a shallow device tray (a lip at the front to stop sliding).
    base = (
        cq.Workplane("XY")
        .box(base_len, width, base_h, centered=(True, True, False))
    )
    # Front lip on the base tray.
    lip = (
        cq.Workplane("XY")
        .box(wall, width, base_h + lip_h, centered=(True, True, False))
        .translate((-base_len / 2.0 + wall / 2.0, 0, 0))
    )
    base = base.union(lip)

    # A row of notch grooves along the base top that the prop leg foot drops
    # into — each groove a step further back = a steeper or shallower lean.
    n_notches = 4
    groove_w = 6.0
    start_x = -base_len / 2.0 + 22.0
    for i in range(n_notches):
        gx = start_x + i * ((base_len - 34.0) / max(1, n_notches - 1))
        groove = (
            cq.Workplane("XY")
            .box(groove_w, width - 2.0 * wall, 3.5, centered=(True, True, False))
            .translate((gx, 0, base_h - 3.5))
        )
        base = base.cut(groove)

    # Prop leg: a flat plate with a device slot near the top and a foot tab that
    # fits the grooves. Rendered standing at the default angle, off to +X so it
    # reads as a distinct second part.
    leg_h = height
    leg = (
        cq.Workplane("XZ")
        .rect(wall * 2.5, leg_h, centered=(True, False))
        .extrude(width)
        .translate((0, width / 2.0, 0))
    )
    # Device slot near the top of the leg (a shallow tilted pocket).
    slot = (
        cq.Workplane("XZ")
        .rect(device_t, device_t + 6.0, centered=True)
        .extrude(width + 20.0)
        .translate((0, (width + 20.0) / 2.0, leg_h - device_t))
    )
    leg = leg.cut(slot)
    # Foot tab under the leg that seats in a groove.
    foot = (
        cq.Workplane("XY")
        .box(groove_w - 0.6, width - 2.0 * wall - 0.6, 3.2,
             centered=(True, True, False))
        .translate((0, 0, -3.2))
    )
    leg = leg.union(foot)
    leg = leg.translate((base_len / 2.0 + 22.0, 0, base_h))

    body = base.union(leg)
    body = _soften(body)
    return body


def build_dock():
    """Wedge stand with a routed cable channel from the back to the device slot
    and a raised back support wall behind the device."""
    body = wedge_prism(width, run, height, wall + device_t + 10.0)

    slot_x = wall + device_t / 2.0
    slot = rest_slot_cutter(width, device_t)
    slot = slot.translate((slot_x + device_t, 0, -2.0))
    body = body.cut(slot)

    # Trim front lip to lip_h.
    if lip_h < height:
        clip = (
            cq.Workplane("XY")
            .box(device_t + 2.0 * wall + 4.0, width + 4.0, height,
                 centered=(True, True, False))
            .translate((slot_x, 0, lip_h))
        )
        body = body.cut(clip)

    # Raised back support: a low wall behind the device rest so a docked device
    # leans against it. Realised as a small block near the tall back edge.
    back_x = wall + device_t + 6.0 + run * 0.35
    support = (
        cq.Workplane("XY")
        .box(wall * 1.8, width * 0.55, height * 0.45, centered=(True, True, False))
        .translate((back_x, 0, height * 0.30))
    )
    body = body.union(support)

    # Cable channel: an L-shaped route. A horizontal bore enters the back of the
    # base and turns up to exit under the device slot.
    horiz = (
        cq.Workplane("XY")
        .box(depth, cable_w, cable_w, centered=(True, True, False))
        .translate((0, 0, wall + cable_w / 2.0))
    )
    vert = (
        cq.Workplane("XY")
        .box(cable_w, cable_w, height, centered=(True, True, False))
        .translate((slot_x + 2.0, 0, 0))
    )
    body = body.cut(horiz)
    body = body.cut(vert)

    body = _soften(body)
    return body


def _soften(body):
    """Round exposed vertical edges a touch for comfort; non-fatal on failure."""
    r = min(1.2, wall * 0.3)
    try:
        body = body.edges("|Z").fillet(r)
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "adjustable":
    result = build_adjustable()
elif target_part == "dock":
    result = build_dock()
else:
    result = build_stand()
