"""
Compliant Gripper Pad — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The wear face that turns a hard jaw into a gentle one. A ribbed TPU pad: a
backing plate with a field of transverse ribs on the gripping face. The ribs
buckle and splay under load, so the pad conforms to a curved or irregular part
without a compliant mechanism — and they are the wear item, replaced in
minutes for pennies.

RIB PITCH is the tunable compliance parameter and is published as a CDG
profile interface: closer ribs = stiffer pad (more material per unit contact
area), wider ribs = softer and more conforming. The backing bolt pattern is the
one already used by `tool-gripper` and by `pneu-net-finger`'s root flange, so a
pad generated at a given `bolt_span` drops onto either jaw.

Modes:
  - flat_pad   : ribbed pad on a flat backing — the general-purpose jaw face.
  - vee_pad    : the same rib field on a V-groove backing, for round stock; the
                 V self-centres a shaft or tube in the jaw.
  - dovetail_pad : ribbed pad on a dovetail tongue instead of bolts, for jaws
                 that carry a dovetail accessory face.

Watertight strategy: the pad is ONE extruded backing prism with ribs UNIONED on
top (never separate bodies — each rib overlaps the backing by construction) and
bolt/dovetail cuts taken last. Rib count is derived from width and pitch and
floored at 1; the V-groove depth and dovetail are clamped against the backing
thickness so no cut can ever pass through and split the plate.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

Print in TPU (Shore 85–95A). The pad is the sacrificial part — expect to
reprint it, not the jaw.
"""

import math

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "flat_pad"))
# "flat_pad" | "vee_pad" | "dovetail_pad"

pad_len    = float(PARAM(lambda: pad_len,   60.0))  # pad length (X)
pad_w      = float(PARAM(lambda: pad_w,     34.0))  # pad width (Y)
back_th    = float(PARAM(lambda: back_th,    4.0))  # backing plate thickness
rib_pitch  = float(PARAM(lambda: rib_pitch,  4.0))  # rib centre spacing — COMPLIANCE
rib_w      = float(PARAM(lambda: rib_w,      1.8))  # rib width at its base
rib_h      = float(PARAM(lambda: rib_h,      3.5))  # rib height above the backing
rib_taper  = float(PARAM(lambda: rib_taper,  0.55)) # tip width as a fraction of base
vee_angle  = float(PARAM(lambda: vee_angle, 90.0))  # included angle of the V groove
bolt_span  = float(PARAM(lambda: bolt_span, 40.0))  # bolt centre-to-centre (X)
bolt_dia   = float(PARAM(lambda: bolt_dia,   4.3))  # M4 clearance
dove_w     = float(PARAM(lambda: dove_w,    16.0))  # dovetail tongue width
dove_h     = float(PARAM(lambda: dove_h,     5.0))  # dovetail tongue height

# ── Clamps ───────────────────────────────────────────────────────────────────
pad_len   = max(15.0, min(pad_len, 220.0))
pad_w     = max(10.0, min(pad_w, 160.0))
back_th   = max(1.5,  min(back_th, 15.0))
rib_pitch = max(1.2,  min(rib_pitch, 20.0))
rib_w     = max(0.6,  min(rib_w, 12.0))
rib_h     = max(0.5,  min(rib_h, 20.0))
rib_taper = max(0.2,  min(rib_taper, 1.0))
vee_angle = max(45.0, min(vee_angle, 150.0))
bolt_span = max(6.0,  min(bolt_span, 200.0))
bolt_dia  = max(1.5,  min(bolt_dia, 12.0))
dove_w    = max(5.0,  min(dove_w, 120.0))
dove_h    = max(1.5,  min(dove_h, 25.0))

