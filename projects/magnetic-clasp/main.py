"""Magnetic Clasp — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The two-part magnetic snap of bags, jackets, and jewellery — the rigid hard good the
Fashion Cabinet `magnetic-clasp` notion places and bridges to here for its geometry. Each
half is a disc housing with a bore for a disc magnet and sew holes around the rim; the two
halves snap together. Printed rigid (drop in the magnets) it stands in for the metal snap.

Modes (dispatched via `target_part`):
  * "set"  — both halves side by side.
  * "half" — one disc housing.

Geometry: a shallow cylinder with a central magnet bore and a ring of small sew holes.
Watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `disc_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
disc_dia   = float(PARAM(lambda: disc_dia,   18.0))  # clasp disc diameter (mm)
disc_h     = float(PARAM(lambda: disc_h,     4.0))   # disc height (mm)
magnet_dia = float(PARAM(lambda: magnet_dia, 10.0))  # magnet bore diameter (mm)
magnet_h   = float(PARAM(lambda: magnet_h,   2.0))   # magnet pocket depth (mm)
sew_holes  = int(  PARAM(lambda: sew_holes,  4))     # sew holes around the rim

target_part = str(PARAM(lambda: target_part, "set"))  # set|half

# ── Safe clamps ──────────────────────────────────────────────────────────────
disc_dia   = max(10.0, min(disc_dia, 40.0))
disc_h     = max(2.5, min(disc_h, 10.0))
magnet_dia = max(4.0, min(magnet_dia, disc_dia - 4.0))
magnet_h   = max(1.0, min(magnet_h, disc_h - 1.0))
sew_holes  = max(0, min(sew_holes, 8))


def build_half():
    """A disc with a central magnet pocket (blind bore) and a ring of sew holes."""
    disc = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, disc_h / 2.0))
        .circle(disc_dia / 2.0)
        .extrude(disc_h)
    )
    try:
        disc = disc.edges(">Z").fillet(disc_h * 0.25)
    except Exception:
        pass
    # Magnet pocket: a blind bore from the top.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, disc_h - magnet_h / 2.0 + 0.01))
        .circle(magnet_dia / 2.0)
        .extrude(magnet_h)
    )
    disc = disc.cut(pocket)
    # Sew holes around the rim (through Z).
    r = (disc_dia / 2.0 + magnet_dia / 2.0) / 2.0
    for i in range(sew_holes):
        a = 2.0 * math.pi * i / sew_holes
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(r * math.cos(a), r * math.sin(a), disc_h / 2.0))
            .circle(1.1)
            .extrude(disc_h + 2.0)
            .translate((0, 0, -1.0))
        )
        disc = disc.cut(hole)
    return disc


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "half":
    result = build_half()
else:
    gap = disc_dia * 0.4
    result = build_half().translate((-(disc_dia / 2.0 + gap / 2.0), 0, 0)).union(
        build_half().translate((disc_dia / 2.0 + gap / 2.0, 0, 0)))
