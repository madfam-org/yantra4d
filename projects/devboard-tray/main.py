"""
Dev-Board Tray — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A mounting tray that carries a microcontroller / SBC dev board on printed
standoffs whose positions match the board's real mounting-hole pattern. Pick the
board and the tray drops the standoffs on the correct hole coordinates so the
board bolts (or press-fits) down; the plate then mounts to a wall, a project box,
or a DIN rail.

Modes are dispatched via `target_part`:
  * "tray"      — standoffs on a flat plate with corner mount holes.
  * "din_tray"  — the tray with a DIN-rail clip foot on the underside.
  * "wall_tray" — the tray with two keyhole wall-mount slots.

Board hole patterns (centre-to-centre, mm) are the published form-factor specs:
  Uno/Leonardo, Mega/Due, Nano, ESP32-DevKitC, Raspberry Pi Pico.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `board`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Board table ──────────────────────────────────────────────────────────────
# holes : list of (x, y) mounting-hole centres relative to the board centre (mm).
# outline : (w, d) board outline for the plate size.
# bore  : mounting-hole diameter on the board (drives the standoff bore).
# Coordinates are the published Arduino/Pi-family form-factor hole patterns.
def _rect_holes(dx, dy):
    return [(-dx / 2.0, -dy / 2.0), (dx / 2.0, -dy / 2.0),
            (dx / 2.0, dy / 2.0), (-dx / 2.0, dy / 2.0)]


_BOARDS = {
    # Arduino Uno/Leonardo: the classic 4-hole pattern (asymmetric), outline 68.6 x 53.4.
    "uno": {
        "outline": (68.6, 53.4), "bore": 3.2,
        "holes": [(-24.4, -20.3), (28.9, -15.2), (28.9, 22.9), (-24.4, 22.9)],
    },
    # Arduino Mega/Due: extended board, outline 101.6 x 53.3.
    "mega": {
        "outline": (101.6, 53.3), "bore": 3.2,
        "holes": [(-40.9, -20.3), (45.5, -15.2), (45.5, 22.9), (-40.9, 22.9),
                  (5.1, 22.9), (5.1, -20.3)],
    },
    # Arduino Nano: two holes on the long edges, outline 43.2 x 17.8.
    "nano": {
        "outline": (43.2, 17.8), "bore": 1.8,
        "holes": _rect_holes(38.1, 12.7),
    },
    # ESP32-DevKitC: 4 corner holes, outline ~52 x 28, 3.2 mm holes at 48.3 x 24.1.
    "esp32-devkit": {
        "outline": (55.0, 28.0), "bore": 3.2,
        "holes": _rect_holes(48.3, 24.1),
    },
    # Raspberry Pi Pico: 2 holes on the centreline pair, outline 51 x 21, 47 x 11.4.
    "pi-pico": {
        "outline": (51.0, 21.0), "bore": 2.1,
        "holes": _rect_holes(47.0, 11.4),
    },
}


def board_spec(key):
    k = str(key).strip().lower().replace(" ", "")
    return _BOARDS.get(k, _BOARDS["uno"])


# ── Parameters ───────────────────────────────────────────────────────────────
board       = str(  PARAM(lambda: board,     "uno"))    # uno|mega|nano|esp32-devkit|pi-pico
standoff_h  = float(PARAM(lambda: standoff_h,  6.0))    # standoff pillar height
boss_d      = float(PARAM(lambda: boss_d,      6.0))    # standoff outer diameter
plate_t     = float(PARAM(lambda: plate_t,     3.0))    # tray plate thickness
margin      = float(PARAM(lambda: margin,      5.0))    # plate border past the outline
mount_bore  = float(PARAM(lambda: mount_bore,  4.3))    # corner wall-mount bore (M4)

target_part = str(PARAM(lambda: target_part, "tray"))   # tray|din_tray|wall_tray

# ── Derived ──────────────────────────────────────────────────────────────────
spec = board_spec(board)
outline_w, outline_d = spec["outline"]
board_bore = spec["bore"]
holes = spec["holes"]

standoff_h = max(2.0, min(standoff_h, 25.0))
boss_d = max(board_bore + 2.0, min(boss_d, 12.0))
plate_t = max(2.0, min(plate_t, 8.0))
margin = max(3.0, min(margin, 20.0))

plate_w = outline_w + 2.0 * margin
plate_d = outline_d + 2.0 * margin
# self-tapping bore: slightly under the board hole so a screw bites the pillar
peg_bore = max(1.4, board_bore - 0.6)

# DIN TS35 rail foot constants (DIN EN 60715) — reuse the compliant idea lightly.
RAIL_SPAN = 35.0
RAIL_DEPTH = 7.5
HOOK_WALL = 2.6
CATCH = 2.0
CLEAR = 0.35


# ── Helpers ──────────────────────────────────────────────────────────────────
def _plate(w, d, t):
    body = cq.Workplane("XY").box(w, d, t, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(3.0, w / 8.0, d / 8.0))
    except Exception:
        pass
    return body


def _standoffs(body, base_z):
    """Add a bored standoff pillar at each board hole. Built as one grouped
    extrude then one grouped bore so a dense pattern stays fast and watertight."""
    pillars = (
        cq.Workplane("XY").workplane(offset=base_z)
        .pushPoints(holes).circle(boss_d / 2.0).extrude(standoff_h)
    )
    body = body.union(pillars)
    bores = (
        cq.Workplane("XY").workplane(offset=base_z - 0.5)
        .pushPoints(holes).circle(peg_bore / 2.0).extrude(standoff_h + 1.0)
    )
    body = body.cut(bores)
    return body


def _din_foot():
    """A short DIN TS35 clip foot: a channel that hugs the rail top-hat with a
    fixed lip on each side. Kept as a rigid catch (a printed foot, not a spring)
    because the plate above provides the mass; snaps over the rail lips."""
    x_in = RAIL_SPAN / 2.0 - CLEAR
    x_wall = RAIL_SPAN / 2.0 + HOOK_WALL
    x_catch = x_in - CATCH
    length = min(plate_d * 0.7, 30.0)
    jaw_h = RAIL_DEPTH + 2.5

    def _hook(mirror):
        s = -1.0 if mirror else 1.0
        pts = [
            (s * x_catch, 0.0),
            (s * x_wall, 0.0),
            (s * x_wall, -jaw_h),
            (s * x_catch, -jaw_h),
            (s * x_catch, -jaw_h + HOOK_WALL),
            (s * x_in, -jaw_h + HOOK_WALL),
            (s * x_in, -2.0),
            (s * x_catch, -2.0),
        ]
        return (
            cq.Workplane("XZ").polyline(pts).close()
            .extrude(length / 2.0, both=True)
        )

    # A backing slab ties the two hooks and fuses to the plate underside.
    slab = cq.Workplane("XY").box(RAIL_SPAN + 2 * HOOK_WALL + 2, length, 2.0,
                                  centered=(True, True, False)).translate((0, 0, -2.0))
    foot = slab.union(_hook(False)).union(_hook(True))
    return foot


# ── Builders ─────────────────────────────────────────────────────────────────
def build_tray():
    body = _plate(plate_w, plate_d, plate_t)
    # Corner mount holes in the plate border.
    hx = plate_w / 2.0 - margin / 2.0
    hy = plate_d / 2.0 - margin / 2.0
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    mount = (
        cq.Workplane("XY").pushPoints(corners).circle(mount_bore / 2.0)
        .extrude(plate_t + 1.0).translate((0, 0, -0.5))
    )
    body = body.cut(mount)
    body = _standoffs(body, plate_t)
    return body


def build_din_tray():
    """Tray on a DIN clip foot (no corner mount holes — it hangs on the rail)."""
    body = _plate(plate_w, plate_d, plate_t)
    body = _standoffs(body, plate_t)
    foot = _din_foot()
    body = body.union(foot)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_wall_tray():
    """Tray with two keyhole slots so it hangs on a pair of wall screws."""
    body = _plate(plate_w, plate_d, plate_t)
    body = _standoffs(body, plate_t)

    # Keyholes on the +/-X border: a big entry hole above a narrow slot.
    ky = 0.0
    for sx in (-1.0, 1.0):
        cx = sx * (plate_w / 2.0 - margin / 2.0)
        big = (
            cq.Workplane("XY").transformed(offset=cq.Vector(cx, ky + 4.0, -0.5))
            .circle(4.0).extrude(plate_t + 1.0)
        )
        slot = (
            cq.Workplane("XY").transformed(offset=cq.Vector(cx, ky - 2.0, -0.5))
            .box(4.4, 12.0, plate_t + 1.0, centered=(True, True, False))
        )
        body = body.cut(big).cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "tray": build_tray,
    "din_tray": build_din_tray,
    "wall_tray": build_wall_tray,
}

result = _dispatch.get(target_part, build_tray)()
