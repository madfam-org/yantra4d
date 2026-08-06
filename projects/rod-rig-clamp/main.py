"""
15 mm Rod Rig Clamp — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The backbone of a cinema camera rig: the 15 mm LWS (Lightweight Support) rod
clamp. Rails run on 15 mm rods spaced 60 mm centre-to-centre (the LWS standard);
matte boxes, follow-focus, monitors and cages all clamp to them. This cartridge
builds a single-rod clamp with an accessory face, a dual-rod bridge that spans
two rods at the 60 mm spacing, and a riser clamp that lifts an accessory above
the rods.

15 mm LWS rod standard (nominal, dimensionally real):
  - rod diameter        = 15.0 mm  (bore = 15 mm + clearance for a sliding clamp)
  - rod spacing         = 60.0 mm  centre-to-centre (LWS 15 mm standard)
  - accessory face      carries 1/4-20 holes (the camera-accessory thread)

Watertight strategy:
  The rod bore is a THROUGH-hole (open at both Y ends → the cavity vents to
  outside, never a trapped void). The clamp pinch-slit is a through-cut that
  reaches the bore, and the clamp bolt hole is a through-hole. All unions are
  overlapping boxes into shared material; fillets are applied to clean blanks
  BEFORE any feature cut, and are wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

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


# ── Parameters (15 mm LWS rod standard) ──────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "single_clamp"))
# "single_clamp" | "dual_rod_bridge" | "riser_clamp"

rod_d = float(PARAM(lambda: rod_d, 15.0))          # rod diameter (LWS 15 mm)
rod_clear = float(PARAM(lambda: rod_clear, 0.3))   # bore clearance over rod (per side)
rod_spacing = float(PARAM(lambda: rod_spacing, 60.0))  # centre-to-centre (LWS std)

body_th = float(PARAM(lambda: body_th, 20.0))      # clamp block thickness along rod (Y)
wall = float(PARAM(lambda: wall, 6.0))             # material around the bore (mm)
clamp_bolt_d = float(PARAM(lambda: clamp_bolt_d, 5.2))  # pinch bolt clearance (M5)
slit_w = float(PARAM(lambda: slit_w, 2.0))         # pinch-slit width (mm)

face_th = float(PARAM(lambda: face_th, 6.0))       # accessory face plate thickness
face_hole_d = float(PARAM(lambda: face_hole_d, 6.6))  # 1/4-20 accessory hole (mm)

riser_h = float(PARAM(lambda: riser_h, 30.0))      # riser column height above bore (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
rod_d = max(6.0, min(rod_d, 30.0))
rod_clear = max(0.1, min(rod_clear, 1.0))
rod_spacing = max(20.0, min(rod_spacing, 120.0))
body_th = max(8.0, min(body_th, 50.0))
wall = max(3.0, min(wall, 15.0))
clamp_bolt_d = max(2.5, min(clamp_bolt_d, 8.0))
slit_w = max(0.8, min(slit_w, 5.0))
face_th = max(3.0, min(face_th, 15.0))
face_hole_d = max(3.0, min(face_hole_d, 10.0))
riser_h = max(10.0, min(riser_h, 100.0))

bore_r = (rod_d + 2.0 * rod_clear) / 2.0
block_h = rod_d + 2.0 * wall           # clamp block height (Z), bore centred at wall+bore_r region


# ── Primitives ───────────────────────────────────────────────────────────────
def _block(w, d, h, r):
    """Axis-aligned block centred in X/Y, base at z=0, rounded vertical edges."""
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.3:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


def _rod_clamp_unit(cx):
    """A single rod-clamp block centred at X = cx: a block with a through-bore
    along Y at height (bore centre), a pinch slit reaching the bore from the
    top, and a pinch bolt across the slit. Returns the finished (watertight)
    solid. Bore axis is at z = block_h/2."""
    bw = rod_d + 2.0 * wall
    block = _block(bw, body_th, block_h, min(2.5, wall - 1.0)).translate((cx, 0, 0))
    zc = block_h / 2.0

    # Through-bore along Y (open both ends → vents to outside).
    bore = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(cx, 0, zc))
        .circle(bore_r)
        .extrude(body_th / 2.0 + 1.0, both=True)
    )
    body = block.cut(bore)

    # Pinch slit: a thin slot from the TOP down into the bore, cut through Y so
    # the two jaws can flex. Reaches from top surface to just past bore centre.
    slit_depth = (block_h - zc) + bore_r * 0.5
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0, block_h - slit_depth))
        .box(slit_w, body_th + 2.0, slit_depth + 1.0, centered=(True, True, False))
    )
    body = body.cut(slit)

    # Pinch bolt: a clearance hole across X through both jaws, above the bore so
    # tightening squeezes the slit. Runs along X, through-hole (vents outside).
    bolt_z = zc + bore_r + (block_h - (zc + bore_r)) * 0.5
    bolt_z = min(bolt_z, block_h - clamp_bolt_d / 2.0 - 0.6)
    bolt = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, bolt_z, cx))
        .circle(max(0.5, clamp_bolt_d / 2.0))
        .extrude(bw / 2.0 + 1.0, both=True)
    )
    body = body.cut(bolt)
    return body, bw, zc


# ── Part builders ────────────────────────────────────────────────────────────
def build_single_clamp():
    """One 15 mm rod clamp with an accessory face on top carrying a 1/4-20 hole
    — the workhorse that puts a monitor, handle or plate onto a single rod."""
    body, bw, zc = _rod_clamp_unit(0.0)

    # Accessory face: a plate on top of the block, offset to the +X side so it
    # clears the pinch slit, with a 1/4-20 hole. Overlaps into the block.
    face_w = bw
    face = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, block_h - 0.01))
        .box(face_w, body_th, face_th + 0.01, centered=(True, True, False))
    )
    try:
        face = face.edges("|Z").fillet(min(2.0, face_w / 2.0 - 0.5))
    except Exception:
        pass
    body = body.union(face)

    # 1/4-20 hole into the face top, placed to one side of the slit. The cut
    # starts ABOVE the top surface and drills down, leaving a ~0.8 mm floor —
    # an open pocket that vents to outside (never a trapped void).
    hr = max(0.5, face_hole_d / 2.0)
    hx = bw / 2.0 - hr - 2.0
    face_top = block_h + face_th
    depth = face_th - 0.8
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(hx, 0, face_top - depth))
        .circle(hr)
        .extrude(depth + 1.0)  # +1 nick above the top face → clean, vented cut
    )
    body = body.cut(hole)
    return body


def build_dual_rod_bridge():
    """A bridge clamping TWO 15 mm rods at the 60 mm LWS spacing, joined by a
    spine that carries an accessory face — the standard way a matte box, cage
    plate or baseplate rides both rails at once."""
    half = rod_spacing / 2.0
    unitL, bw, zc = _rod_clamp_unit(-half)
    unitR, _, _ = _rod_clamp_unit(half)

    # Spine connecting the two clamp bodies at the bore height region. A slab
    # spanning the gap, overlapping into both blocks so the union is solid.
    spine_w = rod_spacing + bw  # reaches into both clamps
    spine_h = block_h * 0.6
    spine = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, block_h - spine_h))
        .box(spine_w, body_th, spine_h + 0.01, centered=(True, True, False))
    )
    try:
        spine = spine.edges("|Z").fillet(min(2.0, body_th / 2.0 - 0.5))
    except Exception:
        pass

    body = unitL.union(spine).union(unitR)

    # Central 1/4-20 hole into the spine top — drilled down from above the top
    # face, leaving a floor, so it is an open (vented) pocket.
    hr = max(0.5, face_hole_d / 2.0)
    top = block_h
    depth = min(face_th, spine_h - 1.0)
    depth = max(2.5, depth)
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, top - depth))
        .circle(hr)
        .extrude(depth + 1.0)
    )
    body = body.cut(hole)
    return body


def build_riser_clamp():
    """A single-rod clamp with a tall riser column lifting a 1/4-20 accessory
    face well above the rod — raises a monitor or EVF over the rail plane."""
    body, bw, zc = _rod_clamp_unit(0.0)

    # Riser column rising from the block top.
    col_w = bw * 0.7
    col_d = body_th * 0.8
    col = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, block_h - 0.01))
        .box(col_w, col_d, riser_h + 0.01, centered=(True, True, False))
    )
    try:
        col = col.edges("|Z").fillet(min(3.0, col_w / 2.0 - 0.5))
    except Exception:
        pass

    # Top cap face (a bit wider than the column) with the 1/4-20 hole.
    cap_w = bw
    cap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, block_h + riser_h - 0.01))
        .box(cap_w, body_th, face_th + 0.01, centered=(True, True, False))
    )
    try:
        cap = cap.edges("|Z").fillet(min(2.5, body_th / 2.0 - 0.5))
    except Exception:
        pass

    body = body.union(col).union(cap)

    # 1/4-20 hole into the cap top — drilled from above, leaving a floor (open,
    # vented pocket).
    hr = max(0.5, face_hole_d / 2.0)
    cap_top = block_h + riser_h + face_th
    depth = face_th - 0.8
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cap_top - depth))
        .circle(hr)
        .extrude(depth + 1.0)
    )
    body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "dual_rod_bridge":
    result = build_dual_rod_bridge()
elif target_part == "riser_clamp":
    result = build_riser_clamp()
else:
    result = build_single_clamp()
