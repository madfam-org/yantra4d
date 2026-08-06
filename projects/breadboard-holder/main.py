"""
Breadboard Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A base that holds a solderless breadboard (or perfboard) flat and captive so it
stops sliding around the bench while you wire a circuit. A recessed pocket sized
to the standard breadboard footprint receives the board; retaining lips along the
long edges hold it down, and screw ears let the whole thing bolt to a project
base or benchtop. Variants add flanking power-rail channels (for the clip-off DC
rails) and an angled easel so the board tilts toward you.

Modes are dispatched via `target_part`:
  * "base_tray"    — flat pocket + retaining lips + corner screw ears.
  * "rail_base"    — the tray with a power-rail channel down each long side.
  * "angled_holder"— the tray carried on a wedge so the board sits at an angle.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bb_size`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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


# ── Breadboard footprint table (nominal solderless-breadboard outlines) ───────
# w, d  : board outline (mm). Standard full/half boards are 55 mm deep.
# The classic 830-point ("full+") board is ~165 x 55; the 400-point is ~83 x 55.
_BOARDS = {
    "830pt": {"w": 165.0, "d": 55.0},
    "400pt": {"w": 83.0, "d": 55.0},
    "mini":  {"w": 46.0, "d": 35.0},
}


def board_spec(key):
    k = str(key).strip().lower().replace(" ", "")
    if k in ("830pt", "830", "full", "830point"):
        return _BOARDS["830pt"]
    if k in ("400pt", "400", "half", "400point"):
        return _BOARDS["400pt"]
    if k in ("mini", "170", "170pt"):
        return _BOARDS["mini"]
    return _BOARDS["830pt"]


# ── Parameters ───────────────────────────────────────────────────────────────
bb_size    = str(  PARAM(lambda: bb_size,   "830pt"))   # 830pt | 400pt | mini
clearance  = float(PARAM(lambda: clearance,    0.4))    # per-side pocket clearance
wall       = float(PARAM(lambda: wall,         2.4))    # pocket wall thickness
floor      = float(PARAM(lambda: floor,        2.4))    # base floor thickness
lip_h      = float(PARAM(lambda: lip_h,        2.0))    # retaining-lip height over board
board_th   = float(PARAM(lambda: board_th,     9.0))    # board thickness held in the pocket
screw_ears = bool( PARAM(lambda: screw_ears,  True))    # corner bolt-down ears
ear_bore   = float(PARAM(lambda: ear_bore,     4.3))    # ear screw clearance bore (M4)
tilt_deg   = float(PARAM(lambda: tilt_deg,    15.0))    # angled_holder easel angle

target_part = str(PARAM(lambda: target_part, "base_tray"))

# ── Derived ──────────────────────────────────────────────────────────────────
spec = board_spec(bb_size)
board_w = spec["w"]
board_d = spec["d"]

clearance = max(0.1, min(clearance, 1.5))
wall = max(1.6, min(wall, 6.0))
floor = max(1.6, min(floor, 8.0))
lip_h = max(0.0, min(lip_h, board_th - 0.5))
board_th = max(4.0, min(board_th, 16.0))
tilt_deg = max(5.0, min(tilt_deg, 35.0))

pocket_w = board_w + 2.0 * clearance
pocket_d = board_d + 2.0 * clearance
outer_w = pocket_w + 2.0 * wall
outer_d = pocket_d + 2.0 * wall
pocket_depth = min(board_th, board_th)          # pocket as deep as the board is thick
wall_h = floor + pocket_depth                   # top of the surrounding wall

RAIL_W = 6.5     # power-rail channel width (a clip-off DC rail sits in this)
RAIL_GAP = 1.0   # gap between pocket wall and rail channel


# ── Helpers ──────────────────────────────────────────────────────────────────
def _rounded_block(w, d, h, r):
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


def _pocket_body(ow, od):
    """Solid outer block (ow x od) with the board pocket cut from the top and the
    two long-edge retaining lips left standing."""
    r = min(3.0, wall)
    body = _rounded_block(ow, od, wall_h, r)

    # Main pocket: full board footprint, cut from the floor up to the rim.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor))
        .box(pocket_w, pocket_d, pocket_depth + 1.0, centered=(True, True, False))
    )
    body = body.cut(pocket)

    # Retaining lips overhang the pocket on the two SHORT ends (±X) so the board
    # slides in from a long side and is captured top-down. Cut a slot in the rim
    # over the long sides so wires/jumpers exit freely.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor + pocket_depth - lip_h))
        .box(pocket_w - 2.0 * 6.0, pocket_d + 2.0 * wall + 2.0, lip_h + 1.0,
             centered=(True, True, False))
    )
    if lip_h > 0.05:
        body = body.cut(slot)
    return body


def _screw_ears(body, ow, od):
    """Add four corner ears with clearance bores for bolting the tray down."""
    if not screw_ears:
        return body
    ear = max(9.0, ear_bore * 2.4)
    hx = ow / 2.0 + ear / 2.0 - 1.0
    hy = od / 2.0 - ear / 2.0
    pts = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    tab = (
        cq.Workplane("XY").pushPoints(pts).circle(ear / 2.0).extrude(floor)
    )
    body = body.union(tab)
    bore = (
        cq.Workplane("XY").pushPoints(pts).circle(ear_bore / 2.0)
        .extrude(floor + 1.0).translate((0, 0, -0.5))
    )
    body = body.cut(bore)
    return body


def build_base_tray():
    body = _pocket_body(outer_w, outer_d)
    body = _screw_ears(body, outer_w, outer_d)
    return body


def build_rail_base():
    """Tray widened so a power-rail channel runs along each long (+/-Y) side. A
    clip-off DC power rail (or a strip of perfboard) seats in each channel."""
    ow = outer_w + 2.0 * (RAIL_W + RAIL_GAP)
    od = outer_d
    body = _pocket_body(ow, od)

    # Channels: shallow open troughs along +Y and -Y just outside the pocket wall.
    ch_y = pocket_d / 2.0 + wall + RAIL_GAP + RAIL_W / 2.0
    for sign in (-1.0, 1.0):
        trough = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sign * ch_y, floor))
            .box(pocket_w, RAIL_W, pocket_depth + 1.0, centered=(True, True, False))
        )
        body = body.cut(trough)
    body = _screw_ears(body, ow, od)
    return body


def build_angled_holder():
    """An easel: a solid triangular wedge whose sloped top face carries the board
    pocket, so the board sits tilted toward the user. Built as ONE solid — the
    wedge — with the pocket and lip slot cut directly into the tilted top face
    (cutters placed on a workplane rotated by `tilt_deg`). No fragile union of two
    solids touching on a slanted seam, so it exports watertight."""
    import math

    a = math.radians(tilt_deg)
    ow, od = outer_w, outer_d
    front_y = -od / 2.0
    back_rise = od * math.sin(a) + floor + 1.0   # back is higher by the tilt rise

    # Wedge prism (triangular in the Y-Z plane, extruded across X).
    wedge_pts = [
        (front_y, 0.0),
        (front_y + od, 0.0),
        (front_y + od, back_rise),
        (front_y, floor + 1.0),
    ]
    body = (
        cq.Workplane("YZ")
        .polyline(wedge_pts).close()
        .extrude(ow).translate((-ow / 2.0, 0, 0))
    )

    # Local frame on the sloped top face: origin at the front-top edge, rotated
    # by tilt about X so +Y' runs up the slope and +Z' is the face normal.
    slope = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, front_y, floor + 1.0))
        .transformed(rotate=cq.Vector(tilt_deg, 0, 0))
    )
    # Pocket cut into the slope (measured from the front edge, up the slope).
    pocket = (
        slope.transformed(offset=cq.Vector(0, od / 2.0, 0))
        .box(pocket_w, pocket_d, pocket_depth, centered=(True, True, True))
    )
    body = body.cut(pocket)

    # Lip slot across the rim over the long sides (same as the flat tray).
    if lip_h > 0.05:
        slot = (
            slope.transformed(offset=cq.Vector(0, od / 2.0, pocket_depth / 2.0 - lip_h / 2.0))
            .box(pocket_w - 12.0, pocket_d + 2.0 * wall + 2.0, lip_h + 1.0,
                 centered=(True, True, True))
        )
        body = body.cut(slot)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "base_tray": build_base_tray,
    "rail_base": build_rail_base,
    "angled_holder": build_angled_holder,
}

result = _dispatch.get(target_part, build_base_tray)()
