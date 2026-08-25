"""
Stud-Mount Bracket Kit — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Wall-stud mounting hardware built to the US framing standard: studs on 16 in
(406.4 mm) centres, fastened with #8/#10 wood or drywall screws (~4.2 / 4.8 mm
shank, ~8 mm head). Every part in this kit shares the same stud-mount plate
interface so it interoperates with the `bike-wall-rack` (which mounts on the
same 16 in stud pitch) and grows the `wall-stud` family.

Three distinct modes (dispatch on target_part):
  - stud_plate  : a flat backing plate spanning ONE or TWO stud bays with
                  countersunk screw holes at the stud pitch plus keyhole
                  hanging slots — the universal wall anchor.
  - stud_shelf  : a gusseted right-angle shelf bracket that screws into a single
                  stud; the triangular web carries the load.
  - stud_hook   : a stout J-hook arm on a stud plate for hanging tools, cables,
                  hoses or bikes off the framing.

Watertight strategy (per the Yantra4D authoring canon):
  - Fillet the clean blank BEFORE cutting any feature (fillet on a feature-laden
    solid crashes OCCT clean()).
  - Keyhole slots are obround (stadium) shapes unioned into a bored circle —
    both cut THROUGH the plate (vent to outside), never trapped.
  - The shelf gusset and the hook arm are unioned into the plate with real
    material overlap so the weld is solid (no tangent seams, no severed bodies).
  - No hollow posts on solid bases (no trapped voids); every cavity vents.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as bare globals.
  - Read every param via PARAM(lambda: <name>, <default>).
  - No cross-file imports; assign the final solid to top-level `result`.
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
target_part = str(PARAM(lambda: target_part, "stud_plate"))
# "stud_plate" | "stud_shelf" | "stud_hook"

stud_pitch = float(PARAM(lambda: stud_pitch, 406.4))   # 16 in US stud spacing
bays = float(PARAM(lambda: bays, 1))                   # stud bays spanned (1 or 2)
plate_h = float(PARAM(lambda: plate_h, 90.0))          # plate height (vertical)
plate_t = float(PARAM(lambda: plate_t, 6.0))           # plate thickness
screw_dia = float(PARAM(lambda: screw_dia, 4.5))       # #8/#10 shank clearance
screw_head = float(PARAM(lambda: screw_head, 9.0))     # countersink head dia
shelf_depth = float(PARAM(lambda: shelf_depth, 120.0))  # shelf projection (Y)
hook_len = float(PARAM(lambda: hook_len, 70.0))        # hook arm length (Y)
hook_dia = float(PARAM(lambda: hook_dia, 20.0))        # hook arm diameter

# Clamp to sane ranges so extreme UI values never crash the kernel.
stud_pitch = max(300.0, min(stud_pitch, 610.0))
bays = 2.0 if bays >= 1.5 else 1.0
plate_h = max(50.0, min(plate_h, 200.0))
plate_t = max(4.0, min(plate_t, 14.0))
screw_dia = max(3.0, min(screw_dia, 8.0))
screw_head = max(screw_dia + 2.0, min(screw_head, 16.0))
shelf_depth = max(50.0, min(shelf_depth, 250.0))
hook_len = max(30.0, min(hook_len, 160.0))
hook_dia = max(10.0, min(hook_dia, 40.0))

_n_studs = int(bays) + 1                       # studs the plate reaches
_margin = max(18.0, screw_head * 1.6)          # edge margin around end holes
_plate_w = stud_pitch * bays + 2.0 * _margin   # full plate width (X)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _stud_x():
    """X centres of the studs the plate spans (centred on origin)."""
    span = stud_pitch * bays
    return [-span / 2.0 + i * stud_pitch for i in range(_n_studs)]


def _screw_cut(wp, x, z, thru):
    """Countersunk screw: a through shank + a conical head recess from the
    front face. `thru` is the plate thickness (Y)."""
    shank = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(x, z, 0))
        .circle(screw_dia / 2.0)
        .extrude(thru + 2.0, both=True)
    )
    # Conical countersink opening on the +Y (front) face.
    csk = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(x, z, -(thru / 2.0)))
        .circle(screw_head / 2.0)
        .workplane(offset=screw_head / 2.0)
        .circle(screw_dia / 2.0)
        .loft()
    )
    return wp.cut(shank).cut(csk)


def _keyhole_cut(wp, x, z, thru):
    """A keyhole hanging slot: a big entry circle with an obround throat rising
    above it, both cut through the plate. Lets the plate drop onto a proud
    screw head. Robust (stadium slot, no arc-fan)."""
    big_r = screw_head / 2.0 + 1.4
    throat_w = screw_dia + 1.2
    rise = big_r + 10.0
    entry = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(x, z, 0))
        .circle(big_r)
        .extrude(thru + 2.0, both=True)
    )
    throat = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(x, z + rise / 2.0, 0))
        .slot2D(rise, throat_w, angle=90)
        .extrude(thru + 2.0, both=True)
    )
    return wp.cut(entry).cut(throat)


# ── Part builders ────────────────────────────────────────────────────────────
def build_stud_plate():
    """Flat backing plate on the 16 in stud pitch: two countersunk screws per
    stud plus a keyhole hanging slot per stud, so it both screws down and hangs.
    Plate lies in the XZ plane, thickness along +Y."""
    plate = (
        cq.Workplane("XZ")
        .box(_plate_w, plate_h, plate_t, centered=(True, True, True))
    )
    # Fillet the clean blank corners BEFORE cutting features.
    try:
        plate = plate.edges("|Y").fillet(min(8.0, _margin - 2.0))
    except Exception:
        pass

    z_hi = plate_h / 2.0 - _margin * 0.65
    z_lo = -plate_h / 2.0 + _margin * 0.65
    for x in _stud_x():
        plate = _screw_cut(plate, x, z_lo, plate_t)          # lower fixing screw
        plate = _keyhole_cut(plate, x, z_hi, plate_t)        # upper keyhole hang
    return plate


def build_stud_shelf():
    """A gusseted right-angle shelf bracket screwed to a SINGLE stud. Vertical
    back plate (XZ) + horizontal shelf (XY) + a triangular gusset web tying
    them, so the shelf carries real load. Screw holes on the stud centreline."""
    back_w = max(60.0, _margin * 2.0 + screw_head)
    back = (
        cq.Workplane("XZ")
        .box(back_w, plate_h, plate_t, centered=(True, True, True))
    )
    try:
        back = back.edges("|Y").fillet(min(6.0, plate_t))
    except Exception:
        pass

    # Horizontal shelf projecting +Y from the bottom of the back plate.
    shelf = (
        cq.Workplane("XY")
        .box(back_w, shelf_depth, plate_t, centered=(True, False, False))
        .translate((0, plate_t / 2.0, -plate_h / 2.0))
    )
    body = back.union(shelf)

    # Triangular gusset web in the YZ plane, centred on X, tying shelf to back.
    gh = plate_h * 0.7
    gd = shelf_depth * 0.7
    gusset = (
        cq.Workplane("YZ")
        .polyline([
            (plate_t / 2.0, -plate_h / 2.0 + plate_t),
            (plate_t / 2.0 + gd, -plate_h / 2.0 + plate_t),
            (plate_t / 2.0, -plate_h / 2.0 + plate_t + gh),
        ])
        .close()
        .extrude(plate_t, both=True)   # thickness along X, centred
    )
    body = body.union(gusset)

    # Two fixing screws up the back plate on the stud centreline (x=0).
    z_hi = plate_h / 2.0 - _margin * 0.6
    z_mid = plate_h / 2.0 - _margin * 1.6
    body = _screw_cut(body, 0.0, z_hi, plate_t)
    body = _screw_cut(body, 0.0, z_mid, plate_t)
    return body


def build_stud_hook():
    """A stout J-hook mounted on a stud plate: a small backing plate (XZ) with
    two fixing screws on the stud centreline, plus a solid arm SWEPT along a
    filleted L-path (out +Y, then up +Z) so the whole hook is one clean body
    (a sweep along a continuous wire never leaves a perpendicular-cylinder
    seam). Mates the same stud pitch."""
    back_w = max(60.0, _margin * 2.0 + screw_head)
    back_h = max(plate_h, hook_dia * 3.0)
    back = (
        cq.Workplane("XZ")
        .box(back_w, back_h, plate_t, centered=(True, True, True))
    )
    try:
        back = back.edges("|Y").fillet(min(6.0, plate_t))
    except Exception:
        pass

    r = hook_dia / 2.0
    up_h = hook_dia * 2.0
    y0 = plate_t / 2.0 - r          # start the sweep INSIDE the plate (overlap)
    y_tip = plate_t / 2.0 + hook_len
    bend = min(hook_len * 0.4, up_h * 0.9, r * 1.6)

    # Sweep path in the YZ plane: from inside the plate straight out +Y, a
    # TANGENT radiusArc turning up, then straight up +Z. A circle swept along
    # this continuous wire is a single clean solid (a sharp 90-degree corner in
    # a round-transition sweep tessellates non-watertight — the arc avoids it).
    path = (
        cq.Workplane("YZ")
        .moveTo(y0, 0.0)
        .lineTo(y_tip - bend, 0.0)
        .radiusArc((y_tip, bend), -bend)
        .lineTo(y_tip, up_h)
    )
    arm = (
        cq.Workplane("XZ")            # profile plane ⟂ to path start (path runs +Y)
        .transformed(offset=cq.Vector(0, 0, y0))
        .circle(r)
        .sweep(path, transition="round")
    )
    body = back.union(arm)

    # Two fixing screws on the stud centreline, above and below the arm root.
    body = _screw_cut(body, 0.0, back_h / 2.0 - _margin * 0.6, plate_t)
    body = _screw_cut(body, 0.0, -back_h / 2.0 + _margin * 0.6, plate_t)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "stud_shelf":
    result = build_stud_shelf()
elif target_part == "stud_hook":
    result = build_stud_hook()
else:
    result = build_stud_plate()
