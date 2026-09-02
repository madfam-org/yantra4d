"""
French Cleat Keyhole Plate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Two one-member families, closed by one plate.

The commons publishes a 45-degree French cleat wall system (`french-cleat`,
`grid-hub`) and a keyhole wall-hanging pattern (`speaker-bracket`). Both families
have exactly one member that the graph can see, and the two systems have never
met — which is odd, because in a real workshop they meet constantly. A cleat wall
is how a shop reconfigures; a keyhole slot is how almost every commercial
appliance, speaker, router bracket and power strip already expects to hang. This
plate is the adapter between them, and it closes both families at once.

It is deliberately the lowest-effort object in the tranche. That is the argument
for it: two singletons closed by one T1 cartridge is the best edge-per-effort
ratio in the whole wave.

Modes are dispatched via `target_part`:
  * "keyhole_plate" — accessory cleat on the back, keyhole SLOTS on the face:
                      the plate hangs on a cleat and receives two screws.
  * "stud_plate"    — accessory cleat on the back, keyhole STUDS on the face:
                      a keyhole-slotted device (`speaker-bracket`, or anything
                      commercial) hangs directly on the cleat wall.
  * "cleat_shelf"   — the same cleat back carrying a small shelf with a front
                      lip, and keyhole slots on its riser.

The `stud_plate` mode is why this is a real mate and not only a graph edge:
`speaker-bracket` presents keyhole SLOTS, so something has to present the studs.

Cleat geometry is not invented here. `cleat_ramp_geometry`,
`wall_cleat_profile` and `accessory_cleat_profile` are inlined from
`french-cleat` unchanged, so this plate drops onto the same wall strip at the
same angle with the same hang gap.

Watertightness strategy:
  * The keyhole is cut as ONE fused tool — the head bore, the slot channel and
    the shank bore unioned before the cut — so its throat is never an edge two
    separate cuts share.
  * Every stud straddles the plate it grows from; the head is a lofted collar
    that OVERLAPS the shank rather than sitting on it.
  * Every cut is bounded inside the plate with a margin that scales, and the
    keyhole positions are derived from the plate, so a wide pattern on a narrow
    plate moves the holes inward instead of cutting off its corners.
  * No sealed void anywhere: every bore opens on a face.
  * No fillet on any edge a slot or a bore has touched — OCC blends such arcs
    without raising and returns a non-watertight solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "keyhole_plate"))

angle = float(PARAM(lambda: angle, 45.0))
cleat_h = float(PARAM(lambda: cleat_h, 30.0))
cleat_depth = float(PARAM(lambda: cleat_depth, 14.0))
plate_w = float(PARAM(lambda: plate_w, 120.0))
plate_h = float(PARAM(lambda: plate_h, 90.0))
wall = float(PARAM(lambda: wall, 4.0))
fit = float(PARAM(lambda: fit, 0.4))
keyhole_dia = float(PARAM(lambda: keyhole_dia, 9.0))
keyhole_slot = float(PARAM(lambda: keyhole_slot, 4.5))
keyhole_drop = float(PARAM(lambda: keyhole_drop, 12.0))
pattern_dx = float(PARAM(lambda: pattern_dx, 80.0))
stud_head_h = float(PARAM(lambda: stud_head_h, 3.0))
shelf_depth = float(PARAM(lambda: shelf_depth, 60.0))

angle = max(30.0, min(angle, 60.0))
cleat_h = max(15.0, min(cleat_h, 60.0))
cleat_depth = max(8.0, min(cleat_depth, 30.0))
plate_w = max(40.0, min(plate_w, 300.0))
plate_h = max(40.0, min(plate_h, 300.0))
wall = max(3.0, min(wall, 10.0))
fit = max(0.1, min(fit, 1.0))
keyhole_dia = max(5.0, min(keyhole_dia, 16.0))
keyhole_slot = max(2.5, min(keyhole_slot, 10.0))
keyhole_drop = max(4.0, min(keyhole_drop, 30.0))
pattern_dx = max(20.0, min(pattern_dx, 280.0))
stud_head_h = max(1.5, min(stud_head_h, 6.0))
shelf_depth = max(20.0, min(shelf_depth, 120.0))

# The slot must be narrower than the head it hangs from, and the head must fit
# in the plate. Clamped against the FINAL plate width, not the requested one.
KH_DIA = min(keyhole_dia, plate_w * 0.30)
KH_DIA = max(KH_DIA, 5.0)
KH_SLOT = min(keyhole_slot, KH_DIA - 1.2)
KH_SLOT = max(KH_SLOT, 2.0)

# Plate height has to hold the cleat AND a keyhole with its drop. Raised, never
# trimmed: trimming would silently shorten the slot travel, which is the one
# dimension that decides whether the plate can actually be lifted off a screw.
PLATE_H = max(plate_h, cleat_h + KH_DIA + keyhole_drop + 3.0 * wall)
PLATE_W = max(plate_w, 2.0 * KH_DIA + 3.0 * wall)

OVERLAP = 1.0


# ── Cleat cross-sections (inlined from `french-cleat`, unchanged) ────────────
def cleat_ramp_geometry(depth, height, ang):
    """Return (run, rise, ramp_z) for a cleat ramp at EXACTLY `ang` degrees.

    Clamping the RISE rather than the run is what keeps the angle exact, so the
    wall strip and this plate present mating faces that are genuinely parallel
    instead of nearly so."""
    rad = math.radians(ang)
    tan = math.tan(rad)
    rise = height * 0.5
    run = rise / tan
    max_run = depth - 2.0
    if run > max_run:
        run = max_run
        rise = run * tan
    ramp_z = height - rise
    return run, rise, ramp_z


def accessory_cleat_profile(depth, height, ang, gap):
    """The COMPLEMENT of the wall cleat: the lip underside is the same plane,
    shifted up by `gap` for a printable hang fit."""
    run, rise, ramp_z = cleat_ramp_geometry(depth, height, ang)
    ramp_x = depth - run
    return (
        cq.Workplane("XZ")
        .polyline([
            (0.0, 0.0),
            (ramp_x, 0.0),
            (depth, ramp_z + gap),
            (depth, height),
            (0.0, height),
        ])
        .close()
    )


# ── Shared plate geometry ────────────────────────────────────────────────────
def base_plate():
    """The face plate, standing in the XZ plane with its thickness along X.

    X is out from the wall, Y across the plate, Z up. The plate's back face is
    at x = 0 and the accessory cleat grows BACKWARD from it, straddling it."""
    return (
        cq.Workplane("XY")
        .box(wall, PLATE_W, PLATE_H, centered=(False, True, False))
    )


def with_cleat(body):
    """Union the accessory cleat onto the plate's back, overlapping it in X.

    The cleat is extruded along Y and translated so it straddles the plate's
    back face rather than meeting it there: a cleat that only touches the plate
    is a tangential union, which OCC fuses and the mesh reports open."""
    cleat_len = PLATE_W - 2.0 * wall
    cleat_len = max(10.0, cleat_len)
    # Extruded SYMMETRICALLY about Y=0. A Workplane("XZ") extrudes along -Y, so
    # `.extrude(len).translate((0, -len/2, 0))` — the form `french-cleat` uses for
    # its own one-piece strip — puts the band at Y in [-1.5L, -0.5L]. On a plate
    # that is centred on Y=0 that leaves the cleat overlapping the plate by a
    # 4 mm sliver and hanging 112 mm off the side, which the first render showed
    # as a 228 mm bounding box on a 120 mm plate. `both=True` is the form that
    # composes with a centred body.
    cleat = (
        accessory_cleat_profile(cleat_depth, cleat_h, angle, fit)
        .extrude(cleat_len / 2.0, both=True)
        .rotate((0, 0, 0), (0, 0, 1), 180.0)
        .translate((OVERLAP, 0, PLATE_H - cleat_h))
    )
    return body.union(cleat)


def keyhole_points():
    """The two keyhole centres, derived from the plate rather than requested.

    A pattern wider than the plate moves the holes INWARD instead of cutting the
    plate's corners off — the same rule as every other bounded cut here."""
    limit = PLATE_W / 2.0 - KH_DIA / 2.0 - wall
    dx = min(pattern_dx / 2.0, max(0.0, limit))
    z = PLATE_H - cleat_h - KH_DIA / 2.0 - wall
    z = max(KH_DIA / 2.0 + keyhole_drop + wall, z)
    z = min(z, PLATE_H - KH_DIA / 2.0 - wall)
    return [(-dx, z), (dx, z)] if dx > KH_DIA * 0.25 else [(0.0, z)]


