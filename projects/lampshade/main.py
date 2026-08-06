"""
Lampshade — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A patterned lampshade or pendant: a thin conical/cylindrical shell with a bulb-socket
ring at the top (sized to an E26/E27 lamp holder) and a perforated pattern that casts
light. Dial top/bottom diameter, height, wall, socket standard, and pattern density.

Three parts (dispatched via `target_part`):
  * "drum_shade" — a straight cylindrical drum shade (top dia == bottom dia).
  * "cone_shade" — a tapered empire/cone shade (top dia < bottom dia).
  * "pendant"    — a downlight pendant: a deeper cone that flares toward an open bottom,
                   with a smaller socket ring for a hanging cord-set.

Performance: the shell is an annular extrude/loft (boolean-free). The pattern is cut in a
SINGLE boolean using a compound of all hole cutters (per-hole cuts are far too slow), so
even a dense pattern renders in a few seconds and exports watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `top_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "drum_shade"))  # drum_shade|cone_shade|pendant
socket      = str(PARAM(lambda: socket,      "E27"))         # E26|E27
pattern     = str(PARAM(lambda: pattern,     "holes"))       # holes|slots|solid

top_dia    = float(PARAM(lambda: top_dia,   140.0))   # top opening diameter (mm)
bottom_dia = float(PARAM(lambda: bottom_dia, 180.0))  # bottom opening diameter (mm)
height     = float(PARAM(lambda: height,    150.0))   # shade height (mm)
wall       = float(PARAM(lambda: wall,        2.0))   # shell wall thickness (mm)
pat_rows   = int(  PARAM(lambda: pat_rows,      3))   # pattern rows up the height
pat_cols   = int(  PARAM(lambda: pat_cols,     14))   # pattern columns around
pat_size   = float(PARAM(lambda: pat_size,    9.0))   # pattern feature size (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
top_dia    = max(40.0, min(top_dia, 300.0))
bottom_dia = max(40.0, min(bottom_dia, 320.0))
height     = max(50.0, min(height, 300.0))
wall       = max(1.2, min(wall, 5.0))
pat_rows   = max(0, min(pat_rows, 8))
pat_cols   = max(4, min(pat_cols, 36))
pat_size   = max(3.0, min(pat_size, 24.0))

# Socket ring inner diameter (E26/E27 holders are ~ Ø40 mm collar; ring bore ~28–30 mm).
SOCKET_BORE = 29.5 if socket == "E27" else 28.5      # E27 slightly larger than E26
RING_OD = 46.0                                        # ring outer diameter (fits holder)
RING_H = 8.0                                          # ring band height


# ── Shell (thin conical B-rep: circle-loft outer minus circle-loft inner) ────
def _shell(td, bd, h):
    """A thin conical shell from bottom diameter bd to top diameter td over height h.
    Built as a circle-loft SOLID cone with a slightly-smaller circle-loft cone cut out.
    Lofting full circles gives a clean conical B-rep surface — unlike a polyline-annulus
    loft — so later pattern booleans stay watertight. Returns the open shell solid."""
    outer = (
        cq.Workplane("XY").circle(bd / 2.0)
        .workplane(offset=h).circle(td / 2.0)
    ).loft(combine=True)
    inner = (
        cq.Workplane("XY").circle(max(1.0, bd / 2.0 - wall))
        .workplane(offset=h).circle(max(1.0, td / 2.0 - wall))
    ).loft(combine=True).translate((0, 0, -1.0))
    return outer.cut(inner)


def _socket_ring(z_top):
    """A cross-bar socket ring hub at the top opening: a small ring bored to `SOCKET_BORE`
    held by three spokes reaching to the shell top. Sits just below the top rim."""
    ring = cq.Workplane("XY").circle(RING_OD / 2.0).circle(SOCKET_BORE / 2.0).extrude(RING_H)
    ring = ring.translate((0, 0, z_top - RING_H))
    # Three spokes from the ring OD out to the shell top inner radius.
    reach = top_dia / 2.0 - wall
    hub = ring
    for k in range(3):
        a = math.radians(120.0 * k)
        spoke = (
            cq.Workplane("XY")
            .box(reach, 5.0, RING_H, centered=(False, True, False))
            .rotate((0, 0, 0), (0, 0, 1), math.degrees(a))
            .translate((0, 0, z_top - RING_H))
        )
        hub = hub.union(spoke)
    try:
        hub = hub.clean()
    except Exception:
        pass
    return hub


# ── Pattern (single compound cut — fast) ─────────────────────────────────────
def _pattern_cutter(td, bd, h):
    """A COMPOUND of all pattern cutters, so the shell is perforated in ONE boolean.
    Cutters are long radial cylinders/boxes placed on a rows×cols lattice and pointed
    through the wall. Returns a cq.Compound or None if pattern is 'solid'."""
    if pattern == "solid" or pat_rows <= 0:
        return None
    # Cap the total cutter count so even the densest UI request renders in a few seconds
    # (the tapered-shell boolean cost scales with cutter count).
    rows = pat_rows
    cols = pat_cols
    while rows * cols > 48:
        if cols > rows:
            cols -= 1
        else:
            rows -= 1
    solids = []
    for r in range(rows):
        frac = (r + 1.0) / (rows + 1.0)
        z = frac * h
        # local radius at this height (linear taper) for correct pointing depth
        for c in range(cols):
            a = 2.0 * math.pi * c / cols + (r % 2) * (math.pi / cols)
            if pattern == "slots":
                cutter = (
                    cq.Workplane("XZ").slot2D(pat_size * 1.8, pat_size * 0.55, 90)
                    .extrude(max(td, bd))
                )
            else:  # holes
                cutter = cq.Workplane("XZ").circle(pat_size / 2.0).extrude(max(td, bd))
            cutter = cutter.rotate((0, 0, 0), (0, 0, 1), math.degrees(a)).translate((0, 0, z))
            solids.append(cutter.val())
    if not solids:
        return None
    return cq.Compound.makeCompound(solids)


# ── Part builders ─────────────────────────────────────────────────────────────
def _build_shade(td, bd, h, small_ring=False):
    shell = _shell(td, bd, h)
    cutter = _pattern_cutter(td, bd, h)
    if cutter is not None:
        shell = shell.cut(cutter)
    if small_ring:
        ring = cq.Workplane("XY").circle(19.0).circle(11.0).extrude(RING_H).translate((0, 0, h - RING_H))
        reach = td / 2.0 - wall
        hub = ring
        for k in range(3):
            a = math.radians(120.0 * k)
            spoke = (
                cq.Workplane("XY").box(reach, 4.0, RING_H, centered=(False, True, False))
                .rotate((0, 0, 0), (0, 0, 1), math.degrees(a)).translate((0, 0, h - RING_H))
            )
            hub = hub.union(spoke)
        body = shell.union(hub)
    else:
        body = shell.union(_socket_ring(h))
    return body


def build_drum_shade():
    """A straight drum: top and bottom diameters equalised to the top diameter."""
    d = top_dia
    return _build_shade(d, d, height)


def build_cone_shade():
    """A tapered empire cone: top smaller than bottom (uses both diameters)."""
    td = min(top_dia, bottom_dia)
    bd = max(top_dia, bottom_dia)
    return _build_shade(td, bd, height)


def build_pendant():
    """A downlight pendant: a deeper flare with a small cord-set ring instead of a full
    lamp-holder ring."""
    td = min(top_dia, bottom_dia) * 0.7
    bd = max(top_dia, bottom_dia)
    return _build_shade(td, bd, height, small_ring=True)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cone_shade":
    result = build_cone_shade()
elif target_part == "pendant":
    result = build_pendant()
else:
    result = build_drum_shade()
