import cadquery as cq
import math

# ─── Globals injected by Yantra4D cq_runner ──────────────────────────────────
finger_length      = float(globals().get("finger_length",      65.0))
base_radius        = float(globals().get("base_radius",        35.0))
flexure_thickness  = float(globals().get("flexure_thickness",   1.2))
finger_count       = int(globals().get("finger_count",           3))
target_part        = str(globals().get("target_part",      "housing"))
phalanx_width      = 18.0

# ─── Helpers ─────────────────────────────────────────────────────────────────
def finger_angle(i):
    return (360.0 / finger_count) * i


def _polar_union(base_wp, build_fn):
    """Union together results of build_fn(angle) for each finger."""
    result = None
    for i in range(finger_count):
        part = build_fn(finger_angle(i))
        result = part if result is None else result.union(part)
    return result


# ─── Housing ─────────────────────────────────────────────────────────────────
def build_housing():
    """ISO-style robotic wrist flange with 6-bolt pattern and knuckle hooks."""

    # Tapered frustum hub
    base = (
        cq.Workplane("XY")
        .circle(base_radius + 5).wires().toPending()
        .workplane(offset=15)
        .circle(base_radius).wires().toPending()
        .loft()
    )

    # Central hollow drive tube
    base = base.faces(">Z").hole(18)

    # 6-bolt radial bolt holes (manual polar loop — most reliable in CQ)
    bolt_r = base_radius - 12
    for k in range(6):
        a = math.radians(k * 60)
        x = bolt_r * math.cos(a)
        y = bolt_r * math.sin(a)
        base = base.faces(">Z").workplane().center(x, y).hole(6.5)

    # Knuckle attachment hooks
    def make_hook(angle_deg):
        a = math.radians(angle_deg)
        cx = (base_radius - 5) * math.cos(a)
        cy = (base_radius - 5) * math.sin(a)
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, 15))
            .box(15, phalanx_width, 10)
            .edges(">Z or <Z").fillet(1.5)
        )

    hooks = _polar_union(None, make_hook)
    return base.union(hooks)


# ─── Skeleton ─────────────────────────────────────────────────────────────────
def build_skeleton():
    """PETG rigid phalanges: proximal (with lightening pocket) + tapered distal."""

    prox_len   = finger_length * 0.45
    prox_start = 22.0
    dist_len   = finger_length * 0.35
    dist_start = prox_start + prox_len + 6.0

    def make_finger(angle_deg):
        a  = math.radians(angle_deg)
        ca = math.cos(a)
        sa = math.sin(a)

        # Proximal phalanx
        cx1 = (base_radius - 2) * ca
        cy1 = (base_radius - 2) * sa
        prox = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx1, cy1, prox_start))
            .transformed(rotate=cq.Vector(0, 0, angle_deg))
            .box(10, phalanx_width - 2, prox_len, centered=(True, True, False))
            .edges("|Z").fillet(2.5)
        )

        # Lightening pocket
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx1, cy1, prox_start + 6))
            .transformed(rotate=cq.Vector(0, 0, angle_deg))
            .box(7, phalanx_width - 10, prox_len - 12, centered=(True, True, False))
        )
        prox = prox.cut(pocket)

        # Distal phalanx (simple tapered box — loft from rotated planes is error-prone)
        cx2 = (base_radius - 5) * ca
        cy2 = (base_radius - 5) * sa
        dist = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx2, cy2, dist_start))
            .transformed(rotate=cq.Vector(0, 0, angle_deg))
            .box(8, phalanx_width - 4, dist_len, centered=(True, True, False))
            .edges(">Z").fillet(3.0)  # rounded fingertip
        )

        return prox.union(dist)

    return _polar_union(None, make_finger)


# ─── Flexure ─────────────────────────────────────────────────────────────────
def build_flexure():
    """TPU V-Notch living hinges carved via cylinder Boolean scoops."""

    prox_len   = finger_length * 0.45
    prox_start = 22.0

    def make_hinge(angle_deg):
        a  = math.radians(angle_deg)
        ca = math.cos(a)
        sa = math.sin(a)

        cx = (base_radius - 5) * ca
        cy = (base_radius - 5) * sa
        hinge_height = prox_start - 15.0

        # ── Wrist hinge block
        block = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, 15))
            .transformed(rotate=cq.Vector(0, 0, angle_deg))
            .box(12, phalanx_width - 2, hinge_height, centered=(True, True, False))
        )

        # Compute scoop radius to achieve the flexure waist thickness
        scoop_r = max(2.0, (12.0 - flexure_thickness) / 2.0)

        # Inner scoop (subtract from +X face)
        mid_z   = 15 + hinge_height / 2.0
        inner_x = cx + (6 - scoop_r) * ca
        inner_y = cy + (6 - scoop_r) * sa
        inner = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(inner_x, inner_y, mid_z))
            .cylinder(phalanx_width + 4, scoop_r)
        )

        # Outer scoop (subtract from -X face)
        outer_x = cx - (6 - scoop_r) * ca
        outer_y = cy - (6 - scoop_r) * sa
        outer = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(outer_x, outer_y, mid_z))
            .cylinder(phalanx_width + 4, scoop_r)
        )

        # Distal hinge block (thinner)
        dist_hinge_z = prox_start + prox_len
        cx2 = (base_radius - 3) * ca
        cy2 = (base_radius - 3) * sa
        block2 = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx2, cy2, dist_hinge_z))
            .transformed(rotate=cq.Vector(0, 0, angle_deg))
            .box(10, phalanx_width - 4, 6, centered=(True, True, False))
        )

        return block.cut(inner).cut(outer).union(block2)

    return _polar_union(None, make_hinge)


# ─── Grip Pad ─────────────────────────────────────────────────────────────────
def build_grip_pad():
    """TPU ribbed friction pads on the inner distal face."""

    prox_len   = finger_length * 0.45
    prox_start = 22.0
    dist_len   = finger_length * 0.35
    dist_start = prox_start + prox_len + 6.0

    def make_pad(angle_deg):
        a  = math.radians(angle_deg)
        ca = math.cos(a)
        sa = math.sin(a)

        px = (base_radius - 9.5) * ca
        py = (base_radius - 9.5) * sa

        pad = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(px, py, dist_start + 2))
            .transformed(rotate=cq.Vector(0, 0, angle_deg))
            .box(3, phalanx_width - 6, dist_len - 4, centered=(True, True, False))
            .edges("|Z").fillet(0.8)
        )

        # Generative rib loop
        total_ribs = max(1, int((dist_len - 8) / 4))
        rx = (base_radius - 12) * ca
        ry = (base_radius - 12) * sa

        for r in range(total_ribs):
            rib_z = dist_start + 4 + (r * 4)
            rib = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(rx, ry, rib_z))
                .transformed(rotate=cq.Vector(0, 0, angle_deg))
                .box(2.5, phalanx_width - 8, 2, centered=(True, True, False))
                .edges(">X").fillet(0.4)
            )
            pad = pad.union(rib)

        return pad

    return _polar_union(None, make_pad)


# ─── Dispatch ────────────────────────────────────────────────────────────────
_dispatch = {
    "skeleton":  build_skeleton,
    "flexure":   build_flexure,
    "grip_pad":  build_grip_pad,
    "housing":   build_housing,
}

result = _dispatch.get(target_part, build_housing)()
