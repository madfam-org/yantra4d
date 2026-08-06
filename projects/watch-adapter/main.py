"""
Watch Band Adapters & Stands — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Watch-lug hardware sized to the standard 18 / 20 / 22 mm lug widths, all built
around one lug interface: a pair of ears spanning the lug gap with spring-bar
(quick-release) pin bores. A lug-to-strap adapter, a watch display stand, and a
charger dock. Every part is one watertight solid built by cutting the pin bores
and cavities from a body.

The quick-release spring-bar is represented dimensionally: the ear gap equals the
lug width and each ear carries a blind pin bore of `pin_dia` at the standard
spring-bar seat, so a real 1.5-1.8 mm spring bar / quick-release bar drops in. No
moving spring is printed (that is a metal bar); the geometry is the correct
mating envelope.

Modes (dispatched via `target_part`):
  * "band_adapter" — a lug adapter: two lug ears with pin bores on one side and a
                     strap slot on the other (lug -> 2-piece strap / paracord).
  * "watch_stand"  — an angled cradle stand a watch head rests in, lugs down.
  * "charger_dock" — a puck dock with a recessed well for a round charger and lug
                     ears so the watch clips in face-up while charging.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `lug_width`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
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
lug_width   = str(  PARAM(lambda: lug_width, "20mm"))   # "18mm"|"20mm"|"22mm"
pin_dia     = float(PARAM(lambda: pin_dia,     1.6))    # spring-bar pin diameter (mm)
strap_t     = float(PARAM(lambda: strap_t,     3.0))    # strap thickness for the adapter (mm)
wall        = float(PARAM(lambda: wall,        3.0))    # wall thickness (mm)
ear_h       = float(PARAM(lambda: ear_h,       8.0))    # lug ear height (mm)
stand_angle = float(PARAM(lambda: stand_angle, 55.0))   # watch-stand cradle angle (deg)
watch_dia   = float(PARAM(lambda: watch_dia,  44.0))    # watch head diameter for stand/dock (mm)

target_part = str(  PARAM(lambda: target_part, "band_adapter"))  # band_adapter|watch_stand|charger_dock

# ── Lug widths ────────────────────────────────────────────────────────────────
_LUG = {"18mm": 18.0, "20mm": 20.0, "22mm": 22.0}
lug_w = _LUG.get(lug_width, 20.0)

# ── Safe clamps ──────────────────────────────────────────────────────────────
pin_dia     = max(1.0, min(pin_dia, 2.5))
strap_t     = max(1.5, min(strap_t, 6.0))
wall        = max(2.0, min(wall, 6.0))
ear_h       = max(5.0, min(ear_h, 16.0))
stand_angle = max(30.0, min(stand_angle, 75.0))
watch_dia   = max(30.0, min(watch_dia, 60.0))


# ── Shared lug-ear helper (the Watch Lug CDG) ─────────────────────────────────
def lug_ears(gap, ear_t, height, base_th):
    """Two lug ears straddling a `gap` (== lug width), each carrying a blind
    spring-bar pin bore near the top. Returns a cq.Workplane centred in X/Y with
    its base at z=0; the ears rise in +Z, the gap opens along X between them, and
    the pin axis runs along X (through both ears). `base_th` is a connecting web
    below the gap so the two ears share one solid. Shared across all parts so the
    watch always clips to the same lug interface."""
    span = gap + 2.0 * ear_t
    # Base web bridging the two ears.
    base = cq.Workplane("XY").box(span, height, base_th, centered=(True, True, False))
    body = base
    for sx in (-1.0, 1.0):
        ear = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * (gap + ear_t) / 2.0, 0, 0))
            .box(ear_t, height, base_th + height, centered=(True, True, False))
        )
        try:
            ear = ear.edges("|Y").fillet(min(ear_t * 0.4, 1.5))
        except Exception:
            pass
        body = body.union(ear)
    # Pin bores: one blind bore into each ear from the gap side, on the pin axis.
    pin_z = base_th + height * 0.6
    bore_r = pin_dia / 2.0 + 0.2
    for sx in (-1.0, 1.0):
        bore = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, pin_z, sx * (gap / 2.0 + ear_t / 2.0)))
            .cylinder(ear_t + 0.4, bore_r)
        )
        body = body.cut(bore)
    return body, span, base_th + height


def rounded_block(w, d, h, r):
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


def strap_slot(width, thickness, length, clearance):
    """A rounded slot sized to a watch strap: width along Y, thickness along Z,
    through-length along X. Used by the band adapter."""
    w = width + clearance
    t = thickness + clearance
    r = min(t / 2.0 - 0.01, 0.8)
    slot = cq.Workplane("XY").box(length, w, t, centered=(True, True, True))
    if r > 0.05:
        try:
            slot = slot.edges("|X").fillet(r)
        except Exception:
            pass
    return slot


# ── Part builders ─────────────────────────────────────────────────────────────
def build_band_adapter():
    """A lug-to-strap adapter: the lug ears on one end (clip to the watch) and a
    strap slot on the other end (thread a 2-piece strap / paracord). One
    watertight solid."""
    ears, span, top = lug_ears(lug_w, wall, ear_h, wall * 1.2)

    # Body block below/behind the ears carrying the strap slot.
    body_d = wall * 1.2 + strap_t + 2.0 * wall
    body = rounded_block(span, body_d, wall * 1.2, min(wall, 2.0))
    # Move body so it extends in +Y (away from the ear span centre).
    body = body.translate((0, -ear_h / 2.0 - body_d / 2.0, 0))

    # Strap slot through the far end of the body (strap runs along X).
    slot = strap_slot(lug_w, strap_t, span + 4.0, 0.6)
    slot = slot.translate((0, -ear_h / 2.0 - body_d + strap_t, wall * 0.6))
    body = body.cut(slot)

    result_body = ears.union(body)
    return result_body


def build_watch_stand():
    """An angled cradle stand: a wedge foot with a curved cradle the watch head
    rests in (lugs hanging down the front), plus a lug-ear detail so a strap can
    be draped. One watertight solid."""
    base_w = watch_dia + 2.0 * wall + 10.0
    base_d = watch_dia * 1.1
    base_h = wall * 2.0
    base = rounded_block(base_w, base_d, base_h, min(base_w * 0.12, 6.0))

    # Angled back support (a wedge) that the watch leans against.
    ang = math.radians(stand_angle)
    back_h = watch_dia * 0.9
    back_t = wall * 2.0
    # Build the wedge as a triangular prism in YZ extruded along X.
    run = back_h / max(math.tan(ang), 0.3)
    pts = [
        (-base_d / 2.0, base_h),
        (-base_d / 2.0 + run + back_t, base_h),
        (-base_d / 2.0 + run, base_h + back_h),
        (-base_d / 2.0, base_h + back_h * 0.15),
    ]
    wedge = (
        cq.Workplane("YZ")
        .polyline(pts)
        .close()
        .extrude(base_w * 0.8)
        .translate((base_w * 0.4, 0, 0))
    )
    body = base.union(wedge)

    # A front lip so the watch does not slide off.
    lip = rounded_block(base_w * 0.8, wall * 1.5, back_h * 0.16 + base_h, min(wall, 2.0))
    lip = lip.translate((0, base_d / 2.0 - wall * 1.5, 0))
    body = body.union(lip)

    # A cradle groove across the wedge face where the watch head sits.
    groove = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -base_d / 2.0 + run * 0.6, base_h + back_h * 0.45))
        .cylinder(base_w * 0.85, watch_dia * 0.5)
    )
    groove = groove.rotate((0, 0, 0), (0, 1, 0), 90)
    body = body.cut(groove)
    return body


def build_charger_dock():
    """A charger dock puck: a round base with a recessed well for a circular
    watch charger and lug ears rising at the back so the watch clips in and rests
    face-up while charging. One watertight solid."""
    puck_r = watch_dia * 0.62 + wall
    puck_h = wall * 3.0
    puck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, puck_h / 2.0))
        .cylinder(puck_h, puck_r)
    )

    # Charger well: a top recess for the round charger (assume ~ watch_dia*0.62).
    well_r = watch_dia * 0.5
    well_d = puck_h * 0.6
    well = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, puck_h - well_d))
        .cylinder(well_d + 1.0, well_r)
    )
    body = puck.cut(well)

    # Cable exit channel from the well out the side.
    cable = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -puck_r, puck_h - well_d * 0.5))
        .box(4.0, 2.0 * puck_r, max(4.0, pin_dia + 2.0), centered=(True, False, True))
    )
    body = body.cut(cable)

    # Lug ears at the back edge so the watch head clips in face-up.
    ears, span, top = lug_ears(lug_w, wall, ear_h, wall)
    ears = ears.translate((0, puck_r - wall * 0.5, puck_h))
    body = body.union(ears)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "watch_stand":
    result = build_watch_stand()
elif target_part == "charger_dock":
    result = build_charger_dock()
else:
    result = build_band_adapter()
