"""Twist-Lock Closure — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The classic handbag twist lock: an oval turn-piece that rotates a quarter turn to trap
the flap, a backplate with a matching oval keeper slot that is riveted through the flap,
and a washer that spreads the load on the reverse of the leather. This is the rigid hard
good the Fashion Cabinet `twist-lock-closure` notion places and bridges to here for its
geometry — satchels, messenger flaps and portfolio cases all set one.

Modes (dispatched via `target_part`):
  * "turn_lock" — the body plate with the pivot boss and the oval turn-piece on it.
  * "backplate" — the flap-side plate with the oval keeper slot and rivet bores.
  * "washer"    — the flat spreader washer for the reverse of the leather.
  * "set"       — all three laid out on one plate as separate bodies.

Geometry: every plate is a rounded slab; the turn-piece is a rounded slab on a stepped
pivot boss (a two-diameter revolve — never a cylinder plus a sphere cap); the keeper slot
is a swept oval cut clean through both faces; rivet bores are one pushPoints cutThruAll.
No fillet or chamfer follows any complex cut.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `plate_l`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
plate_l    = float(PARAM(lambda: plate_l,    34.0))  # plate length across the bag (mm)
plate_w    = float(PARAM(lambda: plate_w,    22.0))  # plate width up the bag (mm)
plate_t    = float(PARAM(lambda: plate_t,     3.0))  # plate thickness (mm)
turn_l     = float(PARAM(lambda: turn_l,     24.0))  # turn-piece long axis (mm)
turn_w     = float(PARAM(lambda: turn_w,      8.0))  # turn-piece short axis (mm)
turn_t     = float(PARAM(lambda: turn_t,      3.2))  # turn-piece thickness (mm)
pivot_dia  = float(PARAM(lambda: pivot_dia,   5.0))  # pivot boss / bore diameter (mm)
leather_t  = float(PARAM(lambda: leather_t,   3.0))  # flap leather thickness the lock spans (mm)
rivet_dia  = float(PARAM(lambda: rivet_dia,   3.0))  # rivet bore diameter (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # turn_lock|backplate|washer|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
# Commercial twist locks run roughly 25-45 mm across the plate; anything smaller is a
# purse catch, anything larger is luggage furniture.
plate_l   = max(20.0, min(plate_l, 60.0))
plate_w   = max(14.0, min(plate_w, 45.0))
plate_t   = max(1.8, min(plate_t, 6.0))
turn_t    = max(1.8, min(turn_t, 6.0))
# The turn-piece must clear the keeper slot but stay inside the plate footprint.
turn_l    = max(10.0, min(turn_l, plate_l - 4.0))
turn_w    = max(4.0, min(turn_w, min(turn_l - 3.0, plate_w - 5.0)))
pivot_dia = max(2.5, min(pivot_dia, turn_w - 1.5))
leather_t = max(0.8, min(leather_t, 8.0))
rivet_dia = max(1.5, min(rivet_dia, 5.0))

# ── Derived geometry ─────────────────────────────────────────────────────────
plate_r = min(plate_w * 0.3, plate_l * 0.2)     # plate corner radius
slot_clear = 0.5                                # keeper slot clearance around the turn-piece
slot_l = turn_l + slot_clear
slot_w = turn_w + slot_clear
# Rivet bores sit outboard of the slot on the plate's long axis, with real wall around.
rivet_x = min(plate_l / 2.0 - rivet_dia / 2.0 - 1.6, slot_l / 2.0 + rivet_dia / 2.0 + 1.6)
# Pivot post: tall enough to span the leather plus the turn-piece plus a peen allowance.
post_h = leather_t + turn_t + 1.2
washer_od = min(plate_l * 0.7, plate_w * 1.1)
washer_t = max(1.0, plate_t * 0.6)


def _oval(length, width):
    """A stadium (obround) outline sketch on the current workplane."""
    r = width / 2.0
    straight = max(0.01, length - width)
    return (
        cq.Workplane("XY")
        .moveTo(-straight / 2.0, r)
        .lineTo(straight / 2.0, r)
        .radiusArc((straight / 2.0, -r), r)
        .lineTo(-straight / 2.0, -r)
        .radiusArc((-straight / 2.0, r), r)
        .close()
    )


def _rounded_plate(length, width, thick, rad):
    """A rounded-rectangle plate sitting on Z=0."""
    r = max(0.3, min(rad, min(length, width) / 2.0 - 0.2))
    wp = cq.Workplane("XY").rect(length, width).extrude(thick)
    try:
        wp = wp.edges("|Z").fillet(r)
    except Exception:
        pass
    return wp


def _rivet_points():
    """Rivet-bore centres on the plate long axis, one on each side of the slot."""
    return [(-rivet_x, 0.0), (rivet_x, 0.0)]


def _cut_rivets(solid, thick):
    """Cut both rivet bores clean through in one operation; cutter overshoots both faces."""
    cutter = (
        cq.Workplane("XY")
        .pushPoints(_rivet_points())
        .circle(rivet_dia / 2.0)
        .extrude(thick + 4.0)
        .translate((0, 0, -2.0))
    )
    return solid.cut(cutter)


def _pivot_post():
    """The stepped pivot post: a shouldered revolve, flat-topped (no pole singularity)."""
    r = pivot_dia / 2.0
    head_r = r + 0.9
    prof = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(r, 0)
        .lineTo(r, post_h - 1.0)
        .lineTo(head_r, post_h - 0.4)
        .lineTo(head_r * 0.7, post_h)
        .lineTo(0, post_h)
        .close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
    )
    return prof


def build_turn_lock():
    """Body plate + pivot post + the oval turn-piece riding on it.

    Printed as one piece: the turn-piece is fused to the post so the whole assembly is a
    single watertight solid. Snap it free at the shoulder groove after printing (see docs)
    or print `turn_lock` and `backplate` and pin them with a 2 mm rod instead.
    """
    plate = _rounded_plate(plate_l, plate_w, plate_t, plate_r)
    plate = _cut_rivets(plate, plate_t)

    # Post rises from the plate top; sink it 0.5 mm into the plate so the union overlaps.
    # _pivot_post already stands upright: revolving an XZ profile about (0,1,0) puts the
    # solid's axis on +Z, so no extra rotate is needed (a rotate here tips it sideways
    # and the turn-piece then floats free — a real bug caught in verification).
    post = _pivot_post()
    body = plate.union(post.translate((0, 0, plate_t - 0.5)))

    # Turn-piece: an oval slab at the top of the post, overlapping it by 0.4 mm.
    z0 = plate_t + leather_t
    turn = (
        _oval(turn_l, turn_w)
        .extrude(turn_t)
        .translate((0, 0, z0))
    )
    try:
        turn = turn.edges("|Z").fillet(min(turn_w * 0.2, 1.0))
    except Exception:
        pass
    # A short collar bridging the post into the turn-piece — real overlap, not a touch.
    collar = (
        cq.Workplane("XY")
        .circle(pivot_dia / 2.0 + 0.3)
        .extrude(turn_t + 1.2)
        .translate((0, 0, z0 - 0.8))
    )
    return body.union(collar).union(turn)


def build_backplate():
    """Flap-side plate: the oval keeper slot cut clean through, plus rivet bores."""
    plate = _rounded_plate(plate_l, plate_w, plate_t, plate_r)
    slot = (
        _oval(slot_l, slot_w)
        .extrude(plate_t + 4.0)
        .translate((0, 0, -2.0))
    )
    plate = plate.cut(slot)
    return _cut_rivets(plate, plate_t)


def build_washer():
    """Flat spreader washer for the reverse of the leather: bore plus rivet bores."""
    washer = (
        cq.Workplane("XY")
        .circle(washer_od / 2.0)
        .extrude(washer_t)
    )
    bore = (
        cq.Workplane("XY")
        .circle(max(pivot_dia / 2.0 + 0.35, slot_w / 2.0 * 0.7))
        .extrude(washer_t + 4.0)
        .translate((0, 0, -2.0))
    )
    washer = washer.cut(bore)
    return _cut_rivets(washer, washer_t)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "turn_lock":
    result = build_turn_lock()
elif target_part == "backplate":
    result = build_backplate()
elif target_part == "washer":
    result = build_washer()
else:
    gap = max(plate_w * 0.35, 5.0)
    pitch = plate_w + gap
    asm = cq.Assembly()
    asm.add(build_turn_lock().translate((0, pitch, 0)),
            name="turn_lock", color=cq.Color("#b9922f"))
    asm.add(build_backplate(), name="backplate", color=cq.Color("#a8862b"))
    asm.add(build_washer().translate((0, -pitch, 0)),
            name="washer", color=cq.Color("#8f7526"))
    result = asm
