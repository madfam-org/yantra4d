"""
Cam-Lock Latch Set — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Companion pieces for a furniture / cabinet cam lock. The `lock-cam` cartridge
builds the swinging cam; this set builds the parts the cam meets: the strike the
cam catches behind, the body bushing that adapts an oversize mounting hole down
to the standard 16/19 mm cam-lock body, and a keeper block that gives the cam a
positive shelf to latch onto. Sized to the two dominant furniture cam-lock body
diameters so the whole cam-lock commons family shares one mounting standard.

Three distinct latch pieces (all keyed to the 16/19 mm cam-lock body standard):
  - strike_plate : a flat mounting plate with a receiving slot the cam swings
                   into and two countersunk screw holes to fix it to the frame.
  - body_bushing : a stepped sleeve that drops into an oversize (worn or over-
                   drilled) mounting hole and bores back down to the 16 mm or
                   19 mm body, with a top flange that stops it at the surface.
  - keeper_block : a raised catch block with an undercut ledge that gives the
                   cam a positive shelf to hook behind, plus screw fixings.

Dimensionally real (standard furniture / cabinet cam locks):
  - body (mounting) diameters : 16 mm and 19 mm (the two dominant standards)
  - cam plate reach           : ~43 mm typical, ~2-2.5 mm steel — the strike slot
                                and keeper ledge are sized to clear that plate
  - fixing screws             : #6 / M3.5-ish wood screws, ~3.5 mm shank, ~7 mm head

Watertight strategy:
  The strike plate is a filleted flat blank; its receiving slot is an obround cut
  fully THROUGH the plate (vents both faces) and the countersunk screw holes are
  through-bores with a stacked-cylinder countersink (never a revolve of a cut
  profile). The body bushing is two coaxial cylinders UNIONED (flange + barrel)
  with the body bore cut fully through (open both ends). The keeper block is a
  filleted blank with the cam ledge cut as a through-pocket that opens to a side
  face, and through screw bores. Fillets are applied to clean blanks BEFORE cuts.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>) — do NOT use globals()/eval.
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


# ── Parameters (16/19 mm cam-lock latch set) ─────────────────────────────────
target_part = str(PARAM(lambda: target_part, "strike_plate"))
# "strike_plate" | "body_bushing" | "keeper_block"

body_d = float(PARAM(lambda: body_d, 16.0))        # cam-lock body Ø (16/19 mm)
plate_t = float(PARAM(lambda: plate_t, 4.0))       # strike / keeper plate thickness
cam_clear = float(PARAM(lambda: cam_clear, 3.0))   # slot / ledge clearance for the cam plate
screw_d = float(PARAM(lambda: screw_d, 3.6))       # fixing-screw shank Ø
hole_d = float(PARAM(lambda: hole_d, 22.0))        # oversize mounting hole Ø (body_bushing)
keep_h = float(PARAM(lambda: keep_h, 8.0))         # keeper catch-block height

# Clamp to sane ranges so extreme UI values never crash the kernel.
body_d = max(12.0, min(body_d, 25.0))
plate_t = max(2.5, min(plate_t, 10.0))
cam_clear = max(2.0, min(cam_clear, 6.0))
screw_d = max(2.5, min(screw_d, 6.0))
hole_d = max(body_d + 3.0, min(hole_d, 40.0))
keep_h = max(4.0, min(keep_h, 20.0))

# Derived footprint for the strike / keeper plates.
plate_w = body_d + 4.0 * screw_d + 8.0     # across the two screw columns
plate_len = max(38.0, body_d * 2.5)        # along the cam swing


# ── Primitives ───────────────────────────────────────────────────────────────
def _flat_blank(w, length, thick, rad):
    """A flat plate blank centred on X/Y, base at z=0, with filleted vertical
    corners applied on the CLEAN blank before any feature cut."""
    blk = cq.Workplane("XY").box(w, length, thick, centered=(True, True, False))
    try:
        blk = blk.edges("|Z").fillet(min(rad, w / 2.0 - 0.5, length / 2.0 - 0.5))
    except Exception:
        pass
    return blk


def _through_slot(width, length, thru_h, cx=0.0, cy=0.0, z0=-0.5):
    """An obround receiving slot cut fully through (vents both faces)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, z0))
        .slot2D(length, width, angle=0)
        .extrude(thru_h)
    )


