"""
15 mm Rod Bridge Plate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A bridge that spans two 15 mm LWS (Lightweight Support) cinema rods at the 60 mm
standard spacing and carries an accessory platform across them. Rails on 15 mm
rods spaced 60 mm centre-to-centre are the backbone of a camera rig; this bridge
clamps both rails at once and gives a flat 1/4-20 cheese plate, a raised riser
plate, or a vertical accessory face. Every rod socket is the real 15 mm LWS bore,
so it shares rails with any 15 mm rod clamp (e.g. `rod-rig-clamp`).

15 mm LWS rod standard (nominal, dimensionally real):
  - rod diameter = 15.0 mm (bore = 15 mm + clearance for a sliding clamp)
  - rod spacing  = 60.0 mm centre-to-centre (LWS 15 mm standard)
  - accessory holes = 1/4-20 UNC (~6.6 mm clearance)

Three modes (each geometrically distinct):
  - bridge_plate : dual rod clamps + a wide flat cheese plate with a 1/4-20 grid.
  - riser_bridge : dual rod clamps + two riser columns lifting a top plate.
  - angle_bridge : dual rod clamps + a vertical face plate on one side with
                   1/4-20 holes (mount a monitor / accessory upright).

Watertight strategy:
  Each rod bore is a THROUGH-hole along Y (vents to outside). The pinch slit and
  clamp bolt are through-cuts. The spanning plate / risers / face overlap into the
  clamp blocks with real material (no tangency). 1/4-20 holes are open pockets
  drilled from above that leave a floor and nick through the top face (vented).
  Fillets are applied to plain blanks BEFORE feature cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Parameters (15 mm LWS rod standard) ──────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "bridge_plate"))
# "bridge_plate" | "riser_bridge" | "angle_bridge"

rod_d = float(PARAM(lambda: rod_d, 15.0))          # rod diameter (LWS 15 mm)
rod_clear = float(PARAM(lambda: rod_clear, 0.3))   # bore clearance over rod (per side)
rod_spacing = float(PARAM(lambda: rod_spacing, 60.0))  # centre-to-centre (LWS std)

body_th = float(PARAM(lambda: body_th, 20.0))      # clamp block thickness along rod (Y)
wall = float(PARAM(lambda: wall, 6.0))             # material around the bore (mm)
clamp_bolt_d = float(PARAM(lambda: clamp_bolt_d, 5.2))  # pinch bolt clearance (M5)
slit_w = float(PARAM(lambda: slit_w, 2.0))         # pinch-slit width (mm)

plate_th = float(PARAM(lambda: plate_th, 6.0))     # cheese/top plate thickness
face_hole_d = float(PARAM(lambda: face_hole_d, 6.6))  # 1/4-20 accessory hole (mm)

riser_h = float(PARAM(lambda: riser_h, 30.0))      # riser column height (riser_bridge)
face_h = float(PARAM(lambda: face_h, 50.0))        # vertical face height (angle_bridge)

# Clamp to sane ranges so extreme UI values never crash the kernel.
rod_d = max(6.0, min(rod_d, 30.0))
rod_clear = max(0.1, min(rod_clear, 1.0))
rod_spacing = max(30.0, min(rod_spacing, 120.0))
body_th = max(8.0, min(body_th, 50.0))
wall = max(3.0, min(wall, 15.0))
clamp_bolt_d = max(2.5, min(clamp_bolt_d, 8.0))
slit_w = max(0.8, min(slit_w, 5.0))
plate_th = max(3.0, min(plate_th, 15.0))
face_hole_d = max(3.0, min(face_hole_d, 10.0))
riser_h = max(10.0, min(riser_h, 100.0))
face_h = max(20.0, min(face_h, 120.0))

bore_r = (rod_d + 2.0 * rod_clear) / 2.0
block_h = rod_d + 2.0 * wall


# ── Primitives ───────────────────────────────────────────────────────────────
def _block(w, d, h, r):
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.3:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


def _rod_unit(cx):
    """A single 15 mm rod clamp centred at X=cx: block + through-bore along Y +
    pinch slit + cross bolt. Returns (solid, block_width)."""
    bw = rod_d + 2.0 * wall
    block = _block(bw, body_th, block_h, min(2.5, wall - 1.0)).translate((cx, 0, 0))
    zc = block_h / 2.0
    bore = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(cx, 0, zc))
        .circle(bore_r)
        .extrude(body_th / 2.0 + 1.0, both=True)
    )
    body = block.cut(bore)
    slit_depth = (block_h - zc) + bore_r * 0.5
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0, block_h - slit_depth))
        .box(slit_w, body_th + 2.0, slit_depth + 1.0, centered=(True, True, False))
    )
    body = body.cut(slit)
    bolt_z = zc + bore_r + (block_h - (zc + bore_r)) * 0.5
    bolt_z = min(bolt_z, block_h - clamp_bolt_d / 2.0 - 0.6)
    bolt = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, bolt_z, cx))
        .circle(max(0.5, clamp_bolt_d / 2.0))
        .extrude(bw / 2.0 + 1.0, both=True)
    )
    body = body.cut(bolt)
    return body, bw


def _dual_clamps():
    """Two rod clamps at the LWS spacing; returns (unionable list, block_width)."""
    half = rod_spacing / 2.0
    uL, bw = _rod_unit(-half)
    uR, _ = _rod_unit(half)
    return uL, uR, bw


def _pocket_1420(body, hx, hy, top_z, depth):
    """Cut an open (vented) 1/4-20 pocket from above the top face down."""
    hr = max(0.5, face_hole_d / 2.0)
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(hx, hy, top_z - depth))
        .circle(hr)
        .extrude(depth + 1.0)
    )
    return body.cut(hole)


# ── Part builders ────────────────────────────────────────────────────────────
def build_bridge_plate():
    """Dual rod clamps spanned by a wide flat cheese plate with a 6-hole 1/4-20
    grid — a baseplate that rides both rails."""
    uL, uR, bw = _dual_clamps()
    plate_w = rod_spacing + bw
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, block_h - 0.01))
        .box(plate_w, body_th, plate_th + 0.01, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Z").fillet(min(2.0, body_th / 2.0 - 0.5))
    except Exception:
        pass
    body = uL.union(plate).union(uR)

    top_z = block_h + plate_th
    depth = plate_th - 0.8
    for hx in (-rod_spacing * 0.3, 0.0, rod_spacing * 0.3):
        for hy in (-body_th * 0.25, body_th * 0.25):
            body = _pocket_1420(body, hx, hy, top_z, depth)
    return body


def build_riser_bridge():
    """Dual rod clamps + two riser columns lifting a top plate above the rails —
    raises a plate / monitor over the rail plane."""
    uL, uR, bw = _dual_clamps()
    half = rod_spacing / 2.0
    body = uL.union(uR)

    # Two riser columns rising from each clamp top, overlapping in.
    col_w = bw * 0.7
    col_d = body_th * 0.8
    for cx in (-half, half):
        col = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0, block_h - 0.01))
            .box(col_w, col_d, riser_h + 0.01, centered=(True, True, False))
        )
        try:
            col = col.edges("|Z").fillet(min(3.0, col_w / 2.0 - 0.5))
        except Exception:
            pass
        body = body.union(col)

    # Top plate spanning both columns.
    plate_w = rod_spacing + bw
    cap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, block_h + riser_h - 0.01))
        .box(plate_w, body_th, plate_th + 0.01, centered=(True, True, False))
    )
    try:
        cap = cap.edges("|Z").fillet(min(2.0, body_th / 2.0 - 0.5))
    except Exception:
        pass
    body = body.union(cap)

    top_z = block_h + riser_h + plate_th
    depth = plate_th - 0.8
    for hx in (-rod_spacing * 0.3, 0.0, rod_spacing * 0.3):
        body = _pocket_1420(body, hx, 0.0, top_z, depth)
    return body


def build_angle_bridge():
    """Dual rod clamps joined by a spine, with a vertical face plate rising on
    the +Y side carrying 1/4-20 holes — mount a monitor / accessory upright."""
    uL, uR, bw = _dual_clamps()
    plate_w = rod_spacing + bw

    # Low spine tying the two clamps together at the top.
    spine = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, block_h - plate_th))
        .box(plate_w, body_th, plate_th + 0.01, centered=(True, True, False))
    )
    try:
        spine = spine.edges("|Z").fillet(min(2.0, body_th / 2.0 - 0.5))
    except Exception:
        pass
    body = uL.union(spine).union(uR)

    # Vertical face plate rising from the +Y edge of the spine.
    face_t = plate_th
    face = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, block_h - 0.5, body_th / 2.0 - face_t / 2.0))
        .box(plate_w, face_h, face_t, centered=(True, True, False))
    )
    try:
        face = face.edges("|Y").fillet(min(2.0, face_t / 2.0 - 0.2))
    except Exception:
        pass
    body = body.union(face)

    # 1/4-20 holes through the vertical face (along Y, through → vented).
    hr = max(0.5, face_hole_d / 2.0)
    for hx in (-rod_spacing * 0.3, 0.0, rod_spacing * 0.3):
        hz = block_h + face_h * 0.5
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(hx, hz, body_th / 2.0 - face_t))
            .circle(hr)
            .extrude(face_t + 2.0)
        )
        body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "riser_bridge":
    result = build_riser_bridge()
elif target_part == "angle_bridge":
    result = build_angle_bridge()
else:  # "bridge_plate"
    result = build_bridge_plate()
