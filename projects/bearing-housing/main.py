"""
Bearing Housing / Pillow Block — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Seats a standard deep-groove ball bearing in a printed housing with a press-fit
bore and a shoulder (lip) so the bearing seats to a positive stop. The user picks
a bearing by its designation; the seat bore, seat depth, and shaft clearance are
taken from the bearing table so the printed part fits a real bearing.

Bearing table (metric deep-groove, ID × OD × width):
  608  → 8 × 22 × 7      623  → 3 × 10 × 4      625  → 5 × 16 × 5
  6900 → 10 × 22 × 6     6902 → 15 × 28 × 7

Modes (dispatched via `target_part`):
  * "pillow_block"  — a raised block; the bearing axis is horizontal and the
                      block is bolted DOWN through side feet (bolts parallel to
                      the mounting surface / through the base ears).
  * "flange_mount"  — a flat plate; the bearing axis is normal to the plate and
                      the housing bolts to a face through holes around the seat.
  * "insert"        — just the press-fit ring (a bearing carrier with the seat +
                      shoulder), to embed in another part.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Bearing table (ID, OD, width in mm) ──────────────────────────────────────
BEARING_TABLE = {
    "608":  {"id": 8.0,  "od": 22.0, "w": 7.0},
    "623":  {"id": 3.0,  "od": 10.0, "w": 4.0},
    "625":  {"id": 5.0,  "od": 16.0, "w": 5.0},
    "6900": {"id": 10.0, "od": 22.0, "w": 6.0},
    "6902": {"id": 15.0, "od": 28.0, "w": 7.0},
}


def bearing_spec(key):
    k = str(key).strip().lower().replace("bearing", "").replace(" ", "")
    return BEARING_TABLE.get(k, BEARING_TABLE["608"])


# ── Parameters ───────────────────────────────────────────────────────────────
bearing      = str(  PARAM(lambda: bearing,     "608"))    # bearing designation
mount_style  = str(  PARAM(lambda: mount_style, "raised")) # "raised" | "flush"
wall         = float(PARAM(lambda: wall,          4.0))    # wall around the bearing OD
back_wall    = float(PARAM(lambda: back_wall,     2.0))    # shoulder/lip thickness (the stop)
mount_holes  = int(  PARAM(lambda: mount_holes,     4))    # 2 or 4 mounting bolts
bolt_dia     = float(PARAM(lambda: bolt_dia,      4.5))    # mounting bolt clearance (≈ M4)
press_fit    = float(PARAM(lambda: press_fit,     0.0))    # seat interference (−) / clearance (+), mm
riser        = float(PARAM(lambda: riser,        10.0))    # pillow-block raise height, mm

target_part = str(  PARAM(lambda: target_part, "pillow_block"))  # pillow_block|flange_mount|insert


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = bearing_spec(bearing)
b_id, b_od, b_w = spec["id"], spec["od"], spec["w"]

wall = max(2.0, wall)
back_wall = max(1.2, back_wall)
seat_r = b_od / 2.0 + press_fit / 2.0        # press_fit<0 tightens the seat
shaft_clear_r = b_id / 2.0 + 1.0             # bore through the back for the shaft
bolt_dia = max(2.0, bolt_dia)
mount_holes = 4 if int(mount_holes) >= 4 else 2

body_r = seat_r + wall                         # cylindrical housing radius
body_h = b_w + back_wall                        # seat depth + shoulder
plate_side = 2.0 * (seat_r + wall + bolt_dia + 2.0)  # square flange footprint


# ── Helpers ──────────────────────────────────────────────────────────────────
def bearing_pocket(depth_from_top, z_top):
    """A cylindrical pocket (the press-fit seat) cut down from z_top by depth."""
    return (
        cq.Workplane("XY")
        .circle(seat_r)
        .extrude(depth_from_top + 0.01)
        .translate((0, 0, z_top - depth_from_top))
    )


def shaft_bore(total_h, z0):
    """Through-bore for the shaft (smaller than the seat → forms the shoulder)."""
    return (
        cq.Workplane("XY")
        .circle(shaft_clear_r)
        .extrude(total_h + 1.0)
        .translate((0, 0, z0 - 0.5))
    )


def bolt_points_square(side):
    inset = bolt_dia + 2.0
    h = side / 2.0 - inset
    if h <= 0:
        return []
    if mount_holes == 2:
        return [(-h, 0.0), (h, 0.0)]
    return [(-h, -h), (h, -h), (h, h), (-h, h)]


def drill(body, points, dia, total_h, z0):
    r = dia / 2.0
    if r <= 0.05 or not points:
        return body
    cutter = (
        cq.Workplane("XY")
        .pushPoints(points)
        .circle(r)
        .extrude(total_h + 1.0)
        .translate((0, 0, z0 - 0.5))
    )
    return body.cut(cutter)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_insert():
    """Just the press-fit carrier ring: seat pocket + shoulder + shaft bore."""
    body = cq.Workplane("XY").circle(body_r).extrude(body_h)
    # Seat opens at the TOP; shoulder is the back_wall slab at the bottom.
    body = body.cut(bearing_pocket(b_w, z_top=body_h))
    body = body.cut(shaft_bore(body_h, 0.0))
    return body


def build_flange_mount():
    """A flat square plate; bearing axis normal to the plate. Seat opens on the
    top face, shoulder at the bottom, mounting bolts around the seat."""
    plate = cq.Workplane("XY").box(
        plate_side, plate_side, body_h, centered=(True, True, False)
    )
    try:
        plate = plate.edges("|Z").fillet(min(bolt_dia, plate_side / 2.0 - 0.5))
    except Exception:
        pass
    plate = plate.cut(bearing_pocket(b_w, z_top=body_h))
    plate = plate.cut(shaft_bore(body_h, 0.0))
    plate = drill(plate, bolt_points_square(plate_side), bolt_dia, body_h, 0.0)
    return plate


def build_pillow_block():
    """A raised block: a base slab with mounting ears, a pedestal, and a
    cylindrical boss holding the bearing with its axis HORIZONTAL (along Y)."""
    base_len = plate_side + 2.0 * (bolt_dia + 2.0)
    base_w = 2.0 * body_r + 4.0
    base_h = max(3.0, back_wall + 1.0)
    boss_axis_z = riser + body_r          # centre height of the bearing axis

    # Base plate with rounded corners.
    base = cq.Workplane("XY").box(base_len, base_w, base_h, centered=(True, True, False))
    try:
        base = base.edges("|Z").fillet(min(bolt_dia, base_w / 2.0 - 0.5))
    except Exception:
        pass

    # Pedestal risers up to the boss centre (two side walls merged into a block).
    ped = cq.Workplane("XY").box(
        2.0 * body_r, base_w, boss_axis_z, centered=(True, True, False)
    )
    body = base.union(ped)

    # Horizontal cylindrical boss along Y through the pedestal at boss_axis_z.
    boss = (
        cq.Workplane("XZ")
        .workplane(offset=-base_w / 2.0)
        .circle(body_r)
        .extrude(base_w)
        .translate((0, 0, boss_axis_z))
    )
    body = body.union(boss)

    # Seat pocket bored in from the +Y face; shoulder left at depth b_w.
    seat = (
        cq.Workplane("XZ")
        .workplane(offset=base_w / 2.0)
        .circle(seat_r)
        .extrude(-b_w)
        .translate((0, 0, boss_axis_z))
    )
    body = body.cut(seat)
    # Shaft bore all the way through along Y.
    bore = (
        cq.Workplane("XZ")
        .workplane(offset=-base_w / 2.0 - 0.5)
        .circle(shaft_clear_r)
        .extrude(base_w + 1.0)
        .translate((0, 0, boss_axis_z))
    )
    body = body.cut(bore)

    # Mounting bolts DOWN through the base ears (vertical holes).
    ear_x = base_len / 2.0 - (bolt_dia + 2.0)
    ear_y = base_w / 2.0 - (bolt_dia + 2.0)
    if mount_holes == 2:
        pts = [(-ear_x, 0.0), (ear_x, 0.0)]
    else:
        pts = [(-ear_x, -ear_y), (ear_x, -ear_y), (ear_x, ear_y), (-ear_x, ear_y)]
    body = drill(body, pts, bolt_dia, base_h, 0.0)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "insert":
    result = build_insert()
elif target_part == "flange_mount":
    result = build_flange_mount()
else:
    # mount_style "flush" collapses the pillow-block riser to a low profile.
    if mount_style == "flush":
        riser = min(riser, 2.0)
    result = build_pillow_block()
