"""
Whiteboard / Marker Tray — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A whiteboard marker tray / eraser holder parametric on the dry-erase marker body
diameter, with optional magnet pockets so it mounts to a steel board. Three
distinct forms dispatched by `target_part`:

  * "marker_tray"   — a horizontal rail trough that holds several markers lying
                      down, with half-round cradle scallops in the floor so they
                      do not roll, and optional magnet pockets on the back face.
  * "eraser_holder" — a block with a rectangular pocket sized for a whiteboard
                      eraser plus a couple of upright marker bores; magnet pockets
                      on the back face for mounting.
  * "marker_cup"    — an upright cup with a row of vertical bores that hold
                      markers tip-up, on a back plate with magnet pockets.

Every pocket / bore opens to a face (upward for the trough and bores, to the BACK
face for the magnet pockets) so the model is always a single watertight solid
with no trapped internal cavity.

Reference dimensions (why the defaults are what they are):
  - A standard chisel-tip dry-erase marker (e.g. Expo) has a ~16 mm body; a
    fine-tip is ~12 mm and a jumbo is ~22 mm. `marker_dia` defaults to 16 mm.
  - Magnet pockets default to 10 mm x 2 mm — a common disc magnet size.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `marker_dia`).
  - Read them via PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
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
marker_dia = float(PARAM(lambda: marker_dia, 16.0))   # dry-erase marker body Ø (mm) — Expo chisel ~16
markers    = int(  PARAM(lambda: markers,       4))   # number of marker positions
clearance  = float(PARAM(lambda: clearance,   1.5))   # gap around each marker (mm)
wall       = float(PARAM(lambda: wall,        4.0))   # wall / floor thickness (mm)
tray_h     = float(PARAM(lambda: tray_h,     28.0))   # trough / cup height (mm)
magnets    = int(  PARAM(lambda: magnets,       2))   # magnet pockets on the back (0 = none)
magnet_dia = float(PARAM(lambda: magnet_dia, 10.0))   # magnet disc Ø (mm)
magnet_t   = float(PARAM(lambda: magnet_t,    2.0))   # magnet disc thickness / pocket depth (mm)
eraser_w   = float(PARAM(lambda: eraser_w,   58.0))   # eraser pocket width (eraser_holder, mm)
eraser_d   = float(PARAM(lambda: eraser_d,   32.0))   # eraser pocket depth front-to-back (mm)

target_part = str(PARAM(lambda: target_part, "marker_tray"))  # marker_tray | eraser_holder | marker_cup

# ── Clamps / derived values ──────────────────────────────────────────────────
marker_dia = max(6.0, min(marker_dia, 40.0))
markers    = max(1, min(markers, 12))
clearance  = max(0.4, min(clearance, 5.0))
wall       = max(2.5, min(wall, 10.0))
tray_h     = max(16.0, min(tray_h, 120.0))
magnets    = max(0, min(magnets, 6))
magnet_dia = max(4.0, min(magnet_dia, 30.0))
magnet_t   = max(1.0, min(magnet_t, 6.0))
eraser_w   = max(30.0, min(eraser_w, 140.0))
eraser_d   = max(20.0, min(eraser_d, 90.0))

bore_dia = marker_dia + clearance
pitch    = bore_dia + wall


# ── Helpers ──────────────────────────────────────────────────────────────────
def _box(w, d, h, x=0.0, y=0.0, z=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(True, True, False))
    )


def _cyl_z(dia, h, x, y, z):
    """Vertical cylinder (axis +Z), base at z."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .circle(dia / 2.0)
        .extrude(h)
    )


