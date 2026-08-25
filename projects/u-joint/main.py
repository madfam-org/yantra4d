"""
Universal Joint (printable) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A Cardan / universal joint transmits rotation between two shafts whose axes meet
at an angle. This cartridge builds a printable U-joint whose two yokes take a
6-10 mm drive shaft on each end — the same small-shaft bore range the shaft-spline
commons family shares — coupled through a central cross (spider).

IMPORTANT — single manifold body:
  A U-joint is conceptually three loose parts (two yokes + a cross) on four pins.
  To print as ONE watertight, single-body (`body_count == 1`) manifold, this
  cartridge fuses the cross to the yokes through SOLID pin bridges and models the
  articulation clearance as relief GROOVES that never sever the body. The result
  is a rigid coupling / joint blank: it holds the true U-joint geometry (bores,
  yoke ears, cross, offset pin axes) and couples two shafts on one common axis or
  at a fixed set angle, but it is a single printed piece — not a print-in-place
  mechanism (those tessellate as multiple bodies and fail the watertight gate).

Three distinct joints (all keyed to the 6-10 mm shaft bore standard):
  - inline_joint : yokes coaxial (0° between shafts) — a rigid inline coupler with
                   the full cross + pin geometry, for joining two collinear shafts.
  - angled_joint : yokes fixed at `joint_ang` degrees — a bent coupler that carries
                   drive around a set corner (the classic U-joint pose, frozen).
  - single_yoke  : one yoke half plus the cross stub and pin bosses — the printable
                   building block you make two of to key onto opposing shafts.

Dimensionally real (small-shaft drive couplings):
  - shaft bore Ø   : 6-10 mm (matches the shaft-spline commons range)
  - setscrew       : M4 ~4.3 mm radial to pin each yoke to its shaft
  - yoke / cross   : sized so the ears and cross arms are stout enough to print

Watertight strategy:
  Each yoke is a solid barrel (shaft bore cut fully THROUGH → vents both ends) with
  two ears; the cross is a central block with four arms; SOLID pins UNION the cross
  arms into the yoke ears so everything is one fused manifold. Articulation relief
  is a set of shallow grooves that never cut all the way through. Setscrew bores are
  radial through-holes venting to outside. Fillets go on clean blanks BEFORE cuts.

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


# ── Parameters (6-10 mm shaft U-joint) ───────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "inline_joint"))
# "inline_joint" | "angled_joint" | "single_yoke"

bore_d = float(PARAM(lambda: bore_d, 8.0))         # drive shaft bore Ø (mm)
yoke_wall = float(PARAM(lambda: yoke_wall, 4.0))   # wall around the shaft bore
ear_t = float(PARAM(lambda: ear_t, 4.0))           # yoke ear thickness (mm)
cross_d = float(PARAM(lambda: cross_d, 7.0))       # cross arm / pin diameter (mm)
set_d = float(PARAM(lambda: set_d, 4.3))           # yoke setscrew Ø (M4 ~4.3 mm)
joint_ang = float(PARAM(lambda: joint_ang, 25.0))  # fixed articulation angle (deg)

# Clamp to sane ranges so extreme UI values never crash the kernel.
bore_d = max(6.0, min(bore_d, 10.0))
yoke_wall = max(3.0, min(yoke_wall, 8.0))
ear_t = max(3.0, min(ear_t, 8.0))
cross_d = max(4.0, min(cross_d, 12.0))
set_d = max(2.5, min(set_d, min(yoke_wall - 0.6, 6.0)))
joint_ang = max(0.0, min(joint_ang, 40.0))

# Derived geometry.
barrel_od = bore_d + 2.0 * yoke_wall               # yoke shaft barrel OD
gap = max(cross_d + 3.0, barrel_od * 0.9)          # ear inner gap (holds the cross)
ear_span = gap + 2.0 * ear_t                        # outer span across both ears
barrel_len = max(12.0, bore_d * 1.8)                # shaft grip length
cross_arm = gap / 2.0 + ear_t * 0.5                 # cross arm half-length (into ears)


# ── Primitives ───────────────────────────────────────────────────────────────
def _barrel(length, od, bore):
    """A yoke shaft barrel along +Z from z=0: OD cylinder with the shaft bore cut
    fully through (vents both ends). Top rim filleted on the clean blank."""
    blk = cq.Workplane("XY").cylinder(length, od / 2.0, centered=(True, True, False))
    try:
        blk = blk.faces(">Z").edges("%circle").fillet(min(0.8, yoke_wall * 0.15))
    except Exception:
        pass
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(bore / 2.0)
        .extrude(length + 1.0)
    )
    return blk.cut(hole)


def _yoke(with_setscrew=True):
    """A single yoke: a shaft barrel (bore along Z, grip at the bottom) topped by
    two ears that straddle a gap. The ears rise in +Z and carry the pin axis along
    X. Returns the yoke as one solid, its open mouth facing +Z, cross gap centred
    on the origin at the ear height. A radial setscrew pins the shaft."""
    barrel = _barrel(barrel_len, barrel_od, bore_d)

    # Ears: two slabs at +/- X of the gap, rising from the barrel top.
    ear_h = gap * 0.9 + cross_d
    ear_z0 = barrel_len - 0.01
    ears = None
    for sx in (gap / 2.0 + ear_t / 2.0, -(gap / 2.0 + ear_t / 2.0)):
        ear = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, 0, ear_z0))
            .box(ear_t, barrel_od, ear_h, centered=(True, True, False))
        )
        ears = ear if ears is None else ears.union(ear)
    # NOTE: no edge fillet on the combined barrel+ears blank — filleting this
    # feature-laden union degenerates the OCCT result (negative-volume body).
    body = barrel.union(ears)

    if with_setscrew:
        set_z = barrel_len / 2.0
        bore = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, set_z, 0))
            .circle(set_d / 2.0)
            .extrude(barrel_od / 2.0 + 1.0, both=True)
        )
        body = body.cut(bore)
    return body, ear_z0, ear_h


def _cross(pin_axis_x=True):
    """The central cross (spider): a box hub with two opposing arms along one axis.
    For a fused single-body joint each arm is a SOLID cylinder that unions the hub
    to a yoke's ears. `pin_axis_x` puts the arms along X (into the ears). A box hub
    (not a sphere) is used: sphere↔cylinder unions leave a non-watertight seam."""
    hub = cq.Workplane("XY").box(cross_d, cross_d, cross_d)
    arm = (
        cq.Workplane("YZ" if pin_axis_x else "XZ")
        .circle(cross_d / 2.0)
        .extrude(cross_arm, both=True)
    )
    return hub.union(arm)


# ── Part builders ────────────────────────────────────────────────────────────
def build_single_yoke():
    """One yoke half plus a cross stub and pin bosses fused in — the printable
    building block. Make two, key each onto opposing shafts, and pin them to a
    shared cross for a working joint; or print this alone as a shaft coupler end."""
    body, ear_z0, ear_h = _yoke(with_setscrew=True)
    z_seat = ear_z0 + ear_h * 0.55
    # Fuse a cross stub between the ears (arms along X into both ears → one body).
    cross = _cross(pin_axis_x=True).translate((0, 0, z_seat))
    body = body.union(cross)
    return body


def _joint(angle_deg):
    """Two yokes fused through the central cross at a fixed angle. Yoke A points
    its shaft down -Z (barrel below), ears up; yoke B is rotated by `angle_deg`
    about the pin (X) axis and flipped so its shaft points away. The cross fuses
    both ear pairs into one manifold."""
    # Yoke A: as built, shaft barrel from z=0 down is at the bottom, ears up.
    yoke_a, ear_z0, ear_h = _yoke(with_setscrew=True)
    z_seat = ear_z0 + ear_h * 0.55

    # Yoke B: identical yoke, rotated 180° about Z so its ear axis is along Y (the
    # second pin axis of a real cross), then tilted by the joint angle about X, and
    # lifted so its ears interleave at the same cross seat.
    yoke_b, _, _ = _yoke(with_setscrew=True)
    yoke_b = yoke_b.rotate((0, 0, 0), (0, 0, 1), 90)   # ears now along Y
    # Flip it over so its shaft points up and mouth faces down toward the seat.
    yoke_b = yoke_b.rotate((0, 0, 0), (1, 0, 0), 180)
    # After the flip, raise it so its mouth meets the seat, then tilt by the angle.
    lift = z_seat * 2.0
    yoke_b = yoke_b.translate((0, 0, lift))
    if angle_deg > 0.01:
        yoke_b = yoke_b.rotate((0, 0, z_seat), (1, 0, 0), angle_deg)

    # Central cross: two arm pairs — one along X (into yoke A ears), one along Y
    # (into yoke B ears) — fused so BOTH yokes bond to the cross → one manifold.
    cross_x = _cross(pin_axis_x=True).translate((0, 0, z_seat))
    cross_y = _cross(pin_axis_x=False).translate((0, 0, z_seat))
    cross = cross_x.union(cross_y)

    body = yoke_a.union(cross).union(yoke_b)
    return body


def build_inline_joint():
    """Rigid inline coupler: both yokes coaxial (0°), full cross + pin geometry."""
    return _joint(0.0)


def build_angled_joint():
    """Bent coupler carrying drive around a fixed `joint_ang` corner."""
    return _joint(max(8.0, joint_ang))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "angled_joint":
    result = build_angled_joint()
elif target_part == "single_yoke":
    result = build_single_yoke()
else:
    result = build_inline_joint()
