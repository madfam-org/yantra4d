"""
Spool / Bobbin Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A desk / drawer organiser for sewing-machine bobbins and thread spools. The
functional interface is the bobbin/spool BORE (the central hole a bobbin or
spool sits on) sized to real sewing standards, plus a peg the bobbin drops onto.

Real dimensions encoded (nominal):
  - Class 15 bobbin: 20.3 mm outer Ø, 11.7 mm wide, 6.1 mm centre hole.
  - L-style bobbin:  20.3 mm outer Ø, 8.9 mm wide, 6.1 mm centre hole.
  - Thread-spool core bore: ~6.5 mm; the same 6 mm peg carries both bobbins and
    small spools, so one rack holds a mixed drawer.

Modes:
  - bobbin_rack : a base plate with a row of upright pegs; each peg holds one
    bobbin/spool by its centre bore, with a shoulder so bobbins don't touch.
  - spool_pin   : a single tall angled spool pin on a weighted foot (a machine-
    top spool holder / thread stand post).
  - bobbin_tray : a shallow tray with a grid of round wells that cradle loose
    bobbins lying flat (no peg) so they can't unwind.

Watertight strategy:
  Every peg is a SOLID cylinder unioned onto the base with a small embed (no
  hollow post on a solid base → no trapped cavity). Wells in the tray are blind
  pockets bored from the OPEN top face (vent to outside). The base blank is
  fillet-cleaned BEFORE any feature cut. A dome cap on the spool pin is a
  loft-to-flat frustum (no sphere pole singularity).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default. `except Exception`
    catches the NameError raised for an unbound param (the sandbox hides
    globals()/NameError)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Bobbin / spool standards (nominal geometry, mm) ──────────────────────────
BOBBIN_STD = {
    # bore = centre hole; od = flange outer Ø; wide = flange-to-flange width.
    "class15": {"bore": 6.1, "od": 20.3, "wide": 11.7},
    "lstyle":  {"bore": 6.1, "od": 20.3, "wide": 8.9},
    "spool":   {"bore": 6.5, "od": 21.0, "wide": 20.0},  # small thread spool
}


def bobbin_geo(name):
    return BOBBIN_STD.get(name, BOBBIN_STD["class15"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "bobbin_rack"))
# "bobbin_rack" | "spool_pin" | "bobbin_tray"

bobbin_type = str(PARAM(lambda: bobbin_type, "class15"))  # bore/OD source
count       = int(PARAM(lambda: count, 6))                # pegs / wells per row
rows        = int(PARAM(lambda: rows, 1))                 # rows (tray/rack)
peg_h       = float(PARAM(lambda: peg_h, 16.0))           # peg height (mm)
peg_clear   = float(PARAM(lambda: peg_clear, 0.4))        # bore fit slop (per side)
base_th     = float(PARAM(lambda: base_th, 4.0))          # base plate thickness
pin_h       = float(PARAM(lambda: pin_h, 60.0))           # spool-pin height
pin_tilt    = float(PARAM(lambda: pin_tilt, 8.0))         # spool-pin lean (deg)

# Clamp to sane ranges so extreme UI values still build watertight.
bobbin_type = bobbin_type if bobbin_type in BOBBIN_STD else "class15"
count   = max(1, min(count, 12))
rows    = max(1, min(rows, 4))
peg_h   = max(6.0, min(peg_h, 40.0))
peg_clear = max(0.0, min(peg_clear, 1.0))
base_th = max(2.5, min(base_th, 10.0))
pin_h   = max(25.0, min(pin_h, 120.0))
pin_tilt = max(0.0, min(pin_tilt, 20.0))

_g = bobbin_geo(bobbin_type)
_peg_r = max(1.0, _g["bore"] / 2.0 - peg_clear)   # peg fits INSIDE the bore
_od = _g["od"]
_pitch = _od + 6.0                                 # centre-to-centre spacing


# ── Helpers (inlined; sandbox blocks cross-file imports) ─────────────────────
def _rounded_plate(length, width, th, fillet_r):
    """A rounded-rectangle base plate, fillet-cleaned BEFORE any feature cut."""
    plate = cq.Workplane("XY").box(length, width, th, centered=(True, True, False))
    try:
        plate = plate.edges("|Z").fillet(min(fillet_r, min(length, width) / 2.0 - 0.5))
    except Exception:
        pass
    return plate


# ── Part builders ────────────────────────────────────────────────────────────
def build_bobbin_rack():
    """A base plate with a grid (count x rows) of solid pegs; each peg carries a
    bobbin/spool by its centre bore, spaced so flanges clear each other."""
    length = _pitch * count + 8.0
    width = _pitch * rows + 8.0
    body = _rounded_plate(length, width, base_th, 4.0)

    x0 = -(_pitch * (count - 1)) / 2.0
    y0 = -(_pitch * (rows - 1)) / 2.0
    pts = [
        (x0 + c * _pitch, y0 + r * _pitch)
        for r in range(rows)
        for c in range(count)
    ]
    # Build ALL shoulders and ALL pegs as single pushPoints solids, then two
    # unions total (fast). Shoulders overlap the base; pegs embed into the base.
    shoulders = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_th))
        .pushPoints(pts)
        .circle(_peg_r + 2.0)
        .extrude(1.2)
    )
    pegs = (
        cq.Workplane("XY")
        .pushPoints(pts)
        .circle(_peg_r)
        .extrude(base_th + peg_h)
    )
    try:
        pegs = pegs.edges(">Z").chamfer(min(_peg_r * 0.4, 1.2))
    except Exception:
        pass
    body = body.union(shoulders).union(pegs)
    return body


def build_spool_pin():
    """A single tall spool pin leaning at pin_tilt on a weighted disc foot — a
    machine-top / free-standing thread post. Cap is a loft frustum (no pole)."""
    foot_r = max(18.0, _od * 1.1)
    foot_h = max(base_th, 5.0)
    foot = (
        cq.Workplane("XY").circle(foot_r).extrude(foot_h)
    )
    try:
        foot = foot.edges("|Z or >Z").fillet(2.0)
    except Exception:
        try:
            foot = foot.edges(">Z").fillet(2.0)
        except Exception:
            pass

    # The pin: a solid rod tilted about X, unioned into the foot with overlap.
    pin_r = _peg_r
    pin = (
        cq.Workplane("XY")
        .circle(pin_r)
        .extrude(pin_h)
    )
    # Flat-top cap frustum so a spool is retained without a spherical pole.
    cap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, pin_h - 1.0))
        .circle(pin_r + 1.6)
        .workplane(offset=3.0)
        .circle(pin_r * 0.6)
        .loft(combine=True)
    )
    pin = pin.union(cap)
    # Tilt the whole pin, then seat its base a little INTO the foot (overlap).
    pin = pin.rotate((0, 0, 0), (1, 0, 0), pin_tilt).translate((0, 0, foot_h - 1.0))
    body = foot.union(pin)
    return body


def build_bobbin_tray():
    """A shallow tray whose top face carries a grid of round wells; loose bobbins
    lie flat in the wells so they can't unwind. Wells are blind pockets bored
    from the open top (vented) — never trapped voids."""
    well_r = _od / 2.0 + 0.6
    well_depth = min(_g["wide"] * 0.7, base_th + 3.0)
    tray_th = well_depth + 2.5
    pitch = _od + 5.0
    length = pitch * count + 8.0
    width = pitch * rows + 8.0

    body = _rounded_plate(length, width, tray_th, 4.0)

    x0 = -(pitch * (count - 1)) / 2.0
    y0 = -(pitch * (rows - 1)) / 2.0
    pts = [
        (x0 + c * pitch, y0 + r * pitch)
        for r in range(rows)
        for c in range(count)
    ]
    # One pushPoints cut of all wells = a single boolean (cheap + watertight),
    # bored from the open top face so every well vents to outside.
    wells = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, tray_th - well_depth))
        .pushPoints(pts)
        .circle(well_r)
        .extrude(well_depth + 1.0)
    )
    body = body.cut(wells)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "spool_pin":
    result = build_spool_pin()
elif target_part == "bobbin_tray":
    result = build_bobbin_tray()
else:
    result = build_bobbin_rack()
