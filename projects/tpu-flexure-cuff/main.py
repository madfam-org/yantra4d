"""TPU Flexure Cuff — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A print-in-place flexible CUFF band — the additive-manufacturing trim the Fashion
Cabinet `printed-flexure-cuff` notion describes and bridges to here for its geometry.
A cylindrical band, printed thin in TPU and perforated by a staggered lattice of
through-slots (a rolled-up living hinge), flexes open to pass over the hand or ankle
and springs back to grip the wrist — a sleeve/hem finish with no separate elastic.

This is the soft-goods↔hard-goods seam made physical: the cuff is simultaneously a
Fashion Cabinet fashion trim (cuff circumference to the wrist, height) and a Yantra4D
solid (the printable flexure band). One material identity spans both — `bambu-tpu-95a`.

Modes (dispatched via `target_part`):
  * "cuff"   — the full flexure band (circumference x height), print-in-place.
  * "swatch" — a short arc sample for a print/flex test.
  * "band"   — a plain (un-slotted) band, to compare stiffness.

The band is a hollow cylinder (outer minus inner) with vertical slots box-cut through
the wall, each leaving a land at top and bottom so the ring never splits — the living
hinge that lets it stretch.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cuff_circum`).
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
cuff_circum = float(PARAM(lambda: cuff_circum, 180.0))  # relaxed inner circumference (mm)
cuff_height = float(PARAM(lambda: cuff_height, 60.0))   # band height along the limb (mm)
wall        = float(PARAM(lambda: wall,        2.0))    # band wall thickness (mm)
slot_rows   = int(  PARAM(lambda: slot_rows,   3))      # rows of flexure slots up the band
slot_cols   = int(  PARAM(lambda: slot_cols,   16))     # slots around the band per row
slot_w      = float(PARAM(lambda: slot_w,      2.0))    # slot width around the band (mm)

target_part = str(  PARAM(lambda: target_part, "cuff"))  # cuff|swatch|band

# ── Safe clamps ──────────────────────────────────────────────────────────────
cuff_circum = max(80.0, min(cuff_circum, 500.0))
cuff_height = max(15.0, min(cuff_height, 200.0))
wall        = max(1.0, min(wall, 6.0))
slot_rows   = max(1, min(slot_rows, 8))
slot_cols   = max(4, min(slot_cols, 48))
slot_w      = max(0.8, min(slot_w, 6.0))

r_in  = cuff_circum / (2.0 * math.pi)
r_out = r_in + wall


def _band(arc_deg=360.0):
    """A hollow cylindrical band spanning `arc_deg` of arc, height cuff_height."""
    outer = (
        cq.Workplane("XY")
        .circle(r_out)
        .extrude(cuff_height)
    )
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(r_in)
        .extrude(cuff_height + 2.0)
    )
    ring = outer.cut(inner)
    if arc_deg < 359.9:
        # Trim to an arc with a big wedge cut (keep the +X-ish sector).
        half = math.radians(arc_deg) / 2.0
        big = r_out + 10.0
        keep = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .moveTo(0, 0)
            .lineTo(big * math.cos(-half), big * math.sin(-half))
            .lineTo(big * math.cos(half), big * math.sin(half))
            .close()
            .extrude(cuff_height + 2.0)
        )
        # A 3-point wedge only covers <180°; for the swatch arc that's fine.
        ring = ring.intersect(keep)
    return ring


def _slot(angle_rad, z_center, height):
    """One vertical through-slot in the wall at `angle_rad`, centred at z_center,
    `height` tall and slot_w wide around the band. Cut radially through the wall."""
    # A thin box straddling the wall at this angle. Local frame: box long axis = Z,
    # width = slot_w (tangential), depth pierces the wall (radial).
    depth = wall + 4.0
    box = (
        cq.Workplane("XY")
        .box(depth, slot_w, height)                 # X=radial, Y=tangential, Z=up
        .translate((r_in + wall / 2.0, 0, 0))       # move out to the wall
        .rotate((0, 0, 0), (0, 0, 1), math.degrees(angle_rad))
        .translate((0, 0, z_center))
    )
    return box


def build_cuff(arc_deg=360.0, cols=None):
    """The flexure band: a hollow cylinder with a staggered lattice of vertical
    through-slots. Slots leave a land at top and bottom of each row so the ring stays
    one watertight solid; alternate rows offset by half a slot so the ligaments
    stagger like a rolled living hinge."""
    cols = slot_cols if cols is None else cols
    body = _band(arc_deg)

    # Vertical extent available for slots, with a solid land top and bottom.
    land = max(2.0, cuff_height * 0.12)
    usable = cuff_height - 2.0 * land
    row_h = usable / slot_rows
    slot_h = row_h * 0.7                      # gap between rows = the flexing ligament

    span_rad = math.radians(arc_deg)
    for r in range(slot_rows):
        z_c = land + row_h * (r + 0.5)
        offset = (span_rad / cols / 2.0) if (r % 2) else 0.0
        for c in range(cols):
            ang = -span_rad / 2.0 + (c + 0.5) * (span_rad / cols) + offset
            if arc_deg > 359.9:
                ang = c * (2.0 * math.pi / cols) + offset
            body = body.cut(_slot(ang, z_c, slot_h))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "band":
    result = _band(360.0)
elif target_part == "swatch":
    result = build_cuff(arc_deg=120.0, cols=max(2, slot_cols // 3))
else:
    result = build_cuff(360.0)
