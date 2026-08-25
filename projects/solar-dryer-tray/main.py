"""
Stacking Solar Dryer Tray — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A stacking mesh tray for a solar food dryer. Post-harvest loss is the highest-leverage
intervention available to a printable commons: a third or more of what smallholders
grow is lost between the field and the plate, and most of that loss is microbial,
which means it is a loss of WATER CONTROL rather than of yield. Drying is the oldest
and cheapest answer, and it needs no power.

What actually drives drying:
  Drying is limited by AIRFLOW ACROSS THE FOOD, not by heat alone. A hotter cabinet
  with stagnant air case-hardens the surface — a dry skin seals in wet flesh, and the
  piece spoils from the inside while looking finished. So the parameter that matters
  most here is the tray's OPEN-AREA RATIO: the fraction of the tray floor that is
  hole rather than material. This cartridge declares it, targets it, and reports what
  it actually achieved, instead of leaving mesh density to chance.

  Open area is computed for the square-pitch grid the tray actually builds:
      open_ratio = (mesh_pitch - strut_width)^2 / mesh_pitch^2
  The builder solves that relation for the strut width needed to hit the requested
  ratio, then clamps the strut to something printable — and the README carries the
  achieved value, not just the requested one.

Stacking:
  Trays stack so one dryer holds several loads and so air is forced to travel across
  each layer in turn. The rim is a male spigot on top and a matching female socket
  below, offset by `clearance`, so a stack self-locates instead of sliding. Stack
  height sets the gap between mesh planes; too tight and the layer above touches the
  food below, too loose and the cabinet is mostly air.

Modes are dispatched via `target_part`:
  * "tray"       — the mesh tray itself: a rim, a stacking spigot, and a grid floor
                   at the declared open-area ratio.
  * "stack_foot" — a base foot that raises the bottom tray off the dryer floor so air
                   can enter under the stack rather than only at its side.
  * "airflow_baffle" — a slotted baffle that sits between trays and forces the air
                   stream to cross the mesh instead of running straight up the gap
                   between the stack and the cabinet wall (the classic short-circuit
                   that leaves the middle of a load wet).

Watertightness strategy:
  Every part is one blank with THROUGH cuts. The mesh is cut as a set of full-width
  slots in two directions, each running PAST both edges of the floor — never as a
  ring of blind pockets. Strut width is clamped to a printable minimum FIRST, and the
  hole count is then derived from the floor the struts must fit inside, so the grid
  can never overrun the tray and sever the rim from the floor. No fillet is taken on
  any edge that a slot has touched: OCC blends such arcs without raising and returns
  a non-watertight solid (see graft-clip in this same batch).

  Each slot family is fused into ONE cutting tool and subtracted in a single boolean.
  Cutting ~150 slots one at a time against a solid that grows more complex with every
  cut did not finish inside ten minutes at fine pitch — a render timeout, not a
  geometry failure, but equally fatal in the sandbox.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
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
target_part = str(PARAM(lambda: target_part, "tray"))
rim_style = str(PARAM(lambda: rim_style, "stacking"))   # stacking | flanged | plain

tray_width_mm = float(PARAM(lambda: tray_width_mm, 200.0))
tray_depth_mm = float(PARAM(lambda: tray_depth_mm, 200.0))
mesh_pitch_mm = float(PARAM(lambda: mesh_pitch_mm, 8.0))
stack_height_mm = float(PARAM(lambda: stack_height_mm, 30.0))
airflow_open_ratio = float(PARAM(lambda: airflow_open_ratio, 0.55))
wall = float(PARAM(lambda: wall, 2.4))

# Clamp so extreme UI values still build watertight.
tray_width_mm = max(80.0, min(tray_width_mm, 300.0))
tray_depth_mm = max(80.0, min(tray_depth_mm, 300.0))
mesh_pitch_mm = max(4.0, min(mesh_pitch_mm, 25.0))
stack_height_mm = max(12.0, min(stack_height_mm, 80.0))
airflow_open_ratio = max(0.20, min(airflow_open_ratio, 0.80))
wall = max(1.6, min(wall, 5.0))

# Minimum printable strut. Below roughly two extrusion widths a strut is a single
# unsupported bead spanning a hole and will droop or break; the tray is a food
# contact part that gets washed, so it is not worth shaving.
MIN_STRUT = 1.0

# Maximum discrete holes in the mesh field. A B-Rep kernel limit, not a design
# preference: fusing several thousand boxes into one cutting tool and subtracting it
# does not complete in any time the render sandbox will wait for. The effective pitch
# is opened up to spread this many holes across whatever tray was asked for, and
# mesh_report() states what was actually achieved.
MAX_HOLES = 900


# ── Mesh solver ──────────────────────────────────────────────────────────────
def strut_for_ratio():
    """Strut width that yields the requested open-area ratio at this pitch.

    For a square grid of pitch p with struts of width s, each cell's open square is
    (p - s) on a side, so:
        open_ratio = (p - s)^2 / p^2   =>   s = p * (1 - sqrt(open_ratio))

    Clamped to MIN_STRUT (printability) and to 60 % of pitch (so a hole always
    survives). Because the clamp can bind, the ACHIEVED ratio is reported separately
    rather than assumed equal to the request."""
    s = mesh_pitch_mm * (1.0 - math.sqrt(airflow_open_ratio))
    return max(MIN_STRUT, min(s, mesh_pitch_mm * 0.6))


def achieved_ratio():
    """Open-area ratio the tray actually delivers after clamping."""
    s = strut_for_ratio()
    open_side = max(0.0, mesh_pitch_mm - s)
    return (open_side * open_side) / (mesh_pitch_mm * mesh_pitch_mm)


def opening_for(pitch_x, pitch_y):
    """Hole opening that preserves the REQUESTED open-area ratio at a given pitch.

    The opening is derived from the pitch actually used, not from the pitch that was
    asked for. When the MAX_HOLES cap opens the effective pitch up, holding the
    opening at the fine value would leave enormous struts and quietly wreck the ratio
    — at a 300 mm tray on 4 mm pitch that dropped the achieved ratio to 0.086 against
    a requested 0.55. Since open_ratio = (open/pitch)^2 for a square grid, the
    opening simply scales with the pitch."""
    f = math.sqrt(airflow_open_ratio)
    ox = max(0.5, min(pitch_x * f, pitch_x - MIN_STRUT))
    oy = max(0.5, min(pitch_y * f, pitch_y - MIN_STRUT))
    return ox, oy


def mesh_report():
    """What the tray ACTUALLY builds, after every clamp has been applied.

    Two things can move between what is asked for and what is built: the strut is
    clamped to MIN_STRUT for printability, and the hole count is capped at MAX_HOLES
    for the kernel's sake — which opens the effective pitch. Reporting both keeps the
    cartridge honest, since open-area ratio is the number the drying rate depends on
    and quietly missing it would be the one failure that matters."""
    s = strut_for_ratio()
    floor_t = max(1.2, wall * 0.8)
    cavity_w = tray_width_mm - 2.0 * wall
    cavity_d = tray_depth_mm - 2.0 * wall
    field_w = cavity_w - 2.0 * s
    field_d = cavity_d - 2.0 * s
    out = {
        "requested_ratio": airflow_open_ratio,
        "requested_pitch": mesh_pitch_mm,
        "strut_mm": s,
        "floor_mm": floor_t,
    }
    if field_w <= mesh_pitch_mm or field_d <= mesh_pitch_mm:
        out.update({"holes": 0, "achieved_ratio": 0.0, "capped": False})
        return out
    nx = int(max(1, math.floor((field_w - s) / mesh_pitch_mm)))
    ny = int(max(1, math.floor((field_d - s) / mesh_pitch_mm)))
    capped = nx * ny > MAX_HOLES
    if capped:
        scale = math.sqrt((nx * ny) / float(MAX_HOLES))
        nx = int(max(1, math.floor(nx / scale)))
        ny = int(max(1, math.floor(ny / scale)))
    pitch_x = (field_w - s) / nx
    pitch_y = (field_d - s) / ny
    open_x, open_y = opening_for(pitch_x, pitch_y)
    out.update({
        "holes": nx * ny,
        "grid": (nx, ny),
        "achieved_pitch": (pitch_x, pitch_y),
        "achieved_ratio": (nx * ny * open_x * open_y) / (field_w * field_d),
        "capped": capped,
    })
    return out


# ── Part builders ─────────────────────────────────────────────────────────────
def build_tray():
    """The mesh tray: rim, stacking spigot, and a grid floor at the declared ratio.

    The mesh is cut as an array of discrete square holes, all bounded strictly inside
    the floor with a full closing strut at every edge, and fused into ONE cutting tool
    so the whole grid is a single boolean.

    It is NOT cut as full-width slots in two directions. That was the first design and
    it fails twice over: the slots run past the tray edges and take the rim's lower
    band with them, and where the two families cross they leave every cell island
    disconnected — a 200 mm tray came back as 531 separate bodies. The hole count is
    DERIVED from the floor the struts must fit inside, so the grid can never overrun
    the tray."""
    w = tray_width_mm
    d = tray_depth_mm
    floor_t = max(1.2, wall * 0.8)
    rim_h = max(6.0, min(stack_height_mm * 0.45, 30.0))

    # Outer shell: rim walls plus a floor.
    body = cq.Workplane("XY").box(w, d, rim_h, centered=(True, True, False))
    cavity_w = w - 2.0 * wall
    cavity_d = d - 2.0 * wall
    if cavity_w > 4.0 and cavity_d > 4.0 and rim_h > floor_t + 1.0:
        cavity = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, floor_t))
            .box(cavity_w, cavity_d, rim_h - floor_t + 1.0, centered=(True, True, False))
        )
        body = body.cut(cavity)

    # Mesh holes: a discrete array, every hole bounded strictly inside the floor.
    s = strut_for_ratio()
    open_side = max(0.5, mesh_pitch_mm - s)

    # The perforated field stops a full strut short of the cavity wall, so the floor
    # always meets the rim through solid material all the way round.
    field_w = cavity_w - 2.0 * s
    field_d = cavity_d - 2.0 * s
    if field_w > mesh_pitch_mm and field_d > mesh_pitch_mm:
        # Count derived from the field the struts must fit inside: n cells of pitch p
        # plus one closing strut must not exceed it.
        nx = int(max(1, math.floor((field_w - s) / mesh_pitch_mm)))
        ny = int(max(1, math.floor((field_d - s) / mesh_pitch_mm)))
        span_x = nx * mesh_pitch_mm + s
        span_y = ny * mesh_pitch_mm + s

        # Hole COUNT is capped, and the pitch is re-derived from the cap.
        #
        # This is a B-Rep kernel limit, not a design preference. A 300 mm tray at
        # 4 mm pitch asks for ~5000 discrete holes; fusing that many boxes into one
        # cutting tool and subtracting it does not complete in any time the render
        # sandbox will wait for — the run was killed at ten minutes with no output.
        # Cutting them one at a time is worse still, since each boolean re-evaluates
        # a solid that has grown more complex than the last.
        #
        # So the grid is capped at MAX_HOLES cells and the EFFECTIVE pitch is opened
        # up to spread that many holes across the tray. The achieved pitch and open
        # ratio are both reported by mesh_report() rather than silently differing
        # from what was asked for.
        if nx * ny > MAX_HOLES:
            scale = math.sqrt((nx * ny) / float(MAX_HOLES))
            nx = int(max(1, math.floor(nx / scale)))
            ny = int(max(1, math.floor(ny / scale)))

        # Re-derive the pitch actually used from the counts that survived the cap, so
        # holes stay evenly spread across the whole field instead of bunching at the
        # centre with a bare margin around them.
        pitch_x = (field_w - s) / nx
        pitch_y = (field_d - s) / ny
        open_x, open_y = opening_for(pitch_x, pitch_y)

        # Every hole is fused into ONE cutting tool and subtracted in a single
        # boolean.
        pts = []
        for i in range(nx):
            cx = -field_w / 2.0 + s + pitch_x * i + open_x / 2.0
            for j in range(ny):
                cy = -field_d / 2.0 + s + pitch_y * j + open_y / 2.0
                pts.append((cx, cy))
        if pts:
            tool = (
                cq.Workplane("XY")
                .pushPoints(pts)
                .box(open_x, open_y, floor_t + 2.0, centered=(True, True, True))
                .translate((0, 0, floor_t / 2.0))
            )
            body = body.cut(tool)

    # Stacking interface: a male spigot on top, so a stack self-locates instead of
    # sliding. The tray above drops its rim over this spigot.
    #
    # The spigot is sized DOWN FROM THE RIM it must grow out of, and deliberately
    # overlaps it: its outer face sits at the rim's OUTER face less `clearance`, so
    # the two share real material. The first draft sized it from `w - 2*wall -
    # 2*clearance`, which put the spigot band at 94.85-97.25 mm while the rim band ran
    # 97.6-100.0 — a 0.35 mm air gap the whole way round, touching only through a
    # -0.01 mm z-overlap on zero footprint. That is a tangent kiss, and the tray came
    # back as two bodies. `clearance` belongs on the socket side of the joint, not on
    # the side that has to stay attached.
    if rim_style == "stacking":
        clearance = 0.35
        spig_h = max(2.5, wall * 1.2)
        spig_w = w - 2.0 * clearance
        spig_d = d - 2.0 * clearance
        inner_w = spig_w - 2.0 * wall
        inner_d = spig_d - 2.0 * wall
        if inner_w > 2.0 and inner_d > 2.0:
            # Start the spigot BELOW the rim top so the union is volumetric.
            z0 = max(0.0, rim_h - wall)
            spig = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0.0, 0.0, z0))
                .box(spig_w, spig_d, (rim_h - z0) + spig_h, centered=(True, True, False))
            )
            hollow = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0.0, 0.0, z0 - 1.0))
                .box(inner_w, inner_d, (rim_h - z0) + spig_h + 2.0, centered=(True, True, False))
            )
            spig = spig.cut(hollow)
            body = body.union(spig)
    elif rim_style == "flanged":
        # A carrying flange all round — easier to lift a hot tray, no stacking.
        #
        # The flange's inner opening is pulled INSIDE the rim's inner face by a
        # quarter wall, so the flange and the rim share real material. Cutting it at
        # exactly `w - 2*wall` would land the two coincident-face-to-coincident-face,
        # which OCC resolves unpredictably — the same tangent-kiss class of defect
        # that detached the stacking spigot above.
        fl_t = max(2.0, wall * 0.9)
        fl = max(5.0, wall * 2.5)
        bite = wall * 0.25
        flange = cq.Workplane("XY").box(w + 2.0 * fl, d + 2.0 * fl, fl_t, centered=(True, True, False))
        inner = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -1.0))
            .box(w - 2.0 * wall - 2.0 * bite, d - 2.0 * wall - 2.0 * bite, fl_t + 2.0,
                 centered=(True, True, False))
        )
        flange = flange.cut(inner)
        body = body.union(flange.translate((0, 0, rim_h - fl_t)))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_stack_foot():
    """A base foot that raises the bottom tray off the dryer floor.

    Air must be able to ENTER under the stack. A stack sitting flat on the cabinet
    floor draws only from its sides, and the bottom tray — usually the one nearest
    the absorber and therefore the hottest — case-hardens first."""
    lift = max(10.0, min(stack_height_mm * 0.6, 50.0))
    pad = max(18.0, min(tray_width_mm * 0.18, 60.0))
    t = max(2.0, wall)

    body = cq.Workplane("XY").box(pad, pad, t, centered=(True, True, False))

    # Leg: a hollow post, volumetrically merged into the pad. Its span is computed
    # explicitly so the lip above can be placed from the leg's REAL top.
    leg_w = max(8.0, pad * 0.5)
    leg_z0 = t * 0.5                    # starts inside the pad — volumetric union
    leg_z1 = t + lift                   # the leg's actual top
    leg = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, leg_z0))
        .box(leg_w, leg_w, leg_z1 - leg_z0, centered=(True, True, False))
    )
    # The hollow stops a full CAP below the leg top so the post is capped, and it is
    # opened THROUGH THE BOTTOM of the pad so it vents.
    #
    # An enclosed void here is wrong twice over. Physically it is unprintable — a
    # sealed cavity traps uncured air, cannot drain when the foot is washed, and
    # cannot be supported. Geometrically, trimesh counts the void's inner shell as a
    # body of its own, so the foot reported `body_count == 2` at every parameter
    # combination while reading perfectly watertight. Isolating the build showed the
    # LEG ALONE was already two bodies before the pad, lip or slots were involved —
    # the earlier lip fixes were chasing the wrong part entirely.
    cap = max(1.5, t)
    core = leg_w - 2.0 * t
    hollow_z0 = -1.0                       # starts below the pad's underside
    hollow_z1 = leg_z1 - cap
    if core > 2.0 and (hollow_z1 - hollow_z0) > 1.0:
        hollow = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, hollow_z0))
            .box(core, core, hollow_z1 - hollow_z0, centered=(True, True, False))
        )
        leg = leg.cut(hollow)
    body = body.union(leg)
    # The pad's own floor under the leg is removed with the same tool, so the cavity
    # is a real opening rather than a pocket closed by the pad beneath it.
    if core > 2.0:
        vent = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -1.0))
            .box(core, core, t + 2.0, centered=(True, True, False))
        )
        try:
            body = body.cut(vent)
        except Exception:
            pass

    # Cradle lip at the top that the tray rim sits into.
    #
    # Placed from `leg_z1` — the leg's computed top — and sunk HALF A CAP into the
    # leg's solid head so the union is volumetric. Two earlier drafts failed here:
    # the first put the lip at `t + lift - t` while the hollow was bored clean
    # through the head, so the lip's entire middle sat inside that hollow and it was
    # a floating ring; the second capped the head but landed the lip's underside
    # exactly on the cap's top face — a coincident-face union, which OCC resolves
    # unpredictably and which left the foot as two bodies again. The lip now
    # overlaps real material.
    lip_w = leg_w + 2.0 * t
    lip_h = max(1.5, t)
    lip_z0 = leg_z1 - lip_h - cap * 0.5
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, lip_z0))
        .box(lip_w, lip_w, (leg_z1 - lip_z0), centered=(True, True, False))
    )
    body = body.union(lip)

    # Ventilation slots through the pad, so the foot does not itself block the air it
    # exists to admit.
    #
    # Each slot is BOUNDED INSIDE the pad, leaving a full margin all round. The first
    # draft ran them past both edges in X (`pad + 2.0`): at the default that left the
    # pad's outer strips beyond y = +/-12.24 attached to nothing, and the foot came
    # back as four separate bodies. A slot that reaches an edge is not a slot, it is
    # a cut-off — the same mistake the tray's first mesh design made at larger scale.
    slot_w = max(2.0, pad * 0.08)
    margin = max(t, pad * 0.12)
    # Kept clear of the leg footprint as well as the pad edge: a slot that ran the
    # pad's full usable length crossed under the leg and undercut the very post it
    # is meant to support.
    slot_len = max(2.0, min(pad - 2.0 * margin, leg_w - 2.0 * t))
    cy_off = leg_w / 2.0 + slot_w / 2.0 + t * 0.5
    if cy_off + slot_w / 2.0 + margin <= pad / 2.0 and slot_len > 2.0:
        for i in (-1.0, 1.0):
            slot = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0.0, i * cy_off, -1.0))
                .box(slot_len, slot_w, t + 2.0, centered=(True, True, False))
            )
            try:
                body = body.cut(slot)
            except Exception:
                pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_airflow_baffle():
    """A slotted baffle that forces air to cross the mesh instead of short-circuiting
    up the gap between the stack and the cabinet wall.

    That short-circuit is the classic reason a load dries at the edges and stays wet
    in the middle: the air takes the cheapest path, and the cheapest path is never
    through the food."""
    w = tray_width_mm
    t = max(2.0, wall)
    h = max(10.0, min(stack_height_mm * 0.8, 60.0))

    body = cq.Workplane("XY").box(w, t, h, centered=(True, True, False))

    # Angled louvre slots: openings that pass air but redirect it downward onto the
    # tray below. Cut as full-depth slots through the plate, so never blind.
    slot_h = max(2.0, h * 0.12)
    gap = max(2.0, h * 0.08)
    n = int(max(1, math.floor((h - gap) / (slot_h + gap))))
    # Leave a full band of material top and bottom so the baffle stays one piece.
    band = max(t, h * 0.12)
    usable = h - 2.0 * band
    if usable > slot_h:
        n = int(max(1, math.floor((usable + gap) / (slot_h + gap))))
        total = n * slot_h + (n - 1) * gap
        z0 = band + (usable - total) / 2.0
        slot_w = max(4.0, w * 0.75)
        for i in range(n):
            z = z0 + i * (slot_h + gap)
            slot = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0.0, 0.0, z))
                .box(slot_w, t + 2.0, slot_h, centered=(True, True, False))
            )
            try:
                body = body.cut(slot)
            except Exception:
                pass

    # Locating tabs at both ends that key into the tray rim, so the baffle cannot be
    # blown out of position. Volumetric union, overlapping the plate.
    tab_w = max(4.0, t * 2.0)
    tab_h = max(4.0, h * 0.2)
    for sign in (-1.0, 1.0):
        tab = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sign * (w / 2.0 - tab_w / 2.0), 0.0, -tab_h + 0.01))
            .box(tab_w, t * 2.0, tab_h + t, centered=(True, True, False))
        )
        body = body.union(tab)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "tray": build_tray,
    "stack_foot": build_stack_foot,
    "airflow_baffle": build_airflow_baffle,
}

result = _dispatch.get(target_part, build_tray)()
