"""
Switch-Adapted Toy / AT Switch Mount — Yantra4D Hyperobject Cartridge (CadQuery).

A mount that cradles a round assistive-technology (AT) switch so it can be
presented at a reliable, repeatable position for a user who activates devices,
toys, or communication aids with a single switch. The switch body drops into a
shallow circular recess; its 3.5 mm (1/8 in) mono cable exits through an open
side channel and is retained by a strain-relief notch. AT switches use the
de-facto 1/8 in / 3.5 mm mono jack (e.g. AbleNet Specs / Big Red family), so a
mount built to the switch's body diameter suits the whole switch ecosystem.

  * "switch_cradle"      — a flat-base cradle with a screw-down flange
                           (target_part == "switch_cradle").
  * "switch_wedge"       — the cradle on an inclined wedge so the switch face
                           tilts toward the user (target_part == "switch_wedge").
  * "switch_strap_mount" — the cradle with two transverse strap slots to lash it
                           to a tray edge, armrest, or lap tray
                           (target_part == "switch_strap_mount").

Watertight strategy: every part is one manifold solid. The switch recess is an
open-topped pocket (vents to the top face — no trapped void). The cable channel
is a through-groove cut from the recess wall out to the block edge (open both
sides). Screw holes and strap slots are through-cuts open to outer faces. The
wedge is a single lofted/extruded prism the cradle block unions onto with an
overlap so the weld is solid. Fillets are applied to clean blanks before feature
cuts and wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "switch_cradle"))
# switch_cradle | switch_wedge | switch_strap_mount

switch_dia = float(PARAM(lambda: switch_dia, 63.0))   # AT switch body diameter (Specs ~63mm)
recess_depth = float(PARAM(lambda: recess_depth, 8.0))  # how deep the switch seats
clearance = float(PARAM(lambda: clearance, 0.6))      # radial slip gap around switch
wall = float(PARAM(lambda: wall, 4.0))                # cradle wall / floor thickness
cable_dia = float(PARAM(lambda: cable_dia, 4.5))      # 3.5mm jack cable OD (with jacket)
flange = float(PARAM(lambda: flange, 12.0))           # screw flange width around cradle
screw_dia = float(PARAM(lambda: screw_dia, 4.2))      # mounting screw clearance (#8 / M4)
tilt_ang = float(PARAM(lambda: tilt_ang, 20.0))       # wedge incline (deg)
strap_w = float(PARAM(lambda: strap_w, 26.0))         # strap slot width

# ── Clamps (keep the kernel safe at UI extremes) ─────────────────────────────
switch_dia = max(20.0, min(switch_dia, 90.0))
recess_depth = max(3.0, min(recess_depth, 20.0))
clearance = max(0.0, min(clearance, 2.0))
wall = max(2.5, min(wall, 10.0))
cable_dia = max(2.0, min(cable_dia, 10.0))
flange = max(6.0, min(flange, 25.0))
screw_dia = max(2.5, min(screw_dia, 6.0))
tilt_ang = max(5.0, min(tilt_ang, 35.0))
strap_w = max(12.0, min(strap_w, 40.0))

recess_r = switch_dia / 2.0 + clearance
outer_r = recess_r + wall
block_h = recess_depth + wall


# ── Shared builders ──────────────────────────────────────────────────────────
def _cradle_block(base_r, height):
    """A solid cylindrical cradle blank (rounded outer edge, filleted before any
    feature cut so OCCT clean() stays happy)."""
    blk = cq.Workplane("XY").circle(base_r).extrude(height)
    try:
        blk = blk.edges("|Z or <Z").fillet(min(2.0, wall - 0.5))
    except Exception:
        pass
    return blk


def _cut_recess(body, top_z):
    """Open-topped circular pocket for the switch, cut down from top_z. Vents to
    the top face → no trapped void."""
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, top_z - recess_depth))
        .circle(recess_r)
        .extrude(recess_depth + 1.0)
    )
    return body.cut(pocket)


def _cut_cable_channel(body, top_z):
    """A through-groove from the recess wall out to the block edge so the switch
    cable exits the side. Open at both ends (recess + outside) → vents."""
    ch_z = top_z - recess_depth + cable_dia / 2.0
    length = outer_r + 4.0
    chan = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, ch_z, 0))
        .circle(cable_dia / 2.0)
        .extrude(-(length))              # runs out along +Y through the wall
    )
    # Rotate the cut so it lies along +Y and pierces the wall to outside.
    chan = chan.rotate((0, 0, 0), (0, 0, 1), 90)
    # A rectangular slot above the round channel opens it to the top so the cable
    # drops in (a keyhole), still all one through-cut region.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, length / 2.0, ch_z))
        .box(cable_dia * 0.7, length, recess_depth, centered=(True, True, False))
    )
    try:
        body = body.cut(chan).cut(slot)
    except Exception:
        body = body.cut(chan)
    return body


def _cut_flange_screws(body, ring_r, top_z):
    """Four through screw holes on a ring, open top-to-bottom (vented)."""
    holes = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .pushPoints([(ring_r, 0), (-ring_r, 0), (0, ring_r), (0, -ring_r)])
        .circle(screw_dia / 2.0)
        .extrude(top_z + 2.0)
    )
    return body.cut(holes)


def build_switch_cradle():
    """A round cradle with a screw-down flange: switch drops in the top recess,
    cable exits the side, four screws fix it to a surface."""
    base_r = outer_r + flange
    body = _cradle_block(base_r, block_h)
    body = _cut_recess(body, block_h)
    body = _cut_cable_channel(body, block_h)
    body = _cut_flange_screws(body, outer_r + flange * 0.5, block_h)
    return body


def build_switch_wedge():
    """The cradle on an inclined wedge so the switch face tilts toward the user.

    Construction that stays one manifold at every extreme: a single solid whose
    profile (in the YZ plane, extruded along X) is a full-thickness slab plus a
    triangular ramp on top. The recess and cable channel are cut into the ramp on
    a workplane rotated to match the incline, so the switch seats square to the
    ramp. The slab floor beneath the ramp is always at least `block_h` thick, so
    even a deep recess cannot sever the base — no disconnected slivers."""
    base_r = outer_r + 3.0
    span = 2.0 * base_r
    # The ramp rises across the depth (Y). Keep a full-thickness slab under it so
    # the switch floor is always solid regardless of recess depth.
    slab = block_h + recess_depth
    rise = span * math.tan(math.radians(tilt_ang))
    # Profile in YZ: rectangle (slab) + triangle (ramp), a single closed polygon.
    pts = [
        (-base_r, 0.0),
        (base_r, 0.0),
        (base_r, slab),
        (-base_r, slab + rise),
    ]
    body = (
        cq.Workplane("YZ")
        .polyline(pts)
        .close()
        .extrude(span / 2.0, both=True)
    )
    try:
        body = body.edges("|X").fillet(2.0)
    except Exception:
        pass

    # Ramp surface: passes through (y=+base_r, z=slab) tilted up toward -Y. Cut a
    # pocket on a workplane coincident with the ramp, centred on the ramp face.
    ramp_z = slab + rise / 2.0                 # ramp height at y=0 (mid)
    ramp_plane = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, ramp_z), rotate=cq.Vector(tilt_ang, 0, 0))
    )
    pocket = ramp_plane.circle(recess_r).extrude(-recess_depth)
    body = body.cut(pocket)

    # Cable channel: an axis-aligned box slot running along +Y from the pocket
    # centre out past the low (+Y) side wall, sized to the cable, its top open to
    # the ramp. A straight box through the side face always exits to air and can
    # never sever the body — one vented through-region into the pocket.
    slot_len = base_r + recess_r + 4.0
    ch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, base_r + 2.0 - slot_len / 2.0, slab - cable_dia))
        .box(cable_dia, slot_len, cable_dia + rise + recess_depth,
             centered=(True, True, False))
    )
    try:
        body = body.cut(ch)
    except Exception:
        pass
    return body


def build_switch_strap_mount():
    """The cradle with two transverse strap slots so a hook-and-loop strap lashes
    it to a tray edge, wheelchair armrest, or lap tray."""
    base_r = outer_r + 6.0
    body = _cradle_block(base_r, block_h)
    body = _cut_recess(body, block_h)
    body = _cut_cable_channel(body, block_h)
    # Two strap slots through X, below the recess floor so they never open it.
    slot_z = wall * 0.5
    slot_h = min(wall * 0.8, 3.0)
    y_off = outer_r + (base_r - outer_r) * 0.5
    for yo in (y_off, -y_off):
        slot = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(yo, slot_z + slot_h / 2.0, 0))
            .box(strap_w, slot_h, 2.0 * base_r + 4.0, centered=(True, True, True))
        )
        try:
            body = body.cut(slot)
        except Exception:
            pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "switch_wedge":
    result = build_switch_wedge()
elif target_part == "switch_strap_mount":
    result = build_switch_strap_mount()
else:  # "switch_cradle"
    result = build_switch_cradle()
