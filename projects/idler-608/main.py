"""
608 Bearing Idler Pulley — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An idler pulley that presses onto a standard 608 skate bearing (22 mm OD ×
8 mm ID × 7 mm) and rides on an M8 shoulder bolt. The bearing carries the load;
the printed pulley is only the running surface + flanges that keep a belt, round
cord, or filament tracking. The FUNCTIONAL interface is the 22 mm press-fit seat
(socket) plus the 8 mm bore, so any 608 drops in and the idler bolts to any 8 mm
axle — the same seat the linear-wheel and bearing-housing cartridges expose.

Bearing table (metric deep-groove, ID × OD × width):
  608  → 8 × 22 × 7   (default, skateboard/printer idler)
  623  → 3 × 10 × 4     625 → 5 × 16 × 5     6900 → 10 × 22 × 6

Modes (dispatched via `target_part`):
  * "flat_idler"   — a smooth cylindrical running surface with two end flanges
                     to guide a flat belt / filament; 608 seat bored through.
  * "round_idler"  — a central V / round groove for a round drive belt or bungee
                     cord; the 608 seat carries it on the M8 axle.
  * "washer_stack" — the mounting hardware: a shoulder spacer + two retaining
                     flange washers that sandwich the 608 on the bolt (no seat).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>) — no globals()/eval/getattr.
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


# ── Bearing table (ID, OD, width in mm) ──────────────────────────────────────
BEARING_TABLE = {
    "608":  {"id": 8.0,  "od": 22.0, "w": 7.0},
    "623":  {"id": 3.0,  "od": 10.0, "w": 4.0},
    "625":  {"id": 5.0,  "od": 16.0, "w": 5.0},
    "6900": {"id": 10.0, "od": 22.0, "w": 6.0},
}


def bearing_spec(key):
    k = str(key).strip().lower().replace("bearing", "").replace(" ", "")
    return BEARING_TABLE.get(k, BEARING_TABLE["608"])


# ── Parameters ───────────────────────────────────────────────────────────────
bearing     = str(  PARAM(lambda: bearing,     "608"))    # bearing designation
od          = float(PARAM(lambda: od,           30.0))    # pulley running-surface diameter (mm)
width       = float(PARAM(lambda: width,        10.0))    # pulley axial width (mm)
flange_h    = float(PARAM(lambda: flange_h,      2.5))    # guide-flange rim height over the OD (mm)
flange_t    = float(PARAM(lambda: flange_t,      2.0))    # flange thickness (mm)
groove_dia  = float(PARAM(lambda: groove_dia,    5.0))    # round-groove belt/cord diameter (mm)
press_fit   = float(PARAM(lambda: press_fit,     0.0))    # seat interference(−)/clearance(+) mm

target_part = str(PARAM(lambda: target_part, "flat_idler"))  # flat_idler|round_idler|washer_stack


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = bearing_spec(bearing)
b_id, b_od, b_w = spec["id"], spec["od"], spec["w"]

seat_r = b_od / 2.0 + press_fit / 2.0     # press_fit<0 tightens the seat
bore_r = b_id / 2.0 + 0.2                 # axle clearance through the bore

width = max(b_w + 1.0, min(width, 30.0))          # must be at least as wide as the bearing
od = max(b_od + 6.0, min(od, 120.0))              # running surface clears seat + wall
flange_h = max(0.0, min(flange_h, 12.0))
flange_t = max(1.2, min(flange_t, 6.0))
groove_dia = max(2.0, min(groove_dia, od * 0.4))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _seat_and_bore(body):
    """Bore the 608 press-fit seat (22 mm) most of the way through and leave an
    8 mm axle bore all the way through, forming an internal shoulder that stops
    the bearing central. Seat is cut from BOTH faces so the bearing can seat
    from either side and there is no trapped void."""
    # Axle bore all the way through (open both faces).
    axle = cq.Workplane("XY").circle(bore_r).extrude(width + 2.0).translate((0, 0, -1.0))
    body = body.cut(axle)
    # Seat pocket bored from the top face down by the bearing width.
    seat_top = (
        cq.Workplane("XY")
        .circle(seat_r)
        .extrude(-(b_w + 0.01))
        .translate((0, 0, width + 0.005))
    )
    body = body.cut(seat_top)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_flat_idler():
    """Smooth cylindrical running surface with two guide flanges. The 608 seats
    from the top; the belt runs on the barrel between the flanges."""
    # Central barrel (running surface).
    body = cq.Workplane("XY").circle(od / 2.0).extrude(width)
    # Two end flanges standing proud of the barrel to keep the belt tracking.
    if flange_h > 0.05:
        fr = od / 2.0 + flange_h
        bot = cq.Workplane("XY").circle(fr).extrude(flange_t)
        top = cq.Workplane("XY").circle(fr).extrude(flange_t).translate((0, 0, width - flange_t))
        body = body.union(bot).union(top)
    body = _seat_and_bore(body)
    return body


def build_round_idler():
    """Running surface with a central V / round groove for a round drive belt or
    bungee cord. The groove is a torus-section cut ringed at mid-height."""
    body = cq.Workplane("XY").circle(od / 2.0).extrude(width)
    # Round groove: revolve a circle around the axis by cutting a torus.
    groove_r = od / 2.0                          # groove sits at the rim
    torus = (
        cq.Workplane("XZ")
        .center(groove_r, width / 2.0)
        .circle(groove_dia / 2.0)
        .revolve(360, (-groove_r, 0), (-groove_r, 1))
    )
    body = body.cut(torus)
    body = _seat_and_bore(body)
    return body


def build_washer_stack():
    """Mounting hardware: a shoulder spacer sleeve (fits the 8 mm bore, sets the
    idler standoff) capped by two retaining flange washers that sandwich the 608
    on the M8 bolt. Modelled as one printed part: spacer tube + one integral
    flange (the second washer prints as the mirrored copy)."""
    axle_r = b_id / 2.0 + 0.3
    sleeve_r = axle_r + 1.6
    flange_r = b_od / 2.0 - 1.0                 # overlaps the bearing inner race only
    sleeve_h = b_w + 2.0                        # spans the bearing + a little proud
    # Shoulder sleeve.
    body = cq.Workplane("XY").circle(sleeve_r).extrude(sleeve_h)
    # Integral retaining flange at the base (washer that presses the inner race).
    flange = cq.Workplane("XY").circle(flange_r).extrude(flange_t)
    body = body.union(flange)
    # Bore for the M8 bolt all the way through.
    bolt = cq.Workplane("XY").circle(axle_r).extrude(sleeve_h + 2.0).translate((0, 0, -1.0))
    body = body.cut(bolt)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "round_idler":
    result = build_round_idler()
elif target_part == "washer_stack":
    result = build_washer_stack()
else:
    result = build_flat_idler()
