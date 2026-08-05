"""
Headphone / Headset Hook — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A hook that hangs a headset by its headband from a broad, rounded cradle so the
band does not develop a dent. Three mount styles (dispatched by `target_part`):

  * "under_desk_hook" — an L-bracket that screws to the underside of a desktop;
                        the arm drops down and forward into an up-turned cradle.
  * "wall_hook"       — a flat screw plate for a wall, with a hook arm out to
                        the cradle.
  * "desk_clamp"      — a C-clamp that grips a desk edge of thickness `desk_t`
                        (no screws) with the cradle on the front.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cradle_w`).
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
mount        = str(  PARAM(lambda: mount, "under_desk"))  # under_desk | wall | clamp
target_part  = str(  PARAM(lambda: target_part, ""))      # overrides mount if a part id

cradle_w     = float(PARAM(lambda: cradle_w,    28.0))    # headband rest width (mm)
reach        = float(PARAM(lambda: reach,       55.0))    # how far the hook sticks out (mm)
drop         = float(PARAM(lambda: drop,        45.0))    # how far the arm drops down (mm)
thick        = float(PARAM(lambda: thick,        8.0))    # arm / plate thickness (mm)
plate_w      = float(PARAM(lambda: plate_w,     40.0))    # mount plate width (mm)
plate_len    = float(PARAM(lambda: plate_len,   55.0))    # mount plate length (mm)
screw_dia    = float(PARAM(lambda: screw_dia,    4.5))    # mount screw clearance dia (mm)
desk_t       = float(PARAM(lambda: desk_t,      25.0))    # desk thickness for the clamp (mm)
clamp_depth  = float(PARAM(lambda: clamp_depth, 45.0))    # how deep the clamp grips (mm)

# ── Resolve active part ──────────────────────────────────────────────────────
_PARTS = ("under_desk_hook", "wall_hook", "desk_clamp")
if target_part in _PARTS:
    active = target_part
else:
    active = {
        "under_desk": "under_desk_hook",
        "wall": "wall_hook",
        "clamp": "desk_clamp",
    }.get(mount, "under_desk_hook")

# ── Clamps / derived values ──────────────────────────────────────────────────
cradle_w    = max(12.0, min(cradle_w, 80.0))
thick       = max(4.0, min(thick, 20.0))
reach       = max(20.0, reach)
drop        = max(15.0, drop)
plate_w     = max(cradle_w, plate_w)
plate_len   = max(30.0, plate_len)
screw_dia   = max(2.5, min(screw_dia, 8.0))
desk_t      = max(8.0, min(desk_t, 60.0))
clamp_depth = max(25.0, clamp_depth)

# A broad, rounded cradle: radius of the semicircular saddle the band rests in.
cradle_r = cradle_w * 0.55


# ── Helpers ──────────────────────────────────────────────────────────────────
def bar_x(length, w, h):
    """A bar running along +X, its near end at x=0, centred in Y, base at z=0."""
    return (
        cq.Workplane("XY")
        .box(length, w, h, centered=(False, True, False))
    )


def bar_z(height_, w, d):
    """A bar running along +Z, base at z=0, centred in Y, near face at x=0."""
    return (
        cq.Workplane("XY")
        .box(d, w, height_, centered=(False, True, False))
    )


def cradle(at_x, at_z, embed=2.0):
    """A broad rounded saddle whose FLOOR sits at z=at_z, for the headband. Built
    as a solid block with a horizontal half-round trough cut from the top (a
    cylinder lying along Y), giving a gentle saddle that will not dent the band.

    `embed` extends the block downward below at_z so it always overlaps the host
    part it unions onto — a coincident mating face would otherwise produce a
    non-manifold seam. Returns the solid Workplane."""
    block_h = cradle_r + thick
    block_len = cradle_r * 2.0 + thick
    base_z = at_z - embed
    block = (
        cq.Workplane("XY")
        .box(block_len, cradle_w + 2.0 * thick, block_h + embed,
             centered=(False, True, False))
        .translate((at_x, 0, base_z))
    )
    # Trough: a cylinder lying along Y, centred over the block, cut from the top.
    top_z = base_z + block_h + embed
    trough = (
        cq.Workplane("XZ")
        .circle(cradle_r)
        .extrude(cradle_w)
        .translate((at_x + block_len / 2.0, cradle_w / 2.0, top_z))
    )
    block = block.cut(trough)
    return block


def screw_holes(body, plate_face_z, points):
    """Drill vertical screw clearance holes through a plate (through +Z)."""
    r = screw_dia / 2.0
    cutter = (
        cq.Workplane("XY")
        .pushPoints(points)
        .circle(r)
        .extrude(thick + 4.0)
        .translate((0, 0, plate_face_z - 2.0))
    )
    return body.cut(cutter)


def plate_hole_points(cx, w, ln):
    """Two-hole pattern centred at (cx, 0) on a plate of size (ln × w)."""
    inset = max(screw_dia + 4.0, 8.0)
    dx = ln / 2.0 - inset
    return [(cx - dx, 0.0), (cx + dx, 0.0)]


def soften(body):
    r = min(2.0, thick * 0.35)
    try:
        body = body.edges("|Y").fillet(r)
    except Exception:
        try:
            body = body.edges("|Z").fillet(r)
        except Exception:
            pass
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_under_desk_hook():
    """L-bracket: a top mounting plate screwed under a desktop, an arm dropping
    down then a short reach forward, ending in an up-turned cradle."""
    # Top plate lies flat at z=0 (screws go up into the desk underside).
    plate = bar_x(plate_len, plate_w, thick)
    body = plate

    # Vertical arm dropping down from the front of the plate.
    arm_v = bar_z(drop, cradle_w, thick).translate((plate_len - thick, 0, -drop))
    body = body.union(arm_v)

    # Forward reach at the bottom of the drop.
    arm_h = bar_x(reach, cradle_w, thick).translate((plate_len - thick, 0, -drop))
    body = body.union(arm_h)

    # Cradle at the end of the reach, opening up.
    body = body.union(cradle(plate_len - thick + reach, -drop))

    # Screws through the top plate.
    body = screw_holes(body, 0.0, plate_hole_points(plate_len / 2.0, plate_w, plate_len))
    return soften(body)


def build_wall_hook():
    """Flat wall screw plate (vertical) with a hook arm reaching out and up into
    a cradle."""
    # Back plate stands in the XZ plane (against the wall at x=0), thickness in X.
    back = (
        cq.Workplane("XY")
        .box(thick, plate_w, plate_len, centered=(False, True, False))
    )
    body = back

    # Arm reaching out from partway up the plate.
    arm_z = plate_len * 0.5
    arm = bar_x(reach, cradle_w, thick).translate((thick, 0, arm_z))
    body = body.union(arm)

    # Cradle at the end, opening up.
    body = body.union(cradle(thick + reach, arm_z))

    # Screw holes through the back plate (bored along +X).
    inset = max(screw_dia + 4.0, 8.0)
    dz = plate_len / 2.0 - inset
    pts_z = [plate_len / 2.0 - dz, plate_len / 2.0 + dz]
    r = screw_dia / 2.0
    for zc in pts_z:
        cutter = (
            cq.Workplane("YZ")
            .circle(r)
            .extrude(thick + 4.0)
            .translate((-2.0, 0, zc))
        )
        body = body.cut(cutter)
    return soften(body)


def build_desk_clamp():
    """C-clamp gripping a desk edge of thickness `desk_t`; the cradle sits on the
    front (outer) face. No screws — a printed spring C-profile."""
    jaw = thick
    inner_gap = desk_t
    total_h = inner_gap + 2.0 * jaw

    # Solid C block: full outer envelope, then cut the desk-edge slot from +X.
    outer = (
        cq.Workplane("XY")
        .box(clamp_depth, cradle_w + 2.0 * thick, total_h, centered=(False, True, False))
    )
    # Slot the desk slides into: open at the front (+X), leaving the back spine.
    slot = (
        cq.Workplane("XY")
        .box(clamp_depth, cradle_w + 2.0 * thick + 2.0, inner_gap,
             centered=(False, True, False))
        .translate((thick, 0, jaw))
    )
    body = outer.cut(slot)

    # Cradle on the front-top of the clamp, opening up.
    body = body.union(cradle(clamp_depth - thick, total_h))

    # Ease the mouth with two 45° lead-in chamfers cut at the slot entrance so
    # the clamp slides onto the desk. Done as boolean cuts (always watertight);
    # a .fillet() on this C + cradle topology produces a non-manifold shell.
    lead = min(3.0, jaw * 0.6, clamp_depth * 0.1)
    if lead > 0.2:
        wide = cradle_w + 2.0 * thick + 4.0
        # Lower jaw lead-in (chamfer the top-front corner of the lower jaw).
        low = (
            cq.Workplane("XZ")
            .polyline([(0, 0), (lead, 0), (0, lead)])
            .close()
            .extrude(wide)
            .translate((0, wide / 2.0, jaw))
        )
        # Upper jaw lead-in (chamfer the bottom-front corner of the upper jaw).
        high = (
            cq.Workplane("XZ")
            .polyline([(0, 0), (lead, 0), (0, -lead)])
            .close()
            .extrude(wide)
            .translate((0, wide / 2.0, jaw + inner_gap))
        )
        body = body.cut(low).cut(high)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active == "wall_hook":
    result = build_wall_hook()
elif active == "desk_clamp":
    result = build_desk_clamp()
else:
    result = build_under_desk_hook()
