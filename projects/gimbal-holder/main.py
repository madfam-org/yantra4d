"""
Gimbal Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A self-leveling drink/bottle holder for a boat or RV: the vessel sits in an inner cup
that pivots inside one or two rings, so it stays upright as the vehicle rolls. The
outer ring (or a wall plate) mounts to a surface; nested rings pivot on stub trunnions.

Pivot approach (print-in-place, watertight): each pivoting body — base frame, outer
ring, cup — is built as its OWN fully-closed solid, and every mating pin keeps a
`pivot_gap` clearance to the ring it turns in. Because the bodies never actually touch,
the exported mesh is a set of DISJOINT closed manifolds, which is watertight (verified),
and the gaps let it move straight off the plate. No boolean weld between moving bodies
is ever attempted (that would be non-manifold).

Watertightness discipline: a cylindrical pin cannot fuse cleanly onto a cylindrical
shell (curved-to-curved intersections tessellate non-manifold). So every pin roots in a
rectangular BOSS whose flat outer face the pin extrudes from, and every socket is bored
into a rectangular boss face. Cylinder-to-plane fuses are clean.

Three parts (dispatched via `target_part`):
  * "gimbal_cup"  — full 2-axis gimbal: base frame + outer ring + inner cup, print-in-place.
  * "single_axis" — a simpler 1-axis rocker: a base frame + a cup that swings on one axis.
  * "wall_gimbal" — a wall-mount plate carrying a 2-axis gimbal cup that hangs off a bulkhead.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `vessel_dia`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "gimbal_cup"))  # gimbal_cup|single_axis|wall_gimbal

vessel_dia = float(PARAM(lambda: vessel_dia, 70.0))   # vessel (cup/bottle) outer diameter (mm)
cup_h      = float(PARAM(lambda: cup_h,      55.0))   # cup wall height (mm)
wall       = float(PARAM(lambda: wall,        3.0))   # ring/cup wall thickness (mm)
pivot_gap  = float(PARAM(lambda: pivot_gap,   0.6))   # clearance around every pivot pin (mm)
ring_gap   = float(PARAM(lambda: ring_gap,    3.0))   # radial gap between nested rings (mm)
pin_dia    = float(PARAM(lambda: pin_dia,     5.0))   # trunnion pin diameter (mm)
base_dia   = float(PARAM(lambda: base_dia,  120.0))   # mounting base outer diameter (mm)
base_t     = float(PARAM(lambda: base_t,      5.0))   # base plate thickness (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
vessel_dia = max(40.0, min(vessel_dia, 100.0))
cup_h      = max(25.0, min(cup_h, 90.0))
wall       = max(2.0, min(wall, 6.0))
pivot_gap  = max(0.3, min(pivot_gap, 1.5))
ring_gap   = max(1.5, min(ring_gap, 8.0))
pin_dia    = max(3.0, min(pin_dia, 10.0))
base_dia   = max(80.0, min(base_dia, 220.0))
base_t     = max(3.0, min(base_t, 12.0))

# Derived radii — each nested body is one (pivot_gap + pin span + ring_gap) apart.
GAP_SPAN = pin_dia + ring_gap                  # nominal radial jump between bodies
cup_or   = vessel_dia / 2.0 + wall
inner_or = cup_or + pivot_gap + GAP_SPAN       # inner ring outer radius
outer_or = inner_or + pivot_gap + GAP_SPAN     # outer ring outer radius
ring_h   = min(cup_h * 0.7, 40.0)              # gimbal ring height band
PZ       = ring_h * 0.55                        # pivot height within the ring band
BOSS     = pin_dia * 1.8                        # boss cube edge (planar pin/socket root)


# ── Planar-boss trunnion helpers ─────────────────────────────────────────────
def _boss_at(cx, cy, cz):
    """A cube boss centred at (cx, cy, cz) — its flat faces let a pin/socket fuse
    cleanly (cylinder-to-plane, not cylinder-to-shell)."""
    return (
        cq.Workplane("XY")
        .center(cx, cy)
        .box(BOSS, BOSS, BOSS, centered=(True, True, True))
        .translate((0, 0, cz))
    )


def _add_pins(body, radius, on_x, cz, reach):
    """Add two outward trunnion pins on ±X (on_x) or ±Y. The boss is seated one half-edge
    INWARD of `radius` so it is fully embedded in the solid body (outer boss face flush at
    `radius`) — a boss merely straddling the surface leaves a half-floating cube whose
    curved-tangent union with the body sheds a sub-mm inverted sliver. The pin extrudes
    outward from the flush boss face. `reach` = pin length past `radius`."""
    bo = radius - BOSS / 2.0  # boss centre, seated inward so the cube is fully inside
    for s in (-1.0, 1.0):
        if on_x:
            body = body.union(_boss_at(s * bo, 0.0, cz))
            pin = (
                cq.Workplane("YZ").circle(pin_dia / 2.0)
                .extrude(s * (BOSS / 2.0 + reach))
                .translate((s * (radius - BOSS / 2.0), 0, cz))
            )
        else:
            body = body.union(_boss_at(0.0, s * bo, cz))
            pin = (
                cq.Workplane("XZ").circle(pin_dia / 2.0)
                .extrude(s * (BOSS / 2.0 + reach))
                .translate((0, s * (radius - BOSS / 2.0), cz))
            )
        body = body.union(pin)
    return body


def _add_sockets(body, radius, on_x, cz):
    """Bore two clearance sockets into bosses straddling `radius` (on ±X if on_x else
    ±Y). The boss provides a flat face for a clean cylindrical bore; the socket receives
    the child pin with `pivot_gap`."""
    sr = pin_dia / 2.0 + pivot_gap
    for s in (-1.0, 1.0):
        if on_x:
            body = body.union(_boss_at(s * radius, 0.0, cz))
            sock = (
                cq.Workplane("YZ").circle(sr)
                .extrude(-s * (BOSS + pivot_gap + 0.5))
                .translate((s * (radius + BOSS / 2.0 + 0.25), 0, cz))
            )
        else:
            body = body.union(_boss_at(0.0, s * radius, cz))
            sock = (
                cq.Workplane("XZ").circle(sr)
                .extrude(-s * (BOSS + pivot_gap + 0.5))
                .translate((0, s * (radius + BOSS / 2.0 + 0.25), cz))
            )
        body = body.cut(sock)
    return body


# ── Cup (the vessel holder, common to all modes) ─────────────────────────────
def _cup(pin_on_x=True):
    """The open cup that holds the vessel: a closed-bottom cylinder, base at z=0, with a
    drain hole. Carries two outward trunnion pins (default on X) to pivot in its ring."""
    cup = cq.Workplane("XY").circle(cup_or).extrude(cup_h)
    cav = cq.Workplane("XY").circle(vessel_dia / 2.0).extrude(cup_h).translate((0, 0, wall))
    cup = cup.cut(cav)
    drain = cq.Workplane("XY").circle(6.0).extrude(wall + 2.0).translate((0, 0, -1.0))
    cup = cup.cut(drain)
    cup = _add_pins(cup, cup_or, pin_on_x, PZ, reach=ring_gap * 0.6)
    try:
        cup = cup.clean()
    except Exception:
        pass
    return cup


def _ring(o_r, i_r, pin_on_x, height, cz):
    """A gimbal ring band (o_r outer, i_r inner). Sockets on the axis toward the child
    (opposite of pin axis) receive the child pins; outward pins on `pin_on_x` pivot in
    the parent. All pins/sockets root in planar bosses for watertightness."""
    ring = cq.Workplane("XY").circle(o_r).circle(i_r).extrude(height)
    ring = _add_sockets(ring, i_r, on_x=not pin_on_x, cz=cz)
    ring = _add_pins(ring, o_r, pin_on_x, cz, reach=ring_gap * 0.6)
    try:
        ring = ring.clean()
    except Exception:
        pass
    return ring


def _base_plate(post_radius, socket_on_x, cz, post_h):
    """A round mounting plate with a swing well and two upright posts (on the socket
    axis) whose bosses receive the trunnion pins of the body above."""
    base = cq.Workplane("XY").circle(base_dia / 2.0).extrude(base_t)
    has_rim = (base_dia / 2.0) > (post_radius + BOSS + 8.0)
    if has_rim:
        well = (
            cq.Workplane("XY").circle(post_radius + BOSS * 0.3).extrude(base_t + 2.0)
            .translate((0, 0, -1.0))
        )
        base = base.cut(well)
    # Posts: tall blocks rising to the pivot height on the socket axis.
    for s in (-1.0, 1.0):
        if socket_on_x:
            post = (
                cq.Workplane("XY").center(s * (post_radius + BOSS * 0.5), 0.0)
                .box(BOSS * 1.4, BOSS * 1.6, post_h, centered=(True, True, False))
            )
        else:
            post = (
                cq.Workplane("XY").center(0.0, s * (post_radius + BOSS * 0.5))
                .box(BOSS * 1.6, BOSS * 1.4, post_h, centered=(True, True, False))
            )
        base = base.union(post)
    # Sockets bored into the posts, facing inward toward the body above.
    sr = pin_dia / 2.0 + pivot_gap
    for s in (-1.0, 1.0):
        if socket_on_x:
            sock = (
                cq.Workplane("YZ").circle(sr).extrude(-s * (BOSS + pivot_gap + 0.5))
                .translate((s * (post_radius + BOSS + 0.25), 0, cz))
            )
        else:
            sock = (
                cq.Workplane("XZ").circle(sr).extrude(-s * (BOSS + pivot_gap + 0.5))
                .translate((0, s * (post_radius + BOSS + 0.25), cz))
            )
        base = base.cut(sock)
    # Mounting screw holes near the rim (only if a rim exists).
    if has_rim:
        for s in (1.0, -1.0):
            if socket_on_x:
                cx, cy = 0.0, s * (base_dia / 2.0 - 7.0)
            else:
                cx, cy = s * (base_dia / 2.0 - 7.0), 0.0
            hole = (
                cq.Workplane("XY").center(cx, cy).circle(2.2)
                .extrude(base_t + 2.0).translate((0, 0, -1.0))
            )
            base = base.cut(hole)
    try:
        base = base.clean()
    except Exception:
        pass
    return base


# ── Part builders ─────────────────────────────────────────────────────────────
def build_gimbal_cup():
    """Full 2-axis gimbal: base frame (posts on Y) + outer ring (pins Y, sockets X toward
    the cup) + inner cup (pins X). Returned as disjoint closed solids (print-in-place)."""
    lift = base_t + 3.0
    cz = base_t + 3.0 + PZ           # pivot height in world Z after lifting the stack
    frame = _base_plate(outer_or, socket_on_x=False,
                        cz=cz, post_h=base_t + PZ + BOSS * 0.5)
    outer = _ring(outer_or, inner_or, pin_on_x=False, height=ring_h, cz=PZ).translate((0, 0, lift))
    cup = _cup(pin_on_x=True).translate((0, 0, lift))
    return frame.union(outer).union(cup)


def build_single_axis():
    """A 1-axis rocker: base frame with posts on X + a cup that swings on X directly
    (no intermediate ring). Simpler and lower."""
    lift = base_t + 3.0
    cz = base_t + 3.0 + PZ
    frame = _base_plate(cup_or, socket_on_x=True,
                        cz=cz, post_h=base_t + PZ + BOSS * 0.5)
    cup = _cup(pin_on_x=True).translate((0, 0, lift))
    return frame.union(cup)


def build_wall_gimbal():
    """A wall/bulkhead plate carrying a 2-axis gimbal cup. The plate stands vertical (XZ
    plane) behind the stack and is fused to the base rim by a short web."""
    stack = build_gimbal_cup()
    plate_w = base_dia * 0.9
    plate_h = cup_h + ring_h + base_t + 24.0
    plate_y = -(base_dia / 2.0)
    plate_t = wall + 2.0
    plate = (
        cq.Workplane("XZ")
        .box(plate_w, plate_h, plate_t, centered=(True, True, False))
        .translate((0, plate_y - plate_t, plate_h / 2.0 - 12.0))
    )
    for sx in (-1.0, 1.0):
        for sz in (0.22, 0.82):
            hole = (
                cq.Workplane("XZ").circle(2.6).extrude(plate_t + 4.0)
                .translate((sx * (plate_w / 2.0 - 8.0), plate_y + 2.0, plate_h * sz - 12.0))
            )
            plate = plate.cut(hole)
    # Web bridging the base rim to the plate (fuses plate to the frame body).
    web = (
        cq.Workplane("XY")
        .box(BOSS * 2.0, base_dia / 2.0, base_t, centered=(True, False, False))
        .translate((0, plate_y, 0))
    )
    return stack.union(web).union(plate)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "single_axis":
    _built = build_single_axis()
elif target_part == "wall_gimbal":
    _built = build_wall_gimbal()
else:
    _built = build_gimbal_cup()


def _sanitize(wp):
    """Drop degenerate / negative-volume solids left by boss↔ring boolean tangents.

    This is a print-in-place assembly of several genuinely separate positive solids
    (the nested rings + base), so we keep EVERY solid with real positive volume and
    discard only tiny inverted-normal sliver fragments (a curved boss face meeting the
    ring shell can shed a sub-mm negative shell). Keeping all positives preserves the
    disjoint pivoting bodies; dropping negatives makes the export cleanly printable."""
    try:
        solids = [s for s in wp.solids().vals() if s.Volume() > 1.0]
        if solids:
            return cq.Compound.makeCompound(solids)
    except Exception:
        pass
    return wp


result = _sanitize(_built)