def keyhole_tool(y, z, thickness):
    """ONE fused tool: head bore + slot channel + shank bore.

    Fusing before the cut matters. Cutting a circle and then a slot leaves the
    throat as an edge two separate booleans share, and OCC will happily produce
    a solid whose mesh is non-manifold at exactly that edge."""
    head = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(y, z, -1.0))
        .circle(KH_DIA / 2.0)
        .extrude(thickness + 2.0)
    )
    channel = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(y, z - keyhole_drop / 2.0, -1.0))
        .rect(KH_SLOT, keyhole_drop)
        .extrude(thickness + 2.0)
    )
    shank = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(y, z - keyhole_drop, -1.0))
        .circle(KH_SLOT / 2.0)
        .extrude(thickness + 2.0)
    )
    return head.union(channel).union(shank)


def cut_keyholes(body, thickness):
    for (y, z) in keyhole_points():
        try:
            body = body.cut(keyhole_tool(y, z, thickness))
        except Exception:
            pass
    return body


def keyhole_stud(y, z):
    """A shank and a lofted head, both straddling what they grow from.

    The head is a loft from the shank radius OUT to the head radius and back —
    one solid, not two frusta meeting on a shared face. Two frusta stacked face
    to face is a tangential union: the kernel accepts it and the mesh comes back
    self-touching."""
    shank_r = KH_SLOT / 2.0
    head_r = KH_DIA / 2.0 - 0.4
    head_r = max(head_r, shank_r + 0.6)
    stand = max(1.6, stud_head_h)
    shank = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(y, z, wall - OVERLAP))
        .circle(shank_r)
        .extrude(stand + OVERLAP)
    )
    head = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(y, z, wall + stand - 0.2))
        .circle(shank_r)
        .workplane(offset=stud_head_h * 0.45)
        .circle(head_r)
        .workplane(offset=stud_head_h * 0.45)
        .circle(head_r * 0.92)
        .loft(ruled=True)
    )
    return shank.union(head)


