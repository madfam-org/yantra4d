"""
DIN Rail Relay Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Holds cube relays / solid-state relays (SSRs) on standard top-hat DIN rail
(TS35, DIN EN 60715 — 35 mm across the lips, 7.5 mm deep). Cradle a plug-in cube
relay, cap the terminals with a finger-safe guard, or mount an SSR against a
finned dissipation plate — pick the style and set the relay body size. Grows the
`din-rail-35` family.

DIN TS35 rail (DIN EN 60715, dimensionally real):
  - rail span across the two rolled lips = 35.0 mm
  - top-hat stand-off depth              = 7.5 mm
  - rolled-lip turn-back (hook grip)     ~ 5.0 mm

Watertight strategy:
  The clip back is a mount plate with two hooks, each an XZ profile extruded
  symmetrically about Y=0 and UNIONED with overlap into the plate. Cradle walls,
  guard shroud and fins are unioned overlapping solids. The relay cavity opens UP
  to a face (vented — no trapped void); wire/terminal windows and vent slots are
  through-cuts. Fillet clean blanks BEFORE feature cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>).
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


# ── DIN TS35 rail (DIN EN 60715) — fixed real geometry ───────────────────────
RAIL_SPAN = 35.0     # width across the two rolled lips
RAIL_DEPTH = 7.5     # top-hat stand-off depth
LIP_GRIP = 5.0       # rolled-lip turn-back (hook grip depth)


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "socket_cradle"))
# "socket_cradle" | "finger_guard" | "ssr_heatsink"

relay_w = float(PARAM(lambda: relay_w, 28.0))       # relay body width (X)
relay_l = float(PARAM(lambda: relay_l, 28.0))       # relay body length (Y, along rail)
relay_h = float(PARAM(lambda: relay_h, 32.0))       # relay body height (Z)
wall = float(PARAM(lambda: wall, 2.6))              # cradle / guard wall thickness
fin_count = int(PARAM(lambda: fin_count, 6))        # heat-sink fin count
fin_h = float(PARAM(lambda: fin_h, 16.0))           # fin height
plate_th = float(PARAM(lambda: plate_th, 4.0))      # mount-plate thickness
vent_w = float(PARAM(lambda: vent_w, 3.0))          # ventilation slot width

# Clamp to sane ranges so extreme UI values never crash the kernel.
relay_w = max(12.0, min(relay_w, 80.0))
relay_l = max(12.0, min(relay_l, 80.0))
relay_h = max(10.0, min(relay_h, 80.0))
wall = max(1.8, min(wall, 6.0))
fin_count = max(2, min(fin_count, 20))
fin_h = max(6.0, min(fin_h, 40.0))
plate_th = max(2.5, min(plate_th, 10.0))
vent_w = max(1.5, min(vent_w, 8.0))

# ── Derived clip geometry ────────────────────────────────────────────────────
JAW_H = RAIL_DEPTH + 2.5
HOOK_WALL = 2.6
CATCH = max(1.5, min(LIP_GRIP - 1.0, 3.0))
CLEAR = 0.35


# ── DIN clip back (self-contained; copy of the din-module idiom) ─────────────
def _extrude_profile_xz(pts, length):
    """Close (x, z) points on XZ and extrude symmetrically about Y=0."""
    return cq.Workplane("XZ").polyline(pts).close().extrude(length / 2.0, both=True)


def _mount_plate(width, length):
    plate = cq.Workplane("XY").box(width, length, plate_th, centered=(True, True, False))
    try:
        plate = plate.edges("|Z").fillet(min(3.0, width / 6.0))
    except Exception:
        pass
    return plate


def _fixed_hook(length):
    """Rigid hook on the +X side (fixed reference jaw)."""
    x_in = RAIL_SPAN / 2.0 - CLEAR
    x_wall = RAIL_SPAN / 2.0 + HOOK_WALL
    x_catch = x_in - CATCH
    pts = [
        (x_catch, plate_th), (x_wall, plate_th),
        (x_wall, -JAW_H), (x_catch, -JAW_H),
        (x_catch, -JAW_H + HOOK_WALL), (x_in, -JAW_H + HOOK_WALL),
        (x_in, 0.0), (x_catch, 0.0),
    ]
    return _extrude_profile_xz(pts, length)


def _spring_hook(length):
    """COMPLIANT sprung hook on the -X side."""
    t = 2.0
    x_lip = -RAIL_SPAN / 2.0
    x_out = x_lip - CLEAR
    x_root_in = x_lip + 7.0
    x_catch = x_out + CATCH
    outer = [
        (x_root_in, plate_th), (x_out, plate_th),
        (x_out, -JAW_H), (x_catch, -JAW_H),
    ]
    inner = [
        (x_catch, -JAW_H + t), (x_out + t, -JAW_H + t),
        (x_out + t, plate_th - t - 3.0), (x_root_in, plate_th - t - 3.0),
    ]
    beam = _extrude_profile_xz(outer + inner, length)
    relief = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x_root_in, 0.0, plate_th - 1.0))
        .box(2.0, length + 2.0, 2.2, centered=(True, True, True))
    )
    try:
        beam = beam.cut(relief)
    except Exception:
        pass
    return beam


def _clip_back(width, length):
    """Mount plate + fixed hook + spring hook, welded into one body."""
    body = _mount_plate(width, length)
    body = body.union(_fixed_hook(length))
    body = body.union(_spring_hook(length))
    return body


def _base_len():
    """Clip length along the rail — at least the relay length plus walls."""
    return max(24.0, relay_l + 2.0 * wall)


# ── Part builders ────────────────────────────────────────────────────────────
def build_socket_cradle():
    """A walled cradle that captures a plug-in cube relay: four walls above the
    DIN clip forming a pocket the relay drops into (open at top → vented), with a
    wire-access window in the front wall. One welded body, no trapped voids."""
    length = _base_len()
    body = _clip_back(max(RAIL_SPAN + 8.0, relay_w + 2.0 * wall), length)

    cav_w = relay_w + 1.0
    cav_l = relay_l + 1.0
    outer_w = cav_w + 2.0 * wall
    outer_l = cav_l + 2.0 * wall
    wall_h = relay_h * 0.7

    cradle = (
        cq.Workplane("XY").workplane(offset=plate_th - 0.01)
        .box(outer_w, min(outer_l, length), wall_h, centered=(True, True, False))
    )
    body = body.union(cradle)

    # Hollow the pocket, open at the top (vents), floor stays solid (the plate).
    pocket = (
        cq.Workplane("XY").workplane(offset=plate_th + 1.0)
        .box(cav_w, cav_l, wall_h, centered=(True, True, False))
    )
    body = body.cut(pocket)

    # Front wire-access window through the +X wall (vents).
    win = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, plate_th + wall_h * 0.45, outer_w / 2.0 + 1.0))
        .rect(cav_l * 0.6, wall_h * 0.5)
        .extrude(-outer_w - 2.0)
    )
    body = body.cut(win)
    return body


def build_finger_guard():
    """A relay cradle capped by a finger-safe GUARD: a low shroud roof over the
    terminal end with louvre slots so a probe can't touch live terminals but wires
    still exit. Roof + walls are welded solids; louvres are through-slots."""
    length = _base_len()
    body = _clip_back(max(RAIL_SPAN + 8.0, relay_w + 2.0 * wall), length)

    cav_w = relay_w + 1.0
    outer_w = cav_w + 2.0 * wall
    wall_h = relay_h * 0.55

    # Two side walls + a roof forming a covered channel over the relay top.
    walls = (
        cq.Workplane("XY").workplane(offset=plate_th - 0.01)
        .box(outer_w, min(relay_l + 2.0 * wall, length), wall_h + wall,
             centered=(True, True, False))
    )
    body = body.union(walls)
    # Hollow under the roof (open to the sides via louvres; open at the bottom to
    # the plate face is fine — it vents through the louvres, no sealed void).
    cavity = (
        cq.Workplane("XY").workplane(offset=plate_th + 1.0)
        .box(cav_w, min(relay_l, length) - 1.0, wall_h,
             centered=(True, True, False))
    )
    body = body.cut(cavity)

    # Louvre slots through the roof (finger-safe venting, run along X).
    n = max(3, int(min(relay_l, length) / (vent_w + 2.0)))
    span = min(relay_l, length) - 4.0
    for i in range(n):
        y = -span / 2.0 + (span / max(1, n - 1)) * i
        louvre = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, plate_th + wall_h - 0.5))
            .box(cav_w * 0.8, vent_w, wall + 2.0, centered=(True, True, False))
        )
        body = body.cut(louvre)
    return body


def build_ssr_heatsink():
    """An SSR mount: a backing plate above the DIN clip that the SSR bolts flat
    against, backed by a row of `fin_count` cooling fins for dissipation. Fins are
    solid plates welded to the back with overlap; two SSR bolt slots vent through
    the plate."""
    length = _base_len()
    body = _clip_back(max(RAIL_SPAN + 8.0, relay_w + 2.0 * wall), length)

    plate_w = relay_w + 2.0 * wall
    face_h = relay_h * 0.9
    # Vertical SSR face plate standing up in +Z, welded to the clip with overlap.
    face = (
        cq.Workplane("XY").workplane(offset=plate_th - 0.01)
        .box(plate_w, wall * 1.6, face_h, centered=(True, True, False))
    )
    body = body.union(face)

    # Cooling fins projecting back (-Y) from the face, evenly spread along X.
    fin_t = 1.6
    span = plate_w - 4.0
    for i in range(fin_count):
        x = -span / 2.0 + (span / max(1, fin_count - 1)) * i
        fin = (
            cq.Workplane("XY").workplane(offset=plate_th - 0.01)
            .transformed(offset=cq.Vector(x, -wall * 0.8 - fin_h / 2.0 + 0.5, 0))
            .box(fin_t, fin_h, face_h, centered=(True, True, False))
        )
        body = body.union(fin)

    # Two SSR mounting bolt slots through the face plate (vent front-to-back).
    for sz in (0.30, 0.70):
        slot = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0, plate_th + face_h * sz, wall * 1.2))
            .slot2D(plate_w * 0.5, 4.5, angle=0)
            .extrude(-wall * 3.0)
        )
        body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "finger_guard":
    result = build_finger_guard()
elif target_part == "ssr_heatsink":
    result = build_ssr_heatsink()
else:
    result = build_socket_cradle()
