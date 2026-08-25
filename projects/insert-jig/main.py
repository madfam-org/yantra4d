"""
Threaded-Insert Jig — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A press-fit alignment jig for seating brass HEAT-SET inserts square and to a
consistent depth with a soldering iron. Heat-set inserts (CNC-Kitchen / McMaster
IUB-IUC series) are the de-facto way to put a reusable metal machine-screw thread
into a 3D print: you melt a knurled brass barrel into a moulded boss, and an
ISO metric screw then threads into it. The hard part by hand is keeping the
insert perpendicular and stopping it flush — this jig fixes both.

Every mode is built around one Common Denominator Geometry: the insert BOSS
SOCKET — a blind counter-bored pocket sized to the insert's outer knurl diameter
(minus a light melt-interference) on the M3-M8 range. Because the socket accepts
the same insert that then receives an ISO metric screw, anything in the
iso-hex-fastener metric family (bolts, nuts) mates through the shared thread.

  - guide_block  : a rectangular guide with a stepped bore (insert counterbore +
                   screw-shank clearance below) that slips over the iron tip and
                   holds the insert coaxial while it melts in. A depth shoulder
                   sets a repeatable seat height.
  - boss_gauge   : a "go / seat-depth" test coupon — a printed boss with the
                   recommended moulded-in insert pocket (tapered lead-in +
                   straight knurl-grip zone) so you can dial in boss ID before
                   committing it to a real part.
  - press_collar : a thick collar that fits over an already-melted insert to press
                   it the last fraction flush and true against a cooling part; a
                   central through bore clears the insert bore and vents the pocket.

Insert dimensions (nominal knurl OD × length, mm — real IUB/IUC heat-set stock):
    M3 → 4.0 × 5.7   M4 → 5.6 × 8.1   M5 → 6.4 × 9.5
    M6 → 8.0 × 12.7  M8 → 10.0 × 12.7
Cited as the CDG `standard` = "M3-M8 insert".

Watertight strategy:
  Every part is ONE extruded blank with the pockets/bores CUT afterwards. Fillets
  are applied to the clean blank BEFORE any feature cut (fillet on a feature-laden
  solid crashes OCCT clean()). Blind pockets stop above a solid floor so no bore
  is open at both ends unless it is a genuine THROUGH clearance (vented to both
  faces → no trapped void). No revolve-of-cut profiles, no tangent unions.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>); the render worker injects
    target_part = <mode.parts[0]>. Do NOT use globals()/eval/getattr.
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


# ── Heat-set insert stock (nominal knurl OD × barrel length, mm) ─────────────
INSERTS = {
    "M3": {"od": 4.0, "length": 5.7, "screw": 3.0},
    "M4": {"od": 5.6, "length": 8.1, "screw": 4.0},
    "M5": {"od": 6.4, "length": 9.5, "screw": 5.0},
    "M6": {"od": 8.0, "length": 12.7, "screw": 6.0},
    "M8": {"od": 10.0, "length": 12.7, "screw": 8.0},
}


def insert_geo(name):
    return INSERTS.get(name, INSERTS["M4"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "guide_block"))
# "guide_block" | "boss_gauge" | "press_collar"

insert_size = str(PARAM(lambda: insert_size, "M4"))    # M3 | M4 | M5 | M6 | M8
melt_fit = float(PARAM(lambda: melt_fit, 0.15))        # per-side interference (mm)
wall = float(PARAM(lambda: wall, 4.0))                 # jig wall around the socket (mm)
seat_depth = float(PARAM(lambda: seat_depth, 0.3))     # flush offset above the part (mm)
block_h = float(PARAM(lambda: block_h, 14.0))          # guide-block height (mm)
gauge_boss_h = float(PARAM(lambda: gauge_boss_h, 8.0))  # test-coupon boss height (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
melt_fit = max(0.0, min(melt_fit, 0.5))
wall = max(2.0, min(wall, 10.0))
seat_depth = max(0.0, min(seat_depth, 3.0))
block_h = max(8.0, min(block_h, 40.0))
gauge_boss_h = max(4.0, min(gauge_boss_h, 30.0))

g = insert_geo(insert_size)
insert_r = g["od"] / 2.0                 # nominal knurl radius
socket_r = insert_r - melt_fit           # printed pocket radius (melt interference)
socket_r = max(0.8, socket_r)
insert_len = g["length"]
screw_r = (g["screw"] + 0.6) / 2.0       # clearance for the machine screw shank


# ── Part builders ────────────────────────────────────────────────────────────
def build_guide_block():
    """A guide block: an outer square post with a stepped coaxial bore. The top
    counterbore takes the insert (holds it coaxial to the iron); a narrower screw
    clearance runs below it down to a solid floor that sets the seat depth."""
    side = g["od"] + 2.0 * wall
    body = cq.Workplane("XY").box(side, side, block_h, centered=(True, True, False))
    # Fillet the vertical edges of the clean blank BEFORE cutting features.
    try:
        body = body.edges("|Z").fillet(min(wall * 0.6, 3.0))
    except Exception:
        pass

    # Insert counterbore from the TOP, blind (leaves a floor below for the seat).
    pocket_depth = min(insert_len + 1.5, block_h - 2.0 - seat_depth)
    pocket_depth = max(2.0, pocket_depth)
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, block_h - pocket_depth))
        .circle(socket_r)
        .extrude(pocket_depth + 0.1)
    )
    body = body.cut(pocket)

    # Screw-shank clearance THROUGH the floor to the bottom face (vents both ends
    # of the lower bore → no trapped void; the insert pocket floor becomes a ring
    # shoulder the insert can rest on if desired).
    thru = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(screw_r)
        .extrude(block_h + 2.0)
    )
    body = body.cut(thru)

    # A shallow lead-in chamfer at the pocket mouth eases insert entry.
    try:
        body = body.faces(">Z").edges("%CIRCLE").chamfer(min(0.6, melt_fit + 0.4))
    except Exception:
        pass
    return body


def build_boss_gauge():
    """A moulded-in boss test coupon: a flat base carrying an upright cylindrical
    boss with the recommended insert pocket. The pocket has a tapered lead-in and
    a straight knurl-grip zone, and stops above a solid floor (blind → no trapped
    void because the floor face is solid material, not a sealed cavity)."""
    base_side = g["od"] + 2.0 * wall + 4.0
    base_h = 3.0
    base = cq.Workplane("XY").box(base_side, base_side, base_h, centered=(True, True, False))
    try:
        base = base.edges("|Z").fillet(2.0)
    except Exception:
        pass

    boss_r = insert_r + wall * 0.8
    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_h - 0.01))
        .circle(boss_r)
        .extrude(gauge_boss_h + 0.01)
    )
    body = base.union(boss)
    top_z = base_h + gauge_boss_h

    # Pocket: straight knurl-grip zone from the boss top down toward (not through)
    # the base. Depth ~ insert length so the coupon models the real seat.
    grip_depth = min(insert_len, gauge_boss_h - 1.0)
    grip_depth = max(2.0, grip_depth)
    grip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, top_z - grip_depth))
        .circle(socket_r)
        .extrude(grip_depth + 0.1)
    )
    body = body.cut(grip)

    # Tapered lead-in cone at the mouth so the cold insert self-centres.
    lead = min(1.2, grip_depth * 0.3)
    cone = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, top_z - lead))
        .circle(socket_r + lead)
        .workplane(offset=lead + 0.1)
        .circle(socket_r)
        .loft(combine=True)
    )
    body = body.cut(cone)
    return body


def build_press_collar():
    """A stout collar to press a just-melted insert the last fraction flush and
    square. It fits down over the insert boss; a central through bore clears the
    insert bore (vented both ends → watertight, no trapped void)."""
    outer_r = insert_r + wall
    height = max(6.0, insert_len * 0.7 + 3.0)
    collar = cq.Workplane("XY").circle(outer_r).extrude(height)

    # Register counterbore from the BOTTOM that slips over the insert/boss.
    reg_depth = min(insert_len * 0.6, height - 2.5)
    reg_depth = max(2.0, reg_depth)
    reg_r = insert_r + 0.5   # slip fit over the boss/insert
    reg = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.1))
        .circle(reg_r)
        .extrude(reg_depth + 0.1)
    )
    collar = collar.cut(reg)

    # Central through bore clears the insert bore and vents the pocket.
    thru = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(screw_r)
        .extrude(height + 2.0)
    )
    collar = collar.cut(thru)

    # Round the top so it is comfortable to press with a thumb / arbor.
    try:
        collar = collar.faces(">Z").edges("%CIRCLE").chamfer(min(1.0, wall * 0.4))
    except Exception:
        pass
    return collar


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "boss_gauge":
    result = build_boss_gauge()
elif target_part == "press_collar":
    result = build_press_collar()
else:  # "guide_block" (default)
    result = build_guide_block()
