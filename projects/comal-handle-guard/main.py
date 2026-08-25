"""
Comal Handle Guard — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A guard for the bare steel handle of a comal.

The comal is the flat griddle of Mesoamerica — clay or, today, most often plain
sheet steel — on which tortillas are cooked, chiles and tomatoes are charred for
salsa, and coffee and cacao are toasted. It is the oldest continuously used cooking
surface in the region and it is still in daily use in millions of kitchens. A steel
comal is usually a plain disc with a flat strap handle welded or riveted to its rim:
one piece of metal, no insulation anywhere, sitting over a flame.

The problem is entirely mundane and entirely real. The handle conducts, so it reaches
the same temperature as the pan, and the thing that gets used to grab it is whatever
cloth is nearest — a rag, a fold of apron, a towel that may be damp. A damp cloth is
the worst case: water conducts far better than the air trapped in a dry one, and it
carries heat to the hand faster than the cloth can be dropped. This guard replaces
that improvisation with a part that clamps on and stays on.

What the guard actually does:
  Printed plastic cannot survive a flame. The guard therefore does NOT try to insulate
  a handle sitting IN the fire — it lives on the OUTER portion of the handle, away
  from the pan, where a strap handle is already much cooler than at its root, and it
  puts a stated air gap plus a wall of low-conductivity material between the steel and
  the hand. `material_temp_class` states plainly which polymer the geometry assumes
  and the README carries the honest limits, because a guard that fails silently at
  temperature would be worse than the rag it replaces.

Handle stock is the parameterisation:
  A comal handle is flat strap — the whole family is described by width x thickness.
  That same rectangular-stock series is what the commons' other handle cartridges
  use, so this guard interchanges with them rather than publishing a fourth
  convention for "a flat handle".

Modes are dispatched via `target_part`:
  * "guard"      — the clamping guard itself: a C-section that springs over the strap
                   and stands the hand off it on a stated air gap.
  * "hook_rest"  — a wall hook sized to the same strap, so the comal hangs by its
                   handle and the guard has somewhere to live between uses.
  * "lid_knob"   — a knob on the same stock interface, for the flat tapadera (lid)
                   that covers a comal to steam tortillas soft.

Watertightness strategy:
  Every part is one blank with THROUGH cuts, and every cut is bounded INSIDE the blank
  with a full margin — never run past its edges, which is a cut-off rather than a
  slot. The C-section's mouth is capped at `2*r - 0.8` equivalent for a rectangular
  jaw, so two retaining legs always survive. No internal void is ever sealed: a closed
  cavity is unprintable and trimesh counts its inner shell as a separate body (found
  in solar-dryer-tray, this same batch). No fillet is taken on any edge a slot or bore
  has touched: OCC blends such arcs without raising and returns a non-watertight
  solid (found in graft-clip, this same batch).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Material temperature classes ─────────────────────────────────────────────
# Continuous-service ceiling, in degrees C, for the polymer the geometry assumes.
# These are conservative working numbers for FDM prints, not datasheet peaks: a
# printed part is anisotropic and loses stiffness well below its published HDT.
#
# `min_wall` is the wall this cartridge will not build below for that class, because
# the guard's whole function is a thermal break and a thin one is not a break.
MATERIAL_CLASS = {
    "pla":   {"ceiling_c": 55.0,  "min_wall": 4.0, "label": "PLA — NOT recommended"},
    "petg":  {"ceiling_c": 70.0,  "min_wall": 3.5, "label": "PETG"},
    "abs":   {"ceiling_c": 90.0,  "min_wall": 3.0, "label": "ABS / ASA"},
    "nylon": {"ceiling_c": 110.0, "min_wall": 3.0, "label": "Nylon (PA)"},
    "pp":    {"ceiling_c": 95.0,  "min_wall": 3.2, "label": "Polypropylene"},
}


def mat_class(name):
    """Look up a material class, defaulting to PETG."""
    return MATERIAL_CLASS.get(name, MATERIAL_CLASS["petg"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "guard"))
material_temp_class = str(PARAM(lambda: material_temp_class, "petg"))

handle_width_mm = float(PARAM(lambda: handle_width_mm, 22.0))
handle_thickness_mm = float(PARAM(lambda: handle_thickness_mm, 4.0))
grip_length_mm = float(PARAM(lambda: grip_length_mm, 90.0))
arc_radius_mm = float(PARAM(lambda: arc_radius_mm, 26.0))
wall = float(PARAM(lambda: wall, 4.0))
air_gap_mm = float(PARAM(lambda: air_gap_mm, 2.5))

# Clamp so extreme UI values still build watertight.
handle_width_mm = max(10.0, min(handle_width_mm, 45.0))
handle_thickness_mm = max(2.0, min(handle_thickness_mm, 12.0))
grip_length_mm = max(40.0, min(grip_length_mm, 180.0))
arc_radius_mm = max(12.0, min(arc_radius_mm, 60.0))
wall = max(2.5, min(wall, 10.0))
air_gap_mm = max(0.0, min(air_gap_mm, 6.0))

# The material class raises the wall floor: the guard IS a thermal break, and a break
# thinner than the material can carry is not a break. Applied as a clamp rather than
# a warning, because a silently-too-thin guard fails at the hand.
wall = max(wall, mat_class(material_temp_class)["min_wall"])


# ── Derived clamp geometry ───────────────────────────────────────────────────
def jaw_opening():
    """Internal jaw the strap sits in, plus the stated standoff air gap.

    The air gap is the point of the part: still air is a far better insulator than
    any printable polymer, so most of the thermal break is the gap and only the rest
    is the wall. Returns (jaw_w, jaw_t)."""
    return (handle_width_mm + 2.0 * air_gap_mm + 0.6,
            handle_thickness_mm + 2.0 * air_gap_mm + 0.6)


def standoff_mm():
    """Total material-plus-air separation between steel and hand, one side."""
    return air_gap_mm + wall


# ── Part builders ─────────────────────────────────────────────────────────────
def build_guard():
    """The clamping guard: a C-section that springs over the flat strap handle and
    stands the hand off it on a stated air gap.

    The blank is derived FROM the jaw it must contain — jaw plus a full wall on every
    side — so no cut can reach an edge at any parameter combination. The mouth is
    capped so two retaining legs always survive; without that cap a wide mouth on a
    thin handle severs the C into loose arcs."""
    jaw_w, jaw_t = jaw_opening()
    length = grip_length_mm

    body_w = jaw_w + 2.0 * wall
    body_t = jaw_t + 2.0 * wall

    body = cq.Workplane("XY").box(length, body_w, body_t, centered=(True, True, False))

    # Comfort curve: the guard's outer back is arched so it beds into a palm rather
    # than presenting a square edge. Cut as a cylinder from above — bounded so it can
    # never break through into the jaw.
    arc_r = max(arc_radius_mm, body_w * 0.6)
    max_bite = max(0.0, wall * 0.5)
    if max_bite >= 0.4:
        # Place the cutting cylinder so it removes exactly `max_bite` at the crown.
        cz = body_t + arc_r - max_bite
        arc = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0.0, cz, 0.0))
            .circle(arc_r)
            .extrude(length * 2.0, both=True)
        )
        try:
            body = body.cut(arc)
        except Exception:
            pass

    # The jaw: a through channel along the handle axis, open at both ends so the
    # guard slides on. Bounded in the two cross-axes by a full wall.
    jaw = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, wall))
        .box(length + 2.0, jaw_w, jaw_t, centered=(True, True, False))
    )
    body = body.cut(jaw)

    # Mouth slot so the guard springs ON rather than having to be threaded from the
    # comal end (which a welded handle usually forbids). Opened downward through the
    # floor, running past the underside, and capped so two legs survive.
    mouth = min(jaw_w * 0.7, jaw_w - 2.0)
    mouth = max(1.5, mouth)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, -1.0))
        .box(length + 2.0, mouth, wall + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # Finger ridges on the outside, so a greasy hand does not slide off. Bounded
    # inside the guard's own length with a margin, and cut only to a fraction of the
    # wall so they can never reach the jaw.
    ridge_d = min(1.2, wall * 0.25)
    if ridge_d >= 0.3 and length > 40.0:
        margin = max(6.0, length * 0.12)
        span = length - 2.0 * margin
        n = int(max(1, min(6, math.floor(span / 12.0))))
        if n >= 1 and span > 0:
            step = span / n
            pts = []
            for i in range(n):
                x = -span / 2.0 + step * (i + 0.5)
                pts.append((x, body_t + arc_radius_mm * 0.0))
            tool = (
                cq.Workplane("XZ")
                .pushPoints([(p[0], body_t - ridge_d * 0.4) for p in pts])
                .circle(ridge_d)
                .extrude(body_w * 2.0, both=True)
            )
            try:
                body = body.cut(tool)
            except Exception:
                pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_hook_rest():
    """A wall hook sized to the same strap stock, so the comal hangs by its handle.

    A comal lives on the wall between uses in most kitchens that have one. Hanging it
    by the handle rather than leaning it on a rim keeps the cooking face off the wall
    and off the counter."""
    jaw_w, jaw_t = jaw_opening()
    plate_t = max(3.0, wall * 0.8)
    plate_w = jaw_w + 4.0 * wall
    plate_h = max(40.0, jaw_t * 4.0 + 30.0)

    body = cq.Workplane("XY").box(plate_t, plate_w, plate_h, centered=(True, True, False))

    # Two screw bores through the plate, bounded inside it with a full margin.
    bore_r = min(2.5, plate_w * 0.12, plate_t * 1.5)
    if bore_r >= 1.2:
        margin = bore_r + max(3.0, plate_t)
        for sign in (-1.0, 1.0):
            z = plate_h - margin if sign > 0 else margin
            bore = (
                cq.Workplane("YZ")
                .transformed(offset=cq.Vector(0.0, z, 0.0))
                .circle(bore_r)
                .extrude(plate_t * 3.0, both=True)
            )
            try:
                body = body.cut(bore)
            except Exception:
                pass

    # The hook: an L that the strap drops into, unioned volumetrically into the plate.
    arm_len = jaw_t + wall * 2.0 + 6.0
    arm_h = max(6.0, wall * 1.5)
    arm_z = plate_h * 0.42
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(plate_t * 0.5, 0.0, arm_z))
        .box(arm_len, min(plate_w, jaw_w + 2.0 * wall), arm_h, centered=(True, True, False))
    )
    body = body.union(arm)

    # Upturned lip at the arm's far end so the comal cannot walk off. Placed from the
    # arm's REAL end and sunk back into it — the detachment lesson from
    # hive-frame-spacer and solar-dryer-tray in this same batch.
    arm_x1 = plate_t * 0.5 + arm_len / 2.0
    lip_h = max(6.0, jaw_t + wall)
    lip_t = max(3.0, wall * 0.8)
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(arm_x1 - lip_t / 2.0, 0.0, arm_z))
        .box(lip_t, min(plate_w, jaw_w + 2.0 * wall), lip_h, centered=(True, True, False))
    )
    body = body.union(lip)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_lid_knob():
    """A knob for the flat tapadera that covers a comal to steam tortillas soft.

    Mounted on the same flat-stock interface: a tapadera is usually a plain disc with
    a strap or a drilled tab, so the knob clamps the same rectangular section the
    guard does rather than needing a threaded boss the lid does not have."""
    jaw_w, jaw_t = jaw_opening()
    base_w = jaw_w + 2.0 * wall
    base_t = jaw_t + 2.0 * wall
    base_l = max(24.0, jaw_w * 1.2)

    body = cq.Workplane("XY").box(base_l, base_w, base_t, centered=(True, True, False))

    # Jaw channel, through along X so the knob slides onto a tab or strap.
    jaw = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, wall))
        .box(base_l + 2.0, jaw_w, jaw_t, centered=(True, True, False))
    )
    body = body.cut(jaw)

    # Mouth downward so it springs on, capped so two legs survive.
    mouth = max(1.5, min(jaw_w * 0.7, jaw_w - 2.0))
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, -1.0))
        .box(base_l + 2.0, mouth, wall + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # The knob itself: a stem and a domed head, both unioned volumetrically.
    stem_r = max(4.0, min(base_w * 0.28, base_l * 0.28))
    stem_h = max(10.0, jaw_t * 1.6)
    stem_z0 = base_t - wall * 0.5
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, stem_z0))
        .circle(stem_r)
        .extrude(stem_h + (base_t - stem_z0))
    )
    body = body.union(stem)

    # The domed head is a REVOLVE ending on a small FLAT apex — never a sphere.
    #
    # `sphere(r).cut(box)` was tried first and is broken at the tessellator, not at
    # the kernel: OCC reports a single valid solid, but the exported mesh comes back
    # non-watertight and splits into two bodies, because a sphere's poles are
    # degenerate points where every meridian meets. Isolating the build made it
    # unambiguous — the HEAD ALONE was already two bodies before any union, so the
    # problem was never the join to the stem.
    #
    # A profile revolved to a point on the axis has the same defect. Ending the
    # profile on a small flat apex (`apex_r`) instead of a point avoids it, which is
    # the same fix the commons' dome geometry already uses elsewhere.
    head_r = stem_r * 1.7
    head_h = head_r * 0.9
    head_z = base_t + stem_h - wall * 0.5      # sunk into the stem, volumetric union
    apex_r = max(0.8, head_r * 0.12)
    prof = (
        cq.Workplane("XZ")
        .moveTo(0.0, head_z)
        .lineTo(head_r, head_z)
        .threePointArc((head_r * 0.92, head_z + head_h * 0.55),
                       (apex_r, head_z + head_h))
        .lineTo(0.0, head_z + head_h)
        .close()
    )
    try:
        head = prof.revolve(360, (0, 0, 0), (0, 1, 0))
        body = body.union(head)
    except Exception:
        pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "guard": build_guard,
    "hook_rest": build_hook_rest,
    "lid_knob": build_lid_knob,
}

result = _dispatch.get(target_part, build_guard)()