# ── Derived, clamped ─────────────────────────────────────────────────────────
# A rib must be narrower than its pitch or the field fuses into a solid slab.
RIB_W = min(rib_w, rib_pitch - 0.4)
RIB_W = max(0.4, RIB_W)
RIB_TIP = max(0.3, RIB_W * rib_taper)
# Ribs run across Y; they are laid out along X. Always at least one.
N_RIB = max(1, int((pad_len - RIB_W) // rib_pitch) + 1)
FIELD = (N_RIB - 1) * rib_pitch
X0 = -FIELD / 2.0

# Bolts must sit inside the plate with a real land.
BOLT_R = min(bolt_dia / 2.0, pad_w / 4.0 - 0.8, pad_len / 4.0 - 0.8)
BOLT_R = max(0.5, BOLT_R)
SPAN = min(bolt_span, pad_len - 2.0 * BOLT_R - 3.0)
SPAN = max(2.0 * BOLT_R + 1.0, SPAN)

# V groove: depth from the geometry of the included angle, capped so it never
# cuts through the backing.
VEE_HALF = math.radians(vee_angle / 2.0)
VEE_DEPTH_FULL = (pad_w / 2.0) / max(math.tan(VEE_HALF), 0.2)
VEE_DEPTH = min(VEE_DEPTH_FULL, back_th - 1.0, rib_h + back_th * 0.6)
VEE_DEPTH = max(0.4, VEE_DEPTH)
VEE_HALF_W = VEE_DEPTH * math.tan(VEE_HALF)
VEE_HALF_W = min(VEE_HALF_W, pad_w / 2.0 - 0.5)

# Dovetail: tongue below the backing, clamped inside the pad width.
DOVE_W = min(dove_w, pad_w - 4.0)
DOVE_W = max(3.0, DOVE_W)
DOVE_H = min(dove_h, pad_len * 0.5)
DOVE_H = max(1.0, DOVE_H)


# ── Helpers ──────────────────────────────────────────────────────────────────
def rib_field(z_top, y_half, y_off=0.0):
    """One fused solid of all ribs standing on the plane z_top.

    Each rib is a tapered prism (base RIB_W, tip RIB_TIP) running along Y. The
    base is sunk 0.2 mm INTO the backing so the union always overlaps."""
    tool = None
    sink = 0.2
    for i in range(N_RIB):
        x = X0 + i * rib_pitch
        rib = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y_off, z_top - sink))
            .rect(RIB_W, 2.0 * y_half)
            .workplane(offset=rib_h + sink)
            .rect(RIB_TIP, 2.0 * y_half)
            .loft(ruled=True)
        )
        tool = rib if tool is None else tool.union(rib)
    return tool


def bolt_holes(z0, z1):
    """Two bolt clearance holes on the X centreline."""
    tool = None
    for sx in (-1, 1):
        h = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * SPAN / 2.0, 0, z0 - 1.0))
            .circle(BOLT_R)
            .extrude((z1 - z0) + 2.0)
        )
        tool = h if tool is None else tool.union(h)
    return tool


# ── Part builders ────────────────────────────────────────────────────────────
def build_flat_pad():
    """Backing plate with the rib field on the +Z (gripping) face."""
    body = (
        cq.Workplane("XY")
        .box(pad_len, pad_w, back_th, centered=(True, True, False))
    )
    body = body.union(rib_field(back_th, pad_w / 2.0))
    body = body.cut(bolt_holes(0.0, back_th + rib_h))
    return body


def build_vee_pad():
    """The same rib field on a V-groove backing so round stock self-centres.

    The V is cut from the ribbed face: a prismatic wedge running along X,
    clamped so it never reaches the underside of the plate."""
    body = (
        cq.Workplane("XY")
        .box(pad_len, pad_w, back_th, centered=(True, True, False))
    )
    body = body.union(rib_field(back_th, pad_w / 2.0))
    top_z = back_th + rib_h
    # Wedge: wide at the top (spanning Y), apex at (top_z - VEE_DEPTH); the
    # prism runs along X. Sketched on YZ and extruded in +X, then shifted so it
    # overhangs both ends of the pad.
    wedge = (
        cq.Workplane("YZ")
        .polyline(
            [
                (-VEE_HALF_W, top_z + 0.5),
                (VEE_HALF_W, top_z + 0.5),
                (0.0, top_z - VEE_DEPTH),
            ]
        )
        .close()
        .extrude(pad_len + 2.0)
        .translate((-(pad_len + 2.0) / 2.0, 0, 0))
    )
    body = body.cut(wedge)
    body = body.cut(bolt_holes(0.0, top_z))
    return body


def build_dovetail_pad():
    """Ribbed pad carried on a dovetail tongue instead of bolts."""
    body = (
        cq.Workplane("XY")
        .box(pad_len, pad_w, back_th, centered=(True, True, False))
    )
    body = body.union(rib_field(back_th, pad_w / 2.0))
    # Dovetail tongue hanging below the backing: a trapezoid prism running
    # along X (narrow at the plate, wide at the tip → it locks in a socket).
    narrow = DOVE_W * 0.72
    tongue = (
        cq.Workplane("YZ")
        .polyline(
            [
                (-narrow / 2.0, 0.2),
                (narrow / 2.0, 0.2),
                (DOVE_W / 2.0, -DOVE_H),
                (-DOVE_W / 2.0, -DOVE_H),
            ]
        )
        .close()
        .extrude(pad_len)
        .translate((-pad_len / 2.0, 0, 0))
    )
    # The tongue's top edge sits 0.2 mm INSIDE the plate, so the union always
    # overlaps and yields a single body.
    body = body.union(tongue)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "vee_pad":
    result = build_vee_pad()
elif target_part == "dovetail_pad":
    result = build_dovetail_pad()
else:  # "flat_pad"
    result = build_flat_pad()
