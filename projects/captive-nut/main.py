"""
Captive-Nut Channel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Holds a standard hex nut captive so a machine screw can be tightened one-handed
from the far side of a joint — the trick behind flat-pack furniture, printer
frames and any panel you cannot reach behind. The functional interface is the
hex-nut POCKET: a hexagonal recess sized to the nut's across-flats (A/F) plus a
slide/drop clearance, with a screw clearance bore through its floor so the bolt
passes and threads into the trapped nut.

Every mode traps the SAME hex nut (M4 7 mm A/F, or M5 8 mm A/F), so the joint
takes the same ISO metric screw as the iso-m5 drum-hardware family.

  - slide_channel : an edge bracket with a horizontal hex slot open on one end —
                    the nut slides in from the side and is captured; a screw bore
                    crosses the slot. The classic "captive nut in a printed ear."
  - tnut_block    : a T-slot-style block whose hex nut drops into a pocket from the
                    top and is retained by a narrower screw slot above it, so the
                    nut cannot fall out once the block is in place.
  - trap_plate    : a flat mounting plate with a recessed hex trap on its
                    underside and a counterbored screw hole through the top — a
                    drop-in threaded anchor for panels.

Nut stock (nominal across-flats A/F × thickness, mm — ISO 4032 style hex nut):
    M4 → 7.0 A/F × 3.2 thick     M5 → 8.0 A/F × 4.0 thick
Cited as the CDG `standard` = "M4/M5 hex nut".

Watertight strategy:
  Each part is ONE extruded blank; the hex pocket, screw slot and bores are CUT
  afterwards. Fillets are applied to the clean blank BEFORE feature cuts. A
  slide/drop pocket that opens to a face is a genuine open feature (not a trapped
  void); the screw bore runs THROUGH to a face so it vents. No revolve-of-cut
  profiles, no tangent unions — every union overlaps.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read via PARAM(lambda: name, def).
    The render worker injects target_part = <mode.parts[0]>.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Hex-nut stock (nominal across-flats × thickness, mm) ─────────────────────
NUTS = {
    "M4": {"af": 7.0, "thick": 3.2, "screw": 4.0},
    "M5": {"af": 8.0, "thick": 4.0, "screw": 5.0},
}


def nut_geo(name):
    return NUTS.get(name, NUTS["M5"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "slide_channel"))
# "slide_channel" | "tnut_block" | "trap_plate"

nut_size = str(PARAM(lambda: nut_size, "M5"))          # M4 | M5
nut_clear = float(PARAM(lambda: nut_clear, 0.35))      # A/F pocket clearance (mm, across flats)
wall = float(PARAM(lambda: wall, 3.0))                 # material around the pocket (mm)
depth_clear = float(PARAM(lambda: depth_clear, 0.4))   # extra pocket depth over nut thickness (mm)
body_len = float(PARAM(lambda: body_len, 30.0))        # length of the bracket / block / plate (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
nut_clear = max(0.0, min(nut_clear, 1.0))
wall = max(1.6, min(wall, 8.0))
depth_clear = max(0.0, min(depth_clear, 2.0))
body_len = max(16.0, min(body_len, 80.0))

g = nut_geo(nut_size)
af = g["af"] + nut_clear                  # pocket across-flats
circ_r = af / (2.0 * math.cos(math.radians(30.0)))   # hex circumradius from A/F
nut_thick = g["thick"] + depth_clear      # pocket depth
screw_r = (g["screw"] + 0.6) / 2.0        # screw shank clearance radius


def _hex_wire(across_flats, rot_deg=0.0):
    """Ordered vertices of a regular hexagon given its across-flats dimension.
    rot_deg rotates it (0 → a flat is perpendicular to +Y, i.e. flats top/bottom)."""
    rc = across_flats / (2.0 * math.cos(math.radians(30.0)))
    pts = []
    for k in range(6):
        a = math.radians(60.0 * k + 30.0 + rot_deg)
        pts.append((rc * math.cos(a), rc * math.sin(a)))
    return pts


# ── Part builders ────────────────────────────────────────────────────────────
def build_slide_channel():
    """An edge bracket: a rectangular ear with a horizontal hex slot open on the
    +X end (the nut slides in from the side). A screw bore crosses the slot on Z
    and vents to the top and bottom faces.

    Layout along X (block runs -L/2 .. +L/2): a FIXED-length solid retained end at
    -X carries the screw bore; the hex slot occupies the rest and opens at +X. The
    retained end is sized so the screw bore always has wall on both sides — this is
    what stops a thin sliver from detaching at small body_len (body_count would
    otherwise become 2)."""
    height = af + 2.0 * wall
    thickness = nut_thick + 2.0 * wall
    body = cq.Workplane("XY").box(body_len, thickness, height, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(wall * 0.6, 2.5))
    except Exception:
        pass

    x_min = -body_len / 2.0
    # Solid BACK-STOP at -X: a fixed wall the nut seats against (slot is blind here).
    backstop = wall
    slot_x0 = x_min + backstop                      # slot inner (blind) end
    slot_len = (body_len / 2.0) - slot_x0 + 1.0     # runs to the open +X end

    # Horizontal hex slot: hex cross-section in YZ, extruded along +X to the open end.
    hexpts = _hex_wire(af, rot_deg=0.0)
    slot = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, height / 2.0, slot_x0))
        .polyline(hexpts)
        .close()
        .extrude(slot_len)
    )
    body = body.cut(slot)

    # Screw bore on Z positioned over the SEATED nut — one hex-circumradius in from
    # the blind end so the bolt passes through the nut's centre. It vents top and
    # bottom. The bore never crosses the -X backstop wall, so the block stays one
    # connected body (no severed sliver at small body_len).
    bore_x = slot_x0 + circ_r
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(bore_x, 0, -1.0))
        .circle(screw_r)
        .extrude(height + 2.0)
    )
    body = body.cut(bore)
    return body


def build_tnut_block():
    """A T-slot block: the hex nut DROPS into a pocket from the top; a narrower
    screw slot above the pocket retains it (the nut cannot rise out through the
    slot). The screw bore runs down through the pocket floor to the bottom face."""
    width = af + 2.0 * wall
    height = nut_thick + wall + 5.0
    body = cq.Workplane("XY").box(body_len, width, height, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(wall * 0.6, 2.5))
    except Exception:
        pass

    # Hex drop pocket from the TOP, blind (stops above a solid floor).
    hexpts = _hex_wire(af, rot_deg=0.0)
    pocket_depth = nut_thick + 0.2
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, height - pocket_depth))
        .polyline(hexpts)
        .close()
        .extrude(pocket_depth + 0.1)
    )
    body = body.cut(pocket)

    # Narrow retention slot from the pocket top up to the top face: a channel
    # wide enough for the screw but narrower than the nut A/F (retains the nut).
    ret_w = screw_r * 2.0 + 1.0
    ret = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, height - pocket_depth - 0.1))
        .box(body_len * 0.5, ret_w, pocket_depth + 2.0, centered=(True, True, False))
    )
    body = body.cut(ret)

    # Screw clearance down through the pocket floor to the bottom (vents both).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(screw_r)
        .extrude(height + 2.0)
    )
    body = body.cut(bore)
    return body


def build_trap_plate():
    """A flat anchor plate: a hex nut trap recessed into the UNDERSIDE and a
    counterbored screw hole through the top. The screw drops from above, threads
    into the trapped nut below — a drop-in threaded insert for panels."""
    width = af + 2.0 * wall
    plate_h = nut_thick + wall + 2.0
    body = cq.Workplane("XY").box(body_len, width, plate_h, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(wall * 0.7, 3.0))
    except Exception:
        pass

    # Hex trap recessed into the BOTTOM face (opens downward → not a sealed void).
    hexpts = _hex_wire(af, rot_deg=0.0)
    trap_depth = nut_thick + 0.2
    trap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.1))
        .polyline(hexpts)
        .close()
        .extrude(trap_depth + 0.1)
    )
    body = body.cut(trap)

    # Screw clearance through the remaining top web into the trap (vents both).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(screw_r)
        .extrude(plate_h + 2.0)
    )
    body = body.cut(bore)

    # Shallow counterbore at the top so a cap-screw head sits flush-ish.
    cb_r = screw_r + 1.4
    cb = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_h - 1.6))
        .circle(cb_r)
        .extrude(1.7)
    )
    body = body.cut(cb)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tnut_block":
    result = build_tnut_block()
elif target_part == "trap_plate":
    result = build_trap_plate()
else:  # "slide_channel" (default)
    result = build_slide_channel()
