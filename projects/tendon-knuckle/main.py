"""
Tendon-Driven Knuckle — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A cable-driven articulated knuckle for soft / underactuated robotic hands. A
tendon (fishing line, Dyneema, or steel cable) runs through a channel on the palm
(flexor) side; pulling it curls the joint, while an elastic return on the back
(extensor) side straightens it — the classic tendon-driven finger. Each part is a
PRINTABLE SINGLE-BODY solid: the tendon channels and pin bores are through-holes
that vent to faces (no trapped void), so the whole mesh is watertight.

Modes:
  - knuckle        : one articulated joint block — a clevis on one end and a
                     tongue on the other (they interlock through a pivot pin),
                     with a flexor tendon channel and an extensor elastic groove.
  - finger_segment : a straight phalanx segment with a through tendon channel and
                     a soft-hinge notch — chain several for a compliant finger.
  - tendon_pulley  : a winch pulley / spool that the tendon wraps, with a set-
                     screw hub bore for the drive shaft.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use
    globals()/eval/getattr — they are not in the sandbox's allowed builtins.
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
target_part = str(PARAM(lambda: target_part, "knuckle"))
# "knuckle" | "finger_segment" | "tendon_pulley"

seg_len = float(PARAM(lambda: seg_len, 26.0))     # segment length (Y)
seg_w = float(PARAM(lambda: seg_w, 18.0))         # segment width (X)
seg_h = float(PARAM(lambda: seg_h, 16.0))         # segment height (Z)
pin_d = float(PARAM(lambda: pin_d, 3.0))          # pivot pin diameter
tendon_d = float(PARAM(lambda: tendon_d, 2.0))    # tendon channel diameter
wall = float(PARAM(lambda: wall, 2.4))            # wall thickness around channels
pulley_d = float(PARAM(lambda: pulley_d, 24.0))   # pulley outer diameter
shaft_d = float(PARAM(lambda: shaft_d, 5.0))      # pulley drive-shaft bore

# ── Clamp to sane ranges ─────────────────────────────────────────────────────
seg_len = max(14.0, min(seg_len, 50.0))
seg_w = max(10.0, min(seg_w, 34.0))
seg_h = max(8.0, min(seg_h, 28.0))
pin_d = max(1.5, min(pin_d, 6.0))
tendon_d = max(1.0, min(tendon_d, 4.0))
wall = max(1.5, min(wall, 5.0))
pulley_d = max(12.0, min(pulley_d, 50.0))
shaft_d = max(3.0, min(shaft_d, 12.0))


# ── Knuckle: interlocking clevis + tongue joint ──────────────────────────────
def build_knuckle():
    """One articulated joint: a body that is a clevis (two-pronged fork) at the
    proximal (-Y) end and a single tongue at the distal (+Y) end. A pivot pin
    passes across X through both. A flexor tendon channel runs along the palm
    (-Z) side; an extensor elastic groove runs along the back (+Z) side. Built as
    a single solid by unioning overlapping boxes, then cutting through-holes."""
    half_w = seg_w / 2.0
    prong_w = seg_w * 0.3
    gap = seg_w - 2.0 * prong_w   # central gap for the mating tongue
    joint_r = seg_h * 0.5

    # Central spine block (the segment body), y from 0..seg_len.
    spine = (
        cq.Workplane("XY")
        .box(seg_w, seg_len, seg_h, centered=(True, False, False))
    )
    body = spine

    # Distal tongue: a rounded tab sticking out +Y, centred, half width.
    tongue = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, seg_len, 0))
        .box(gap, joint_r * 1.6, seg_h, centered=(True, False, False))
    )
    # round its tip
    tongue_tip = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, seg_h / 2.0, -(seg_len + joint_r * 1.6)))
        .circle(seg_h / 2.0)
        .extrude(gap, both=False)
        .translate((gap / 2.0, 0, 0))
    )
    body = body.union(tongue).union(tongue_tip)

    # Proximal clevis: two prongs sticking out -Y (left & right), with the gap
    # between them to receive the previous segment's tongue.
    for sx in (-1, 1):
        px = sx * (half_w - prong_w / 2.0)
        prong = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(px, -joint_r * 1.6, 0))
            .box(prong_w, joint_r * 1.6 + 0.2, seg_h, centered=(True, False, False))
        )
        prong_tip = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(px, seg_h / 2.0, joint_r * 1.6))
            .circle(seg_h / 2.0)
            .extrude(-prong_w)
            .translate((prong_w / 2.0, 0, 0))
        )
        body = body.union(prong).union(prong_tip)

    # Pivot pin bore across X through the clevis prongs (vented both ends).
    pin_z = seg_h / 2.0
    pin_bore = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(-joint_r * 0.8, pin_z, 0))
        .circle(pin_d / 2.0)
        .extrude(half_w + 2.0, both=True)
    )
    body = body.cut(pin_bore)

    # Pivot pin bore across X through the distal tongue too (its own hole).
    tongue_pin = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(seg_len + joint_r * 0.8, pin_z, 0))
        .circle(pin_d / 2.0)
        .extrude(half_w + 2.0, both=True)
    )
    body = body.cut(tongue_pin)

    # Flexor tendon channel along the palm (-Z) side: a through hole running the
    # length of the spine in Y, near the bottom (vented both Y ends).
    flexor = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, wall + tendon_d / 2.0, 1.0))
        .circle(tendon_d / 2.0)
        .extrude(-(seg_len + joint_r * 1.6 + 2.0))
    )
    body = body.cut(flexor)

    # Extensor elastic groove along the back (+Z) side: a shallow channel open to
    # the top face (vents up), for a return elastic.
    ext = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -1.0, seg_h - tendon_d * 0.7))
        .box(tendon_d + 0.8, seg_len + 2.0, tendon_d, centered=(True, False, False))
    )
    body = body.cut(ext)
    return body


def build_finger_segment():
    """A straight phalanx segment: a rounded bar with a through flexor tendon
    channel and a soft-hinge V-notch on the palm side (a living-hinge relief).
    Chain several with cord for an underactuated compliant finger."""
    body = (
        cq.Workplane("XY")
        .box(seg_w, seg_len, seg_h, centered=(True, False, False))
    )
    try:
        body = body.edges("|Y").fillet(min(3.0, seg_h / 3.0, seg_w / 3.0))
    except Exception:
        pass

    # Through tendon channel along Y near the palm (-Z) side (vented both ends).
    chan = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, wall + tendon_d / 2.0, 1.0))
        .circle(tendon_d / 2.0)
        .extrude(-(seg_len + 2.0))
    )
    body = body.cut(chan)

    # A second, dorsal channel for a return cord (vented both ends).
    chan2 = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, seg_h - wall - tendon_d / 2.0, 1.0))
        .circle(tendon_d / 2.0)
        .extrude(-(seg_len + 2.0))
    )
    body = body.cut(chan2)

    # Soft-hinge V-notch across the palm side at mid-length (opens to -Z face).
    notch_w = seg_w + 2.0
    notch = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, 0, -seg_len / 2.0))
        .polyline([(-notch_w / 2.0, 0), (notch_w / 2.0, 0), (0, seg_h * 0.45)])
        .close()
        .extrude(notch_w, both=True)
    )
    # position the notch prism so its apex points up from the palm face
    notch = notch.translate((0, 0, 0))
    body = body.cut(notch)
    return body


def build_tendon_pulley():
    """A winch pulley / spool the tendon wraps around, with a set-screw hub bore
    for the drive shaft. A grooved disc: two flanges with a narrower waist between
    them (built as stacked cylinders → single solid), a central shaft bore, and a
    radial set-screw hole into the hub."""
    ro = pulley_d / 2.0
    flange_t = max(2.0, pulley_d * 0.08)
    waist_r = ro * 0.68
    waist_h = max(3.0, tendon_d * 2.0)
    hub_r = max(shaft_d / 2.0 + 3.0, waist_r * 0.5)

    # bottom flange
    body = cq.Workplane("XY").circle(ro).extrude(flange_t)
    # waist (narrower) overlapping up
    body = body.union(
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, flange_t - 0.2))
        .circle(waist_r)
        .extrude(waist_h + 0.4)
    )
    # top flange
    body = body.union(
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, flange_t + waist_h - 0.2))
        .circle(ro)
        .extrude(flange_t + 0.2)
    )
    total_h = 2.0 * flange_t + waist_h
    # central shaft bore (through, vented both ends)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(shaft_d / 2.0)
        .extrude(total_h + 2.0)
    )
    body = body.cut(bore)
    # tendon anchor hole: a small radial hole through a flange into the waist
    anchor = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, flange_t + waist_h / 2.0, ro - 1.0))
        .circle(max(0.8, tendon_d / 2.0))
        .extrude(ro + 1.0)
    )
    body = body.cut(anchor)
    # set-screw hole radially into the hub (vents from rim to the shaft bore)
    setscrew = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, flange_t + waist_h / 2.0, ro - 1.0))
        .circle(1.4)
        .extrude(ro - hub_r * 0.2)
    )
    # rotate the set-screw 90° so it doesn't coincide with the anchor
    setscrew = setscrew.rotate((0, 0, 0), (0, 0, 1), 90.0)
    body = body.cut(setscrew)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "finger_segment":
    result = build_finger_segment()
elif target_part == "tendon_pulley":
    result = build_tendon_pulley()
else:
    result = build_knuckle()