def add_magnet_pockets(body, back_y, span_x, z_center):
    """Cut `magnets` blind disc pockets into the BACK face (at y = back_y, facing
    -Y). Opening to the back face means each is open to a surface — never a
    trapped void. `span_x` is the usable width to space them across."""
    if magnets <= 0:
        return body
    n = magnets
    if n == 1:
        xs = [0.0]
    else:
        gap = span_x / n
        xs = [-span_x / 2.0 + (i + 0.5) * gap for i in range(n)]
    for xc in xs:
        # A cylinder whose axis runs along Y, seated so it opens out of the back
        # face and reaches `magnet_t` into the material.
        pocket = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(xc, z_center, -back_y - 0.02))
            .circle(magnet_dia / 2.0)
            .extrude(magnet_t + 0.02)
        )
        body = body.cut(pocket)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_marker_tray():
    """Horizontal rail trough: a solid bar with an upward-open channel and
    half-round cradle scallops in the floor so markers do not roll."""
    length = markers * pitch + wall
    tray_d = marker_dia + 2.0 * wall            # front-to-back depth of the bar
    body = _box(length, tray_d, tray_h)
    # Fillet the vertical corners BEFORE cutting the channel.
    try:
        body = body.edges("|Z").fillet(min(wall * 1.2, tray_d / 5.0))
    except Exception:
        pass
    # Upward-open channel: a rectangular pocket cut from the top, leaving a floor
    # of `wall` and a front/back lip of `wall`.
    ch_w = length - 2.0 * wall
    ch_d = tray_d - 2.0 * wall
    channel = _box(ch_w, ch_d, tray_h, z=wall)
    body = body.cut(channel)
    # Cradle scallops: a horizontal half-cylinder (axis along X) cut into the
    # channel floor at each marker position so markers nest and don't roll.
    # The row of markers runs along X; each marker lies across the tray depth
    # (its length along Y). At each X station cut a half-round trough running
    # along Y into the channel floor, so the marker nests in it and won't roll.
    floor_z = wall
    scallop_r = bore_dia / 2.0
    for i in range(markers):
        xc = -length / 2.0 + wall + (i + 0.5) * pitch
        scallop = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, floor_z + scallop_r * 0.35, -ch_d / 2.0 - 1.0))
            .circle(scallop_r)
            .extrude(ch_d + 2.0)
            .translate((xc, 0, 0))
        )
        body = body.cut(scallop)
    # Magnet pockets on the back face.
    body = add_magnet_pockets(body, tray_d / 2.0, length - 2.0 * wall, tray_h * 0.5)
    return body


def build_eraser_holder():
    """A block with a rectangular eraser pocket (upward-open) plus a couple of
    upright marker bores, and magnet pockets on the back face."""
    n_bores = min(markers, 3)
    block_w = max(eraser_w + 2.0 * wall, n_bores * pitch + wall)
    block_d = eraser_d + bore_dia + 3.0 * wall
    block_h = tray_h
    body = _box(block_w, block_d, block_h)
    try:
        body = body.edges("|Z").fillet(min(wall * 1.2, block_w / 8.0, block_d / 8.0))
    except Exception:
        pass
    # Eraser pocket: an upward-open rectangular pocket toward the back.
    er_y = block_d / 2.0 - eraser_d / 2.0 - wall
    eraser_pocket = _box(eraser_w, eraser_d, block_h, y=er_y, z=wall)
    body = body.cut(eraser_pocket)
    # Marker bores at the front, upward-open.
    bore_y = -block_d / 2.0 + bore_dia / 2.0 + wall
    x0 = -(n_bores - 1) * pitch / 2.0
    for i in range(n_bores):
        bore = _cyl_z(bore_dia, block_h, x0 + i * pitch, bore_y, wall)
        body = body.cut(bore)
    # Magnet pockets on the back face.
    body = add_magnet_pockets(body, block_d / 2.0, block_w - 2.0 * wall, block_h * 0.5)
    return body


def build_marker_cup():
    """An upright cup: a solid block with a row of vertical marker bores (open
    upward), on a back plate that carries magnet pockets."""
    length = markers * pitch + wall
    cup_d = marker_dia + 2.0 * wall
    body = _box(length, cup_d, tray_h)
    try:
        body = body.edges("|Z").fillet(min(wall * 1.2, cup_d / 5.0))
    except Exception:
        pass
    # Vertical bores, one per marker, blind (leave a floor of `wall`), open upward.
    x0 = -length / 2.0 + wall + pitch / 2.0
    for i in range(markers):
        bore = _cyl_z(bore_dia, tray_h, x0 + i * pitch, 0.0, wall)
        body = body.cut(bore)
    # A thin back plate rising above the cup to carry magnets (unioned solid).
    plate_h = tray_h + marker_dia * 0.4
    plate = _box(length, wall, plate_h, y=-cup_d / 2.0 + wall / 2.0)
    body = body.union(plate)
    # Magnet pockets on the back face of the plate.
    body = add_magnet_pockets(body, cup_d / 2.0, length - 2.0 * wall, plate_h * 0.6)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "eraser_holder":
    result = build_eraser_holder()
elif target_part == "marker_cup":
    result = build_marker_cup()
else:
    result = build_marker_tray()
