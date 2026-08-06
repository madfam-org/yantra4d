"""
Deck Cable Gland — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A sealed cable pass-through plate for a boat deck, RV roof, or panel: cables enter
through a raised gland boss with a stepped cavity for a rubber grommet/sealant, and
the plate bolts down on a gasket. Sized by cable diameter and a rectangular bolt
pattern so it drops onto a drilled hole pattern.

Three parts (dispatched via `target_part`):
  * "gland_plate" — one-piece plate: a single sealed cable boss + corner bolt pattern.
  * "split_gland" — a two-half plate that clamps around an already-terminated cable
                    (both halves, printed side by side; a captive-cable retrofit).
  * "multi_gland" — a wider plate with a row of `cable_count` sealed cable bosses.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cable_dia`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "gland_plate"))  # gland_plate|split_gland|multi_gland

cable_dia   = float(PARAM(lambda: cable_dia,   8.0))   # cable outer diameter (mm)
plate_t     = float(PARAM(lambda: plate_t,     5.0))   # base plate thickness (mm)
boss_h      = float(PARAM(lambda: boss_h,     10.0))   # sealed boss height above the plate (mm)
seal_step   = float(PARAM(lambda: seal_step,   2.0))   # grommet counterbore depth (mm)
bolt_dia    = float(PARAM(lambda: bolt_dia,    4.0))   # deck bolt clearance dia (mm)
bolt_dx     = float(PARAM(lambda: bolt_dx,    46.0))   # bolt pattern spacing in X (mm)
bolt_dy     = float(PARAM(lambda: bolt_dy,    46.0))   # bolt pattern spacing in Y (mm)
margin      = float(PARAM(lambda: margin,      8.0))   # plate edge margin past the bolts (mm)
cable_count = int(  PARAM(lambda: cable_count,   3))   # cables in a multi_gland row

# Clamp inputs to sane ranges so extreme UI values still build watertight.
cable_dia   = max(3.0, min(cable_dia, 30.0))
plate_t     = max(3.0, min(plate_t, 12.0))
boss_h      = max(4.0, min(boss_h, 30.0))
seal_step   = max(0.5, min(seal_step, min(boss_h, plate_t) - 1.0))
bolt_dia    = max(2.5, min(bolt_dia, 10.0))
bolt_dx     = max(20.0, min(bolt_dx, 160.0))
bolt_dy     = max(20.0, min(bolt_dy, 160.0))
margin      = max(4.0, min(margin, 30.0))
cable_count = max(2, min(cable_count, 6))

boss_or = cable_dia / 2.0 + max(3.0, cable_dia * 0.4)   # boss outer radius (sealing wall)


# ── Shared plate + features ──────────────────────────────────────────────────
def _base_plate(w, d):
    """A rectangular base plate on XY, base at z=0, centred in X/Y."""
    return cq.Workplane("XY").box(w, d, plate_t, centered=(True, True, False))


def _bolt_holes(plate, dx, dy):
    """Four corner bolt clearance holes at ±dx/2, ±dy/2 through the plate."""
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            hole = (
                cq.Workplane("XY")
                .center(sx * dx / 2.0, sy * dy / 2.0)
                .circle(bolt_dia / 2.0)
                .extrude(plate_t + 2.0)
                .translate((0, 0, -1.0))
            )
            plate = plate.cut(hole)
    return plate


def _sealed_boss(cx, cy):
    """A raised sealing boss at (cx, cy): an outer cylinder rising `boss_h`, bored for
    the cable, with a top counterbore that seats a rubber grommet against a stepped
    shoulder (the grommet squeezes the cable; the shoulder stops it)."""
    boss = (
        cq.Workplane("XY")
        .center(cx, cy)
        .circle(boss_or)
        .extrude(plate_t + boss_h)
    )
    # Through cable bore.
    bore = (
        cq.Workplane("XY")
        .center(cx, cy)
        .circle(cable_dia / 2.0)
        .extrude(plate_t + boss_h + 2.0)
        .translate((0, 0, -1.0))
    )
    boss = boss.cut(bore)
    # Grommet counterbore from the top (larger than the cable, stops at a shoulder).
    cbore = (
        cq.Workplane("XY")
        .center(cx, cy)
        .circle(cable_dia / 2.0 + max(1.5, cable_dia * 0.25))
        .extrude(seal_step)
        .translate((0, 0, plate_t + boss_h - seal_step))
    )
    boss = boss.cut(cbore)
    return boss


def build_gland_plate():
    """One sealed cable boss centred on a bolt-patterned plate."""
    w = bolt_dx + 2.0 * margin
    d = bolt_dy + 2.0 * margin
    plate = _base_plate(w, d)
    plate = plate.union(_sealed_boss(0.0, 0.0))
    plate = _bolt_holes(plate, bolt_dx, bolt_dy)
    return plate


def build_split_gland():
    """A two-half gland that clamps around an already-terminated cable. Each half is the
    plate+boss cut on the cable centre plane (Y=0); the halves print side by side and
    bolt together, so a pre-wired cable can be sealed without disconnecting it."""
    w = bolt_dx + 2.0 * margin
    d = bolt_dy + 2.0 * margin
    whole = _base_plate(w, d).union(_sealed_boss(0.0, 0.0))
    whole = _bolt_holes(whole, bolt_dx, bolt_dy)
    big = plate_t + boss_h + 4.0
    # Cut into +Y and -Y halves along the cable slot plane.
    keep_pos = cq.Workplane("XY").box(w + 4.0, d + 4.0, big, centered=(True, False, False))
    keep_pos = keep_pos.translate((0, 0.0, 0))            # y >= 0
    keep_neg = cq.Workplane("XY").box(w + 4.0, d + 4.0, big, centered=(True, False, False))
    keep_neg = keep_neg.translate((0, -(d + 4.0), 0))     # y <= 0
    half_pos = whole.intersect(keep_pos).translate((0, margin * 0.8, 0))
    half_neg = whole.intersect(keep_neg).translate((0, -margin * 0.8, 0))
    return half_pos.union(half_neg)


def build_multi_gland():
    """A wider plate carrying a row of `cable_count` sealed bosses, with a bolt pattern
    stretched to span the row."""
    pitch = boss_or * 2.0 + 6.0
    row_w = pitch * (cable_count - 1)
    w = row_w + 2.0 * (boss_or + margin)
    d = bolt_dy + 2.0 * margin
    plate = _base_plate(w, d)
    x0 = -row_w / 2.0
    for i in range(cable_count):
        plate = plate.union(_sealed_boss(x0 + i * pitch, 0.0))
    # Bolt pattern spans the wider plate; keep corners inside the margin.
    dx = w - 2.0 * margin
    plate = _bolt_holes(plate, dx, bolt_dy)
    return plate


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "split_gland":
    result = build_split_gland()
elif target_part == "multi_gland":
    result = build_multi_gland()
else:
    result = build_gland_plate()
