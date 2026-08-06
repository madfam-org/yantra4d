"""
Reagent Bottle Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Snap-on identification hardware for reagent and solution bottles: a C-clip that
grips the bottle body and presents a flat window for a written or printed label,
a hanging neck tag, and a small cap marker disc that colour-codes a screw cap.

  * "label_clip" — a C-clip around the bottle body carrying a raised-border label
                   window (target_part == "label_clip").
  * "neck_tag"   — a keyhole tag that drops over the bottle neck with a label
                   panel and a write-on area (target_part == "neck_tag").
  * "cap_marker" — a thin disc that sits on the cap top with a bold notch index
                   and a label ring (target_part == "cap_marker").

Watertight strategy: the clip is a solid C-ring (a full ring with a mouth slot
removed) fused with a solid label plate; the label "window" is a shallow recess
that never perforates the plate. The tag and marker are single extruded plates
with holes cut straight through. Every result is one manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "label_clip"))  # label_clip | neck_tag | cap_marker

bottle_dia = float(PARAM(lambda: bottle_dia, 54.0))   # bottle body diameter (mm)
neck_dia   = float(PARAM(lambda: neck_dia,   28.0))   # bottle neck diameter (mm)
label_w    = float(PARAM(lambda: label_w,    40.0))   # label window width (mm)
label_h    = float(PARAM(lambda: label_h,    24.0))   # label window height (mm)
wall       = float(PARAM(lambda: wall,        3.0))   # clip / plate thickness
clearance  = float(PARAM(lambda: clearance,   0.5))   # grip clearance per side
clip_h     = float(PARAM(lambda: clip_h,     18.0))   # clip band height

# ── Clamps ───────────────────────────────────────────────────────────────────
bottle_dia = max(15.0, min(bottle_dia, 120.0))
neck_dia   = max(10.0, min(neck_dia, 80.0))
label_w    = max(15.0, min(label_w, 90.0))
label_h    = max(10.0, min(label_h, 70.0))
wall       = max(2.0,  min(wall, 8.0))
clearance  = max(0.0,  min(clearance, 2.0))
clip_h     = max(8.0,  min(clip_h, 60.0))


def label_plate(w, h, th):
    """A rounded label plate with a shallow recessed writing window bordered by a
    raised lip. The recess never cuts through (leaves `th*0.4` behind)."""
    plate = (
        cq.Workplane("XY")
        .box(w + 2.0 * wall, h + 2.0 * wall, th, centered=(True, True, False))
        .edges("|Z").fillet(min(wall, 2.5))
    )
    recess = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, th * 0.6))
        .box(w, h, th, centered=(True, True, False))
    )
    plate = plate.cut(recess)
    return plate


# ── Part builders ────────────────────────────────────────────────────────────
def build_label_clip():
    """A C-clip band around the bottle with a label plate on the front."""
    bore_r = bottle_dia / 2.0 + clearance
    clip_or = bore_r + wall
    band = cq.Workplane("XY").circle(clip_or).extrude(clip_h)
    bore = cq.Workplane("XY").circle(bore_r).extrude(clip_h + 2.0).translate((0, 0, -1.0))
    band = band.cut(bore)
    # Mouth opening ~78% of the diameter so it snaps over the bottle and grips.
    mouth = max(3.0, bottle_dia * 0.78)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, clip_or, 0))
        .box(mouth, clip_or * 2.2, clip_h + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    band = band.cut(slot)

    # Label plate mounted on the back (opposite the mouth).
    plate = label_plate(label_w, label_h, wall)
    plate = plate.rotate((0, 0, 0), (1, 0, 0), 90).translate(
        (0, -clip_or - wall, clip_h / 2.0)
    )
    body = band.union(plate)
    return body


def build_neck_tag():
    """A keyhole tag: a round collar that drops over the neck, joined to a label
    panel that hangs to the front."""
    collar_bore = neck_dia / 2.0 + clearance
    collar_or = collar_bore + wall
    collar = cq.Workplane("XY").circle(collar_or).extrude(wall)
    hole = cq.Workplane("XY").circle(collar_bore).extrude(wall + 2.0).translate((0, 0, -1.0))
    collar = collar.cut(hole)
    # Keyhole entry slot so it slides onto the neck from the side.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, collar_or, 0))
        .box(neck_dia * 0.5, collar_or * 2.2, wall + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    collar = collar.cut(slot)

    # Label panel joined to the front of the collar, coplanar (flat tag).
    plate = label_plate(label_w, label_h, wall)
    plate = plate.translate((0, -collar_or - wall - label_h / 2.0, 0))
    # Bridge neck between collar and plate.
    bridge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -collar_or, 0))
        .box(wall * 3.0, wall * 2.5, wall, centered=(True, False, False))
    )
    body = collar.union(bridge).union(plate)
    return body


def build_cap_marker():
    """A thin disc for the cap top: a label ring with a bold index notch so a
    cap's contents are identifiable at a glance."""
    disc_r = max(neck_dia, 20.0) / 2.0 + wall
    disc = cq.Workplane("XY").circle(disc_r).extrude(wall)
    try:
        disc = disc.edges("<Z").chamfer(min(0.8, wall * 0.3))
    except Exception:
        pass
    # Central hole so it drops over a cap knob / finial (optional grip).
    hub = cq.Workplane("XY").circle(disc_r * 0.28).extrude(wall + 2.0).translate((0, 0, -1.0))
    disc = disc.cut(hub)
    # Bold index notch (a wedge cut from the rim) to point at a scale.
    notch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, disc_r, 0))
        .box(disc_r * 0.28, disc_r * 0.7, wall + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    disc = disc.cut(notch)
    # Shallow label ring recess on top (write-on band).
    ring = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall * 0.55))
        .circle(disc_r * 0.85)
        .circle(disc_r * 0.42)
        .extrude(wall)
    )
    disc = disc.cut(ring)
    return disc


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "neck_tag":
    result = build_neck_tag()
elif target_part == "cap_marker":
    result = build_cap_marker()
else:  # "label_clip"
    result = build_label_clip()
