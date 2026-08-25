import math

import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
# cq_runner injects parameters as module globals but blocks the globals()
# builtin, so reading them via globals().get() failed every production render
# of this cartridge. The NameError probe below needs no blocked builtins.
def PARAM(getter, default):
    try:
        return getter()
    except Exception:  # noqa: BLE001 — NameError is absent from older
        # cq_runner sandbox builtin allowlists, so catching it by name raises
        # inside the sandbox; the broad catch is the portable probe.
        return default


finger_length     = float(PARAM(lambda: finger_length,     65.0))
base_radius       = float(PARAM(lambda: base_radius,       35.0))
flexure_thickness = float(PARAM(lambda: flexure_thickness,  1.2))
# int(float(...)) — the API coerces slider values to float and int("3.0") raises.
finger_count      = int(float(PARAM(lambda: finger_count,     3)))
target_part       = str(PARAM(lambda: target_part,    "housing"))
phalanx_width     = 18.0


# ─── Helpers ─────────────────────────────────────────────────────────────────
def fa(i):
    """Finger angle in degrees for finger i."""
    return (360.0 / finger_count) * i


def polar_xy(radius, angle_deg):
    """Return (x, y) for a point at radius and angle (degrees)."""
    a = math.radians(angle_deg)
    return radius * math.cos(a), radius * math.sin(a)


def union_all(shapes):
    """Reduce a list of Workplanes into a single union."""
    result = shapes[0]
    for s in shapes[1:]:
        result = result.union(s)
    return result


# ─── Housing ─────────────────────────────────────────────────────────────────
def build_housing():
    """ISO wrist flange: cylinder hub + 6 bolt holes + knuckle hooks."""

    # Main hub (plain cylinder — no loft to avoid pending-wire issues)
    base = (
        cq.Workplane("XY")
        .cylinder(15, base_radius + 3)
    )

    # Central drive bore
    base = base.faces(">Z").hole(18)

    # 6-bolt radial pattern
    bolt_r = base_radius - 10
    for k in range(6):
        bx, by = polar_xy(bolt_r, k * 60)
        base = base.faces(">Z").workplane().center(bx, by).hole(6.5)

    # Knuckle attachment hooks per finger
    hooks = []
    for i in range(finger_count):
        ang = fa(i)
        cx, cy = polar_xy(base_radius - 4, ang)
        hook = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, 7.5))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(14, phalanx_width, 10)
        )
        hooks.append(hook)

    return union_all([base] + hooks)


# ─── Skeleton ─────────────────────────────────────────────────────────────────
def build_skeleton():
    """PETG phalanges: proximal box with lightening pocket + tapered distal box."""

    prox_len   = finger_length * 0.45
    prox_start = 22.0
    dist_len   = finger_length * 0.35
    dist_start = prox_start + prox_len + 6.0

    fingers = []
    for i in range(finger_count):
        ang = fa(i)
        cx1, cy1 = polar_xy(base_radius - 2, ang)
        cx2, cy2 = polar_xy(base_radius - 5, ang)

        # Proximal phalanx
        prox = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx1, cy1, prox_start))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(10, phalanx_width - 2, prox_len, centered=(True, True, False))
        )

        # Lightening pocket
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx1, cy1, prox_start + 6))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(6, phalanx_width - 10, prox_len - 12, centered=(True, True, False))
        )
        prox = prox.cut(pocket)

        # Distal phalanx
        dist = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx2, cy2, dist_start))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(8, phalanx_width - 4, dist_len, centered=(True, True, False))
        )

        fingers.append(prox.union(dist))

    return union_all(fingers)


# ─── Flexure ─────────────────────────────────────────────────────────────────
def build_flexure():
    """TPU V-Notch living hinges: block with cylindrical scoops to thin the waist."""

    prox_len   = finger_length * 0.45
    prox_start = 22.0

    hinge_height = max(4.0, prox_start - 15.0)
    scoop_r      = max(1.5, (12.0 - max(0.4, flexure_thickness)) / 2.0)

    hinges = []
    for i in range(finger_count):
        ang     = fa(i)
        a_rad   = math.radians(ang)
        ca, sa  = math.cos(a_rad), math.sin(a_rad)

        cx  = (base_radius - 5) * ca
        cy  = (base_radius - 5) * sa
        mid_z = 15.0 + hinge_height / 2.0

        # Main hinge block (wrist → proximal)
        block1 = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, 15))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(12, phalanx_width - 2, hinge_height, centered=(True, True, False))
        )

        # Inner scoop cylinder (to thin the hinge to flexure_thickness)
        inner_x = cx + (6.0 - scoop_r) * ca
        inner_y = cy + (6.0 - scoop_r) * sa
        scoop1 = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(inner_x, inner_y, mid_z))
            .cylinder(phalanx_width + 4, scoop_r)
        )

        outer_x = cx - (6.0 - scoop_r) * ca
        outer_y = cy - (6.0 - scoop_r) * sa
        scoop2 = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(outer_x, outer_y, mid_z))
            .cylinder(phalanx_width + 4, scoop_r)
        )

        h1 = block1.cut(scoop1).cut(scoop2)

        # Distal hinge block (proximal → distal)
        cx2 = (base_radius - 3) * ca
        cy2 = (base_radius - 3) * sa
        h2 = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx2, cy2, prox_start + prox_len))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(10, phalanx_width - 4, 6, centered=(True, True, False))
        )

        hinges.append(h1.union(h2))

    return union_all(hinges)


# ─── Grip Pad ─────────────────────────────────────────────────────────────────
def build_grip_pad():
    """TPU ribbed friction pads on the inner distal face."""

    prox_len   = finger_length * 0.45
    prox_start = 22.0
    dist_len   = finger_length * 0.35
    dist_start = prox_start + prox_len + 6.0

    total_ribs = max(1, int((dist_len - 8.0) / 4.0))

    pads = []
    for i in range(finger_count):
        ang     = fa(i)
        a_rad   = math.radians(ang)
        ca, sa  = math.cos(a_rad), math.sin(a_rad)

        px = (base_radius - 9.5) * ca
        py = (base_radius - 9.5) * sa

        pad = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(px, py, dist_start + 2))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(3, phalanx_width - 6, dist_len - 4, centered=(True, True, False))
        )

        rx = (base_radius - 12) * ca
        ry = (base_radius - 12) * sa

        ribs = []
        for r in range(total_ribs):
            rib_z = dist_start + 4 + (r * 4)
            rib = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(rx, ry, rib_z))
                .transformed(rotate=cq.Vector(0, 0, ang))
                .box(2.5, phalanx_width - 8, 2, centered=(True, True, False))
            )
            ribs.append(rib)

        if ribs:
            pad = union_all([pad] + ribs)
        pads.append(pad)

    return union_all(pads)


# ─── Dispatch ────────────────────────────────────────────────────────────────
_dispatch = {
    "skeleton": build_skeleton,
    "flexure":  build_flexure,
    "grip_pad": build_grip_pad,
    "housing":  build_housing,
}

result = _dispatch.get(target_part, build_housing)()
