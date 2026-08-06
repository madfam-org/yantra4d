"""
GT2 / HTD Timing Pulley — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The canonical synchronous-belt pulley for 3D printers, CNC gantries, and small
robotics. The user picks a belt standard (GT2-2mm, GT2-3mm, HTD-3M, HTD-5M) and
a tooth count; the pulley pitch diameter and outside diameter are derived from
the standard so the printed pulley meshes a real belt.

Tooth model:
  * The pulley pitch diameter is  PD = teeth * pitch / pi.
  * A synchronous belt rides on the pitch line, which sits one "pitch-line
    differential" (PLD) BELOW the tip of the pulley teeth, so the tooth-tip
    (outside) diameter is  OD = PD - 2 * PLD.
  * The belt's own teeth sit in valleys cut into the pulley rim. We approximate
    the GT2 curvilinear / HTD rounded tooth *valley* with a circular arc of
    radius `valley_r` centred on the pitch circle — a close, watertight stand-in
    for the exact involute-free profile. `teeth` valleys are cut around the rim.

Modes (dispatched via `target_part`):
  * "pulley"         — a toothed pulley with an optional set-screw hub.
  * "pulley_flanged" — same, plus retaining flanges above and below the belt.
  * "idler"          — a SMOOTH (toothless) idler wheel of the same OD, always
                       flanged, bored for a bearing rather than a shaft.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `teeth`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


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


# ── Belt-standard table ──────────────────────────────────────────────────────
# pitch  : tooth-to-tooth spacing along the belt (mm) → sets pitch diameter.
# depth  : radial depth of the tooth valley cut into the rim (mm).
# pld    : pitch-line differential — how far the pitch line sits below the tip.
# valley : radius of the circular arc approximating one tooth valley (mm).
BELT_TABLE = {
    "GT2-2mm": {"pitch": 2.0, "depth": 0.76, "pld": 0.254, "valley": 0.60},
    "GT2-3mm": {"pitch": 3.0, "depth": 1.14, "pld": 0.381, "valley": 0.90},
    "HTD-3M":  {"pitch": 3.0, "depth": 1.22, "pld": 0.381, "valley": 0.95},
    "HTD-5M":  {"pitch": 5.0, "depth": 2.06, "pld": 0.571, "valley": 1.60},
}


def belt_spec(key):
    """Look up a belt standard, tolerant of spelling / casing."""
    k = str(key).strip().upper().replace(" ", "")
    if k in ("GT2-2MM", "GT2", "2GT", "GT2-2"):
        return BELT_TABLE["GT2-2mm"]
    if k in ("GT2-3MM", "3GT", "GT2-3"):
        return BELT_TABLE["GT2-3mm"]
    if k in ("HTD-3M", "HTD3M", "3M"):
        return BELT_TABLE["HTD-3M"]
    if k in ("HTD-5M", "HTD5M", "5M"):
        return BELT_TABLE["HTD-5M"]
    return BELT_TABLE["GT2-2mm"]


# ── Parameters ───────────────────────────────────────────────────────────────
belt_type   = str(  PARAM(lambda: belt_type, "GT2-2mm"))   # belt standard
teeth       = int(  PARAM(lambda: teeth,          20))     # number of pulley teeth
width        = float(PARAM(lambda: width,          6.0))   # belt (rim) width, mm
bore         = float(PARAM(lambda: bore,           5.0))   # shaft bore diameter, mm
flanges      = bool( PARAM(lambda: flanges,       False))  # add retaining flanges
flange_h     = float(PARAM(lambda: flange_h,       1.2))   # flange thickness, mm
hub          = bool( PARAM(lambda: hub,            True))  # set-screw hub below rim
hub_dia      = float(PARAM(lambda: hub_dia,       12.0))   # hub outer diameter, mm
hub_height   = float(PARAM(lambda: hub_height,     6.0))   # hub height, mm
setscrew     = bool( PARAM(lambda: setscrew,       True))  # radial set-screw hole
setscrew_dia = float(PARAM(lambda: setscrew_dia,   3.2))   # set-screw clearance (≈ M3)
bearing_od   = float(PARAM(lambda: bearing_od,    13.0))   # idler bearing OD (623=10, 625=16)

target_part = str(  PARAM(lambda: target_part, "pulley"))  # pulley|pulley_flanged|idler


# ── Derived geometry ─────────────────────────────────────────────────────────
spec = belt_spec(belt_type)
pitch = spec["pitch"]
tooth_depth = spec["depth"]
pld = spec["pld"]
valley_r = spec["valley"]

teeth = max(8, min(int(teeth), 120))
width = max(2.0, width)

# Core synchronous-belt math.
pitch_dia = teeth * pitch / math.pi           # PD = N * p / pi
outside_dia = pitch_dia - 2.0 * pld           # tooth-tip diameter
outside_r = outside_dia / 2.0
pitch_r = pitch_dia / 2.0
# The valley-arc centres ride on the pitch circle; the root of a valley reaches
# (outside_r - tooth_depth). We keep a solid web inside the roots.
root_r = outside_r - tooth_depth

bore = max(2.0, min(bore, root_r - 2.0))       # keep a wall between bore and roots
bore_r = bore / 2.0
CLR = 0.10                                      # bore print clearance

# Flanges must clear the belt: a little larger than the OD.
flange_r = outside_r + max(1.2, pitch * 0.9)
flange_h = max(0.6, flange_h)

hub_dia = max(bore + 3.0, hub_dia)
hub_r = hub_dia / 2.0
hub_height = max(2.0, hub_height)

bearing_od = max(bore + 2.0, min(bearing_od, 2.0 * flange_r - 4.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def toothed_rim():
    """A cylinder of the pulley OD with `teeth` valley arcs cut into the rim.
    Each valley is a vertical cylinder of radius `valley_r` whose axis is placed
    on the pitch circle, so the belt tooth nests into the arc."""
    rim = cq.Workplane("XY").circle(outside_r).extrude(width)
    # Build one combined cutter of all valley pins, then subtract once.
    cutter = None
    for i in range(teeth):
        ang = 2.0 * math.pi * i / teeth
        cx = pitch_r * math.cos(ang)
        cy = pitch_r * math.sin(ang)
        pin = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, -0.5))
            .circle(valley_r)
            .extrude(width + 1.0)
        )
        cutter = pin if cutter is None else cutter.union(pin)
    if cutter is not None:
        rim = rim.cut(cutter)
    return rim


def add_flanges(body):
    """Retaining discs slightly larger than the OD, above and below the belt."""
    bottom = cq.Workplane("XY").circle(flange_r).extrude(flange_h)
    body = body.union(bottom.translate((0, 0, -flange_h)))
    top = cq.Workplane("XY").circle(flange_r).extrude(flange_h)
    body = body.union(top.translate((0, 0, width)))
    return body


def add_hub(body):
    """A cylindrical hub below the rim to carry the set screw / give grip."""
    h = cq.Workplane("XY").circle(hub_r).extrude(hub_height)
    return body.union(h.translate((0, 0, -hub_height)))


def bore_out(body, total_h, z0):
    """Through-bore for the shaft, from z0 up through total_h."""
    if bore_r <= 0.05:
        return body
    cutter = (
        cq.Workplane("XY")
        .circle(bore_r + CLR)
        .extrude(total_h + 1.0)
        .translate((0, 0, z0 - 0.5))
    )
    return body.cut(cutter)


def add_setscrew(body, z_center):
    """Radial set-screw hole through the hub wall into the bore."""
    if not setscrew:
        return body
    d = max(1.5, min(setscrew_dia, hub_dia * 0.4))
    hole = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, z_center, 0))
        .circle(d / 2.0)
        .extrude(hub_r + 0.5)     # centre outward through the +X wall
    )
    return body.cut(hole)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_pulley(with_flanges):
    body = toothed_rim()
    if with_flanges:
        body = add_flanges(body)
    z_low = 0.0
    if hub:
        body = add_hub(body)
        z_low = -hub_height
    if with_flanges:
        z_low = min(z_low, -flange_h)
    total_h = width - z_low + (flange_h if with_flanges else 0.0)
    body = bore_out(body, total_h, z_low)
    if hub:
        body = add_setscrew(body, z_center=max(2.0, hub_height * 0.5))
    return body


def build_idler():
    """A smooth (toothless) flanged idler bored for a bearing press-fit."""
    rim = cq.Workplane("XY").circle(outside_r).extrude(width)
    rim = add_flanges(rim)
    z_low = -flange_h
    total_h = width + 2.0 * flange_h
    # Bearing bore straight through (press-fit seat).
    seat_r = bearing_od / 2.0
    seat = (
        cq.Workplane("XY")
        .circle(seat_r)
        .extrude(total_h + 1.0)
        .translate((0, 0, z_low - 0.5))
    )
    return rim.cut(seat)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "idler":
    result = build_idler()
elif target_part == "pulley_flanged":
    result = build_pulley(with_flanges=True)
else:
    result = build_pulley(with_flanges=flanges)
