"""
Reed / Mouthpiece Cap — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Reed cases and mouthpiece caps for woodwinds. The functional interface is the
mouthpiece SOCKET — the cup that slides over the mouthpiece tip (with the reed
and ligature on) to protect the fragile reed tip — and the reed slot that cradles
a spare reed.

Real dimensions encoded (nominal):
  - Bb clarinet mouthpiece body ~30 mm across the beak end; bore ~14.6 mm.
  - Alto sax mouthpiece ~32-34 mm; tenor larger. The cap ID clears the
    mouthpiece + reed + ligature, so ~31-37 mm depending on instrument.
  - Reeds: clarinet ~13 mm wide, alto/tenor sax ~14 mm, length ~68-72 mm.

Modes:
  - cap        : a cup that slides over the mouthpiece tip; a cutout on one face
    clears the ligature screws, and a vent hole lets the reed dry.
  - reed_case  : a flat case body with parallel reed slots that hold spare reeds
    flat so they don't chip or warp.
  - lig_band   : a ligature band — a split ring that wraps the mouthpiece and
    presses the reed to the table, with two screw bosses to tighten.

Watertight strategy:
  The cap is a cup: a solid cylinder with a blind bore from the OPEN mouth end
  (vents to outside) — not a sealed cavity. The ligature-clearance cutout and
  vent are through-cuts. Reed slots are obround pockets bored from the open top.
  The ligature band is a split ring (open gap → not enclosed). Blanks are
  fillet-cleaned BEFORE feature cuts. No trapped voids.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` pre-injected; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Injected global if present else default; `except` catches the unbound-name
    NameError the sandbox raises (globals()/NameError are hidden)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Woodwind mouthpiece standards (nominal, mm) ──────────────────────────────
MP_STD = {
    # od = mouthpiece body outer Ø at the cap seat; reed_w = reed width.
    "clarinet": {"od": 30.0, "reed_w": 13.0},
    "alto":     {"od": 33.0, "reed_w": 14.0},
    "tenor":    {"od": 36.0, "reed_w": 14.5},
}


def mp_geo(name):
    return MP_STD.get(name, MP_STD["clarinet"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "cap"))
# "cap" | "reed_case" | "lig_band"

mp_type   = str(PARAM(lambda: mp_type, "clarinet"))   # clarinet | alto | tenor
cap_clear = float(PARAM(lambda: cap_clear, 1.2))      # cap ID clearance over the mp (per side)
cap_len   = float(PARAM(lambda: cap_len, 55.0))       # cap length (mm)
wall      = float(PARAM(lambda: wall, 2.4))           # wall thickness (mm)
reed_ct   = int(PARAM(lambda: reed_ct, 4))            # reeds the case holds
reed_len  = float(PARAM(lambda: reed_len, 70.0))      # reed slot length (mm)

# Clamp to sane ranges so extreme UI values still build watertight.
mp_type   = mp_type if mp_type in MP_STD else "clarinet"
cap_clear = max(0.4, min(cap_clear, 3.0))
cap_len   = max(30.0, min(cap_len, 90.0))
wall      = max(1.6, min(wall, 5.0))
reed_ct   = max(1, min(reed_ct, 8))
reed_len  = max(45.0, min(reed_len, 85.0))

_g = mp_geo(mp_type)
_cap_ir = _g["od"] / 2.0 + cap_clear     # cap internal radius
_cap_or = _cap_ir + wall                 # cap outer radius


# ── Helpers (inlined) ─────────────────────────────────────────────────────────
def _rounded_block(length, width, height, fillet_r, centered_z=False):
    """A rounded-rectangle block, fillet-cleaned BEFORE feature cuts."""
    blk = cq.Workplane("XY").box(length, width, height, centered=(True, True, centered_z))
    try:
        blk = blk.edges("|Z").fillet(min(fillet_r, min(length, width) / 2.0 - 0.5))
    except Exception:
        pass
    return blk


# ── Part builders ────────────────────────────────────────────────────────────
def build_cap():
    """A cup that slides over the mouthpiece tip. A blind bore from the open mouth
    (vented) takes the mouthpiece + reed; a slot on one side clears the ligature
    screws; a small vent hole in the closed end lets the reed dry."""
    body = cq.Workplane("XY").circle(_cap_or).extrude(cap_len)
    # Blind bore from the open (bottom) end up toward the closed top — vents to
    # outside at the mouth, so no sealed cavity forms.
    bore_depth = cap_len - wall
    bore = (
        cq.Workplane("XY")
        .circle(_cap_ir)
        .extrude(bore_depth)
        .translate((0, 0, -0.01))
    )
    body = body.cut(bore)
    # Round the closed top edge (loft-free fillet on the outer top edge).
    try:
        body = body.edges(">Z").fillet(min(wall * 0.8, 1.6))
    except Exception:
        pass

    # Ligature-screw clearance notch: a U-notch open at the mouth (the ligature
    # screws sit near the mouth). A box cutter on the +X wall, wider in Y than the
    # cap so it removes a clean rim section — a flat obround grazing the curved
    # wall leaves tangent slivers (non-watertight), so a through box is used.
    notch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(_cap_or, 0, -1.0))
        .box(2.0 * wall + 2.0, min(_cap_ir * 0.9, 14.0), cap_len * 0.5, centered=(True, True, False))
    )
    body = body.cut(notch)

    # Vent hole through the closed top (lets the reed dry; open both ends).
    vent = (
        cq.Workplane("XY")
        .circle(2.5)
        .extrude(wall + 2.0)
        .translate((0, 0, cap_len - wall - 1.0))
    )
    body = body.cut(vent)
    return body


def build_reed_case():
    """A flat case body with parallel reed slots that hold spare reeds flat so
    they don't chip or warp. Slots are obround pockets bored from the open top."""
    reed_w = _g["reed_w"]
    slot_pitch = reed_w + 4.0
    case_w = slot_pitch * reed_ct + 8.0
    case_l = reed_len + 20.0
    case_h = 6.0
    body = _rounded_block(case_l, case_w, case_h, 4.0)

    # Reed slots: obround pockets down from the open top face (vented). One
    # pushPoints pass = one boolean. Each slot cradles a reed lying flat.
    y0 = -(slot_pitch * (reed_ct - 1)) / 2.0
    slot_depth = case_h - 2.0
    pts = [(0.0, y0 + i * slot_pitch) for i in range(reed_ct)]
    slots = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, case_h - slot_depth))
        .pushPoints(pts)
        .slot2D(reed_len, reed_w + 0.6, angle=0)
        .extrude(slot_depth + 1.0)
    )
    body = body.cut(slots)

    # Two finger holes clearly beyond the reed ends (clean through-holes, vented
    # top and bottom) so a reed can be pushed up and lifted out. The standoff
    # keeps them from touching the slot end caps — an overlap there shares a floor
    # face with the slot (non-watertight), and a cross-notch through the slots
    # does the same, so both are avoided.
    standoff = 5.5
    fh = [(reed_len / 2.0 + standoff, 0.0), (-reed_len / 2.0 - standoff, 0.0)]
    holes = (
        cq.Workplane("XY")
        .pushPoints(fh)
        .circle(2.5)
        .extrude(case_h + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(holes)
    return body


def build_lig_band():
    """A ligature band: a split ring that wraps the mouthpiece and presses the
    reed to the table. Two screw bosses on the open side tighten it. The split
    gap keeps it open (never an enclosed cavity)."""
    band_h = 12.0
    ring = cq.Workplane("XY").circle(_cap_or).extrude(band_h)
    bore = cq.Workplane("XY").circle(_cap_ir).extrude(band_h + 2.0).translate((0, 0, -1.0))
    ring = ring.cut(bore)

    # Split gap on +X (open the ring so it flexes onto the mouthpiece).
    gap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(_cap_or, 0, -1.0))
        .box(_cap_or * 1.2, max(2.0, wall * 0.8), band_h + 2.0, centered=(True, True, False))
    )
    ring = ring.cut(gap)

    # Two screw bosses flanking the gap (solid tabs with through-holes to pinch).
    boss_off = max(2.0, wall * 0.8) / 2.0 + 3.0
    body = ring
    for sy in (-1.0, 1.0):
        boss = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(_cap_or - 1.0, sy * boss_off, 0))
            .box(6.0, 6.0, band_h, centered=(True, True, False))
        )
        body = body.union(boss)
    # A cross screw hole through both bosses (through-hole across Y, vented).
    screw = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(_cap_or + 1.0, band_h / 2.0, 0))
        .circle(1.6)
        .extrude(-(boss_off + 6.0) * 2.0)
    )
    body = body.cut(screw)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "reed_case":
    result = build_reed_case()
elif target_part == "lig_band":
    result = build_lig_band()
else:
    result = build_cap()