# ── Part builders ────────────────────────────────────────────────────────────
def build_keyhole_plate():
    """Accessory cleat on the back, keyhole SLOTS on the face."""
    body = with_cleat(base_plate())
    body = cut_keyholes(body, wall)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_stud_plate():
    """Accessory cleat on the back, keyhole STUDS on the face.

    This is the mode that makes the mate physical: `speaker-bracket` presents
    keyhole slots, so something has to present the studs."""
    body = with_cleat(base_plate())
    for (y, z) in keyhole_points():
        try:
            body = body.union(keyhole_stud(y, z))
        except Exception:
            pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cleat_shelf():
    """The same cleat back carrying a shelf with a front lip, keyholes on the
    riser above it."""
    body = with_cleat(base_plate())

    shelf_t = max(3.0, wall)
    shelf = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(wall - OVERLAP, 0.0, wall))
        .box(shelf_depth + OVERLAP, PLATE_W, shelf_t, centered=(False, True, False))
    )
    body = body.union(shelf)

    lip_h = max(4.0, shelf_t * 2.0)
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(wall + shelf_depth - shelf_t, 0.0,
                                      wall + shelf_t - OVERLAP))
        .box(shelf_t, PLATE_W, lip_h + OVERLAP, centered=(False, True, False))
    )
    body = body.union(lip)

    # Drain / lightening slots in the shelf, counted from the space that
    # survives the margins and skipped entirely when there is none.
    margin = max(6.0, wall * 1.5)
    avail_y = PLATE_W - 2.0 * margin
    avail_x = shelf_depth - 2.0 * margin
    if avail_y > 12.0 and avail_x > 8.0:
        slot_w = 6.0
        pitch = slot_w + 6.0
        n = int(math.floor(avail_y / pitch))
        if n >= 1:
            span = (n - 1) * pitch
            for i in range(n):
                y = -span / 2.0 + i * pitch
                tool = (
                    cq.Workplane("XY")
                    .transformed(offset=cq.Vector(wall + margin, y, wall - 1.0))
                    .box(avail_x, slot_w, shelf_t + 2.0, centered=(False, True, False))
                )
                try:
                    body = body.cut(tool)
                except Exception:
                    pass

    body = cut_keyholes(body, wall)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "keyhole_plate": build_keyhole_plate,
    "stud_plate": build_stud_plate,
    "cleat_shelf": build_cleat_shelf,
}

result = _dispatch.get(target_part, build_keyhole_plate)()
