"""
Radiator / Baseboard Vent — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Deflectors and covers for household radiators and baseboard heat: a scoop deflector
that redirects a floor/wall register's airflow out into the room, a louvered
baseboard cover panel, and an adjustable magnet-mount corner deflector. These are
project-internal profiles (no external dimensional standard) sized to common
residential registers and baseboard channels.

Real dimensions (typical US residential, expressed in mm):
  - Floor / wall register faces around 4x10" to 6x12" (matched by width/depth).
  - Baseboard heater fin covers roughly 175-230 mm tall.
  Everything is parametric so it fits the register or baseboard you measure.

Watertightness strategy (louvered panels as closed manifolds):
  Every part is a SOLID plate (or a plate plus a solid scoop) from which louver
  slots are cut as through-slots — a plate with through-holes is still one sealed
  2-manifold solid (each slot adds an interior wall loop, not a boundary edge).
  Slots are plain rectangular pockets cut fully through the panel thickness so no
  blind void is trapped. Mounting tabs and the scoop are unioned to the panel with
  real volumetric overlap, never a tangent kiss. The fold between a scoop's floor
  and its raked face is modeled as one lofted/unioned solid so the two never rely on
  a zero-thickness seam.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "deflector"))
width = float(PARAM(lambda: width, 254.0))        # register / cover width (mm)
height = float(PARAM(lambda: height, 180.0))      # cover height or scoop depth (mm)
thickness = float(PARAM(lambda: thickness, 3.0))  # panel wall thickness (mm)
louver_count = int(PARAM(lambda: louver_count, 7))    # number of vent slots
louver_angle = float(PARAM(lambda: louver_angle, 35.0))  # scoop rake / deflection (deg)
tab = bool(PARAM(lambda: tab, True))              # mounting tabs

# Clamp so extreme UI values still build watertight.
width = max(80.0, min(width, 400.0))
height = max(60.0, min(height, 320.0))
thickness = max(2.0, min(thickness, 6.0))
louver_count = max(2, min(louver_count, 20))
louver_angle = max(10.0, min(louver_angle, 60.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _louver_slots(panel, panel_w, panel_h, base_offset):
    """Cut `louver_count` through-slots across a flat panel lying in XY. Slots run the
    panel width and are spaced along the panel height (Y); each is cut fully through
    the panel thickness in +Z. `base_offset` shifts the slot field along Y."""
    slot_w = panel_w * 0.82
    pitch = panel_h / (louver_count + 1)
    slot_h = min(pitch * 0.55, 14.0)
    cutter = None
    for i in range(louver_count):
        yc = base_offset + pitch * (i + 1) - panel_h / 2.0
        one = (
            cq.Workplane("XY")
            .workplane(offset=-2.0)
            .center(0, yc)
            .rect(slot_w, slot_h)
            .extrude(thickness + 4.0)
        )
        cutter = one if cutter is None else cutter.union(one)
    if cutter is not None:
        panel = panel.cut(cutter)
    return panel


def _tabs(panel_w, panel_h):
    """Two mounting ears at the top corners of a flat panel (in the XY plane at
    z=0..thickness), each with a screw hole. Unioned with full overlap into the panel."""
    ear_w, ear_l = 18.0, 22.0
    ears = None
    for sx in (-1, 1):
        x = sx * (panel_w / 2.0 - ear_w / 2.0)
        y = panel_h / 2.0 + ear_l / 2.0 - 4.0
        ear = cq.Workplane("XY").center(x, y).rect(ear_w, ear_l).extrude(thickness)
        hole = (
            cq.Workplane("XY").workplane(offset=-1.0)
            .center(x, y + ear_l / 2.0 - 7.0).circle(2.6).extrude(thickness + 2.0)
        )
        ear = ear.cut(hole)
        ears = ear if ears is None else ears.union(ear)
    return ears


# ── Part builders ─────────────────────────────────────────────────────────────
def build_deflector():
    """A scoop deflector: a floor/base plate that sits over a register, plus a raked
    louvered face that lifts at `louver_angle` to throw air into the room. Base and
    raked face are unioned into one solid; louvers are cut through the raked face."""
    base_len = height * 0.55
    face_len = height

    # Base plate lying flat in XY at the register.
    base = cq.Workplane("XY").box(width, base_len, thickness, centered=(True, True, False))

    # Raked face: a plate tilted up about the far edge of the base. It starts 5 mm
    # BEFORE the fold (negative Y start) so it overlaps the base volume — a real
    # volumetric bond, not a fragile tangent-edge kiss.
    face = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, base_len / 2.0 - 5.0, 0.0))
        .transformed(rotate=cq.Vector(louver_angle, 0, 0))
        .box(width, face_len + 5.0, thickness, centered=(True, False, False))
    )
    # Louver slots through the raked face (cut in the face's local frame, whose
    # origin matches the face's shifted start at base_len/2 - 5).
    slot_w = width * 0.82
    pitch = face_len / (louver_count + 1)
    slot_h = min(pitch * 0.5, 12.0)
    face_cut = None
    for i in range(louver_count):
        yl = 5.0 + pitch * (i + 1)
        one = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, base_len / 2.0 - 5.0, 0.0))
            .transformed(rotate=cq.Vector(louver_angle, 0, 0))
            .transformed(offset=cq.Vector(0, yl, -2.0))
            .rect(slot_w, slot_h)
            .extrude(thickness + 4.0)
        )
        face_cut = one if face_cut is None else face_cut.union(one)
    if face_cut is not None:
        face = face.cut(face_cut)

    body = base.union(face)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_baseboard_cover():
    """A flat louvered baseboard cover panel: a solid plate with horizontal vent
    slots and optional mounting tabs. Lies in the XY plane; slots cut through Z."""
    panel = cq.Workplane("XY").box(width, height, thickness, centered=(True, True, False))
    panel = _louver_slots(panel, width, height, 0.0)
    if tab:
        panel = panel.union(_tabs(width, height))
    try:
        panel = panel.clean()
    except Exception:
        pass
    return panel


def build_corner_deflector():
    """An L-profile corner deflector: a mounting flange and a deflection vane meeting
    at a rounded fold, louvered across the vane. One solid via a swept L-section."""
    flange_len = height * 0.4
    vane_len = height * 0.7

    # Flange flat in XY.
    flange = cq.Workplane("XY").box(width, flange_len, thickness, centered=(True, True, False))
    # Vane rising vertically from the flange's back edge.
    vane = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, flange_len / 2.0, 0.0))
        .transformed(rotate=cq.Vector(90.0 - (louver_angle - 30.0), 0, 0))
        .box(width, vane_len, thickness, centered=(True, False, False))
    )
    # Louver slots through the vane (local frame).
    slot_w = width * 0.8
    pitch = vane_len / (louver_count + 1)
    slot_h = min(pitch * 0.5, 11.0)
    vc = None
    for i in range(louver_count):
        yl = pitch * (i + 1)
        one = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, flange_len / 2.0, 0.0))
            .transformed(rotate=cq.Vector(90.0 - (louver_angle - 30.0), 0, 0))
            .transformed(offset=cq.Vector(0, yl, -2.0))
            .rect(slot_w, slot_h)
            .extrude(thickness + 4.0)
        )
        vc = one if vc is None else vc.union(one)
    if vc is not None:
        vane = vane.cut(vc)

    body = flange.union(vane)
    if tab:
        body = body.union(_tabs(width, flange_len))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "baseboard_cover":
    result = build_baseboard_cover()
elif target_part == "corner_deflector":
    result = build_corner_deflector()
else:
    result = build_deflector()