def _cs_screw(cx, cy, thru_h, z_top):
    """A countersunk screw hole: a shank through-bore plus a stacked conical
    countersink built as a short widening cylinder from the top face (approximate
    csink; NOT a revolve of a cut profile). Vents both faces."""
    shank = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, -0.5))
        .circle(screw_d / 2.0)
        .extrude(thru_h)
    )
    head_r = screw_d
    csink = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, z_top - head_r))
        .circle(screw_d / 2.0)
        .workplane(offset=head_r + 0.5)
        .circle(head_r)
        .loft(combine=True)
    )
    return shank, csink


# ── Part builders ────────────────────────────────────────────────────────────
def build_strike_plate():
    """A flat strike: a receiving slot the cam swings into, flanked by two
    countersunk screw holes to fix it to the frame."""
    body = _flat_blank(plate_w, plate_len, plate_t, 3.0)

    # Receiving slot down the middle, sized to clear the cam plate + swing.
    slot_len = plate_len * 0.55
    slot_w = cam_clear + 2.0
    body = body.cut(_through_slot(slot_w, slot_len, plate_t + 1.0))

    # Two countersunk screws, one at each end past the slot.
    sy = plate_len / 2.0 - screw_d * 1.6
    for cy in (sy, -sy):
        shank, csink = _cs_screw(0.0, cy, plate_t + 1.0, plate_t)
        body = body.cut(shank).cut(csink)
    return body


def build_body_bushing():
    """A stepped adapter sleeve for an oversize / worn mounting hole: a barrel
    that fills the oversize hole, a top flange that stops it at the surface, and
    the body bore cut fully through so the real cam-lock body passes through."""
    barrel_h = plate_t + keep_h            # deep enough to grip the panel
    flange_od = hole_d + 2.0 * screw_d + 4.0
    flange_h = max(2.5, plate_t * 0.6)

    barrel = (
        cq.Workplane("XY")
        .cylinder(barrel_h, hole_d / 2.0, centered=(True, True, False))
    )
    flange = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, barrel_h - flange_h))
        .cylinder(flange_h, flange_od / 2.0, centered=(True, True, False))
    )
    try:
        flange = flange.faces(">Z").edges("%circle").fillet(min(1.0, flange_h * 0.3))
    except Exception:
        pass
    body = barrel.union(flange)

    # Body bore straight through the whole stack (open both ends → vents).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(body_d / 2.0)
        .extrude(barrel_h + 1.0)
    )
    body = body.cut(bore)
    return body


def build_keeper_block():
    """A raised catch block: a filleted base plate carrying a raised block with an
    undercut ledge that gives the cam a positive shelf to hook behind, plus two
    through screw fixings. The ledge is a through-pocket opening to a side face
    (vents to outside), so no sealed cavity."""
    base = _flat_blank(plate_w, plate_len, plate_t, 3.0)

    # Raised catch block on top, offset to one side (the cam approaches from +Y).
    blk_len = plate_len * 0.4
    blk_w = plate_w * 0.7
    block = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_len * 0.15, plate_t - 0.01))
        .box(blk_w, blk_len, keep_h, centered=(True, True, False))
    )
    body = base.union(block)
    try:
        body = body.edges("|Z").fillet(2.0)
    except Exception:
        pass

    # Undercut catch ledge: a pocket cut into the block face that opens to the -Y
    # side face (a through-pocket → vents to outside). Sized to clear the cam.
    ledge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_len * 0.15 - blk_len * 0.5,
                                      plate_t + keep_h - cam_clear - 1.0))
        .box(blk_w * 0.6, blk_len + 2.0, cam_clear + 1.0,
             centered=(True, True, False))
    )
    body = body.cut(ledge)

    # Two screw fixings through the base at the far (-Y) end, clear of the block.
    sy = -plate_len / 2.0 + screw_d * 1.6
    sx = plate_w / 2.0 - screw_d * 1.6
    for cx in (sx, -sx):
        shank, csink = _cs_screw(cx, sy, plate_t + 1.0, plate_t)
        body = body.cut(shank).cut(csink)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "body_bushing":
    result = build_body_bushing()
elif target_part == "keeper_block":
    result = build_keeper_block()
else:
    result = build_strike_plate()
