"""
Pi DIN Carrier — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A single-board computer, clipped onto TS35 top-hat rail.

Industrial deployment is standard-shaped, not bespoke. A control cabinet is a
length of DIN EN 60715 TS35 rail and a row of things that clip to it, and the
commons already has seven of those things — `din-module`, `din-relay`,
`din-rail-clip`, `din-terminal-comb`, `terminal-cover`, `busbar-support`,
`devboard-tray`. It also has two cartridges built around the Raspberry Pi hole
pattern — `pi-hat-case` and `sbc-case`. Nothing joined the two families, so a
board that is being deployed *industrially* had to be zip-tied to something.

This carrier is that joint: the Raspberry Pi HAT / Model B mounting pattern on
one face, the TS35 rail interface on the other. Nine live cartridges mate it,
every one of them on a genuine numbered standard.

Modes are dispatched via `target_part`:
  * "rail_carrier" — the carrier itself: a plate with a rigid reference hook and
                     a COMPLIANT sprung hook on the TS35 span, and standoffs on
                     the board pattern.
  * "hat_hood"     — a vented hood that bolts to the SAME pattern and clears a
                     HAT stack: finger protection and dust cover in one part.
  * "riser_frame"  — a stacking frame that lifts a second board on the same
                     pattern, with a cable window through the middle.

Rail geometry is not invented here. RAIL_SPAN / RAIL_DEPTH / LIP_GRIP and the
hook profile mirror `din-module`'s published geometry exactly, because a carrier
that grips a rail 0.2 mm differently from the module beside it is a second
convention, not an interface.

Watertightness strategy (the traps this batch inherited):
  * Union OVERLAPS, never tangents. Every standoff, boss and hook straddles the
    plate it grows from in Z, so the intersection is volumetric at EVERY
    parameter combination rather than only the default one.
  * Every cut is bounded INSIDE the blank that must contain it, with a margin
    that scales with the blank — a cut that reaches an edge is a cut-off, not a
    slot, and it opens the shell.
  * Vent slots are counted from the space actually available and skipped
    entirely when there is none, rather than being clamped into an overlap with
    the standoffs they must avoid.
  * No sealed void: the hood is open at its bottom, the frame is open through
    its window, and every standoff bore opens at the top face.
  * No fillet is taken on any edge a bore or a slot has touched.

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


# ── DIN EN 60715 TS35 top-hat rail ───────────────────────────────────────────
# Mirrors `din-module`'s published constants so a carrier and a module grip the
# same rail identically. TS35 comes in two depths: 35 x 7.5 and 35 x 15.
RAIL_SPAN = 35.0        # across the two rolled lips (catch to catch)
LIP_GRIP = 5.0          # rolled-lip turn-back — the depth a hook can catch
CLEAR = 0.35            # printed fit clearance on the rail
HOOK_WALL = 2.6

# Raspberry Pi HAT / Model B mounting spec. Both figures are the published
# pattern, not measurements of one board.
PI_HOLE_DX = 58.0
PI_HOLE_DY = 49.0

OVERLAP = 1.0           # volumetric union margin, in Z


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "rail_carrier"))
rail_depth_class = str(PARAM(lambda: rail_depth_class, "ts35_7v5"))
vent_style = str(PARAM(lambda: vent_style, "slots"))

hole_dx = float(PARAM(lambda: hole_dx, PI_HOLE_DX))
hole_dy = float(PARAM(lambda: hole_dy, PI_HOLE_DY))
hole_dia = float(PARAM(lambda: hole_dia, 2.75))
standoff_h = float(PARAM(lambda: standoff_h, 6.0))
plate_th = float(PARAM(lambda: plate_th, 3.2))
rail_len = float(PARAM(lambda: rail_len, 56.0))
spring_thick = float(PARAM(lambda: spring_thick, 2.0))
board_margin = float(PARAM(lambda: board_margin, 4.0))
hood_h = float(PARAM(lambda: hood_h, 26.0))

# Input clamps, matching the manifest slider bounds exactly.
hole_dx = max(20.0, min(hole_dx, 90.0))
hole_dy = max(15.0, min(hole_dy, 80.0))
hole_dia = max(2.2, min(hole_dia, 4.5))
standoff_h = max(3.0, min(standoff_h, 20.0))
plate_th = max(2.5, min(plate_th, 8.0))
rail_len = max(20.0, min(rail_len, 120.0))
spring_thick = max(1.2, min(spring_thick, 4.0))
board_margin = max(2.0, min(board_margin, 15.0))
hood_h = max(10.0, min(hood_h, 60.0))

RAIL_DEPTH = 15.0 if rail_depth_class == "ts35_15" else 7.5


# ── Derived, clamped against FINAL values ────────────────────────────────────
JAW_H = RAIL_DEPTH + 2.5
CATCH = max(1.5, min(LIP_GRIP - 1.0, 3.0))

# The plate must contain the board pattern AND the rail hooks, whichever is
# wider. Derived from both rather than assumed, because a Pi Zero pattern is
# narrower than the rail and a Pi 5 pattern is wider.
BOSS_R = max(hole_dia * 0.5 + 1.6, 3.0)

# The board footprint governs every mode. The RAIL governs only the mode that
# touches a rail: folding rail_len into the hood and the frame made two parts
# that never see a rail grow when the rail length was raised, which is both
# wrong and how ALL-MIN produced a 60 mm frame from a 25 mm pattern.
BOARD_W = hole_dx + 2.0 * BOSS_R + 2.0 * board_margin
BOARD_L = hole_dy + 2.0 * BOSS_R + 2.0 * board_margin
ON_RAIL = target_part == "rail_carrier"
PLATE_W = max(BOARD_W, RAIL_SPAN + 2.0 * HOOK_WALL + 4.0) if ON_RAIL else BOARD_W
PLATE_L = max(BOARD_L, rail_len + 4.0) if ON_RAIL else BOARD_L
HOOK_LEN = min(rail_len, PLATE_L - 2.0)


def _hole_points():
    """The four board mounting-hole centres, on the declared pattern."""
    return [(sx * hole_dx / 2.0, sy * hole_dy / 2.0)
            for sx in (-1.0, 1.0) for sy in (-1.0, 1.0)]


def _extrude_profile_xz(pts, length):
    """Close (x, z) points on XZ and extrude symmetrically about Y = 0."""
    return cq.Workplane("XZ").polyline(pts).close().extrude(length / 2.0, both=True)


def _fixed_hook():
    """Rigid hook on the +X side — the fixed reference jaw.

    Profile mirrors `din-module`'s, so the two cartridges grip the same rail the
    same way. Its top edge lands at `plate_th`, inside the plate it fuses to, so
    the union has volume in Z rather than meeting the plate at a face."""
    x_in = RAIL_SPAN / 2.0 - CLEAR
    x_wall = RAIL_SPAN / 2.0 + HOOK_WALL
    x_catch = x_in - CATCH
    pts = [
        (x_catch, plate_th), (x_wall, plate_th),
        (x_wall, -JAW_H), (x_catch, -JAW_H),
        (x_catch, -JAW_H + HOOK_WALL), (x_in, -JAW_H + HOOK_WALL),
        (x_in, 0.0), (x_catch, 0.0),
    ]
    return _extrude_profile_xz(pts, HOOK_LEN)


def _spring_hook():
    """COMPLIANT sprung hook on the -X side: a slender folded cantilever that
    flexes out over the lip and springs back to grip.

    The bend energy lives in the beam geometry, so the wall is never held in
    permanent strain and the print does not creep off the rail over months in a
    warm cabinet. `spring_thick` sets the stiffness."""
    t = spring_thick
    x_lip = -RAIL_SPAN / 2.0
    x_out = x_lip - CLEAR
    x_root_in = x_lip + 7.0
    x_catch = x_out + CATCH
    outer = [
        (x_root_in, plate_th), (x_out, plate_th),
        (x_out, -JAW_H), (x_catch, -JAW_H),
    ]
    inner = [
        (x_catch, -JAW_H + t), (x_out + t, -JAW_H + t),
        (x_out + t, plate_th - t - 2.0), (x_root_in, plate_th - t - 2.0),
    ]
    return _extrude_profile_xz(outer + inner, HOOK_LEN)


def _standoffs(z0, height, bore_depth, bore_r):
    """Four bosses on the board pattern, each with a bore open at its top face.

    Returned as a list so the caller unions them into a plate they overlap in Z
    and cuts the bores afterwards — a boss placed to *touch* a plate is a
    tangential union and renders an open shell."""
    solids = []
    for (x, y) in _hole_points():
        solids.append(
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, z0))
            .circle(BOSS_R)
            .extrude(height)
        )
    bores = []
    for (x, y) in _hole_points():
        bores.append(
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, z0 + height - bore_depth))
            .circle(bore_r)
            .extrude(bore_depth + 1.0)
        )
    return solids, bores


def _vent_window(outer_w, outer_l, rim):
    """The rectangle a vent is allowed to occupy: strictly INSIDE the standoff
    ring, and strictly inside the plate.

    The keepout is the boss pattern, not the plate edge. Sizing it from the edge
    let a slot run under a standoff at a large plate margin — the boss then sits
    over a hole, which is a weak boss and a sliver in the mesh, and nothing in
    the kernel or the mesh checker objects."""
    win_w = min(hole_dx - 2.0 * BOSS_R - 2.0, outer_w - 2.0 * rim)
    win_l = min(hole_dy - 2.0 * BOSS_R - 2.0, outer_l - 2.0 * rim)
    return win_w, win_l


def _vent(body, z0, th, inner_w, inner_l):
    """Cut vents through a plate, inside the window `_vent_window` allows.

    The slot count is derived from the space that actually EXISTS — not picked
    first and clamped afterwards. A count trimmed after the fact is how a vent
    ends up crossing the boss it was meant to avoid."""
    if vent_style == "none":
        return body
    if inner_w < 6.0 or inner_l < 6.0:
        return body

    if vent_style == "slots":
        slot_w = 3.0
        pitch = slot_w + 3.0
        n = int(math.floor(inner_w / pitch))
        if n < 1:
            return body
        span = (n - 1) * pitch
        for i in range(n):
            x = -span / 2.0 + i * pitch
            tool = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, 0.0, z0 - 1.0))
                .box(slot_w, inner_l, th + 2.0, centered=(True, True, False))
            )
            try:
                body = body.cut(tool)
            except Exception:
                pass
        return body

    # "holes": a bounded grid of round vents
    hole_r = 1.6
    pitch = hole_r * 2.0 + 2.4
    nx = int(math.floor(inner_w / pitch))
    ny = int(math.floor(inner_l / pitch))
    if nx < 1 or ny < 1:
        return body
    sx = (nx - 1) * pitch
    sy = (ny - 1) * pitch
    pts = [(-sx / 2.0 + i * pitch, -sy / 2.0 + j * pitch)
           for i in range(nx) for j in range(ny)]
    tool = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, z0 - 1.0))
        .pushPoints(pts)
        .circle(hole_r)
        .extrude(th + 2.0)
    )
    try:
        body = body.cut(tool)
    except Exception:
        pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_rail_carrier():
    """Carrier plate: TS35 hooks below, board standoffs above."""
    body = (
        cq.Workplane("XY")
        .box(PLATE_W, PLATE_L, plate_th, centered=(True, True, False))
    )

    vw, vl = _vent_window(PLATE_W, PLATE_L, 3.0)
    body = _vent(body, 0.0, plate_th, vw, vl)

    body = body.union(_fixed_hook())
    body = body.union(_spring_hook())

    # Standoffs start BELOW the plate top so the fuse is volumetric.
    bore_r = max(0.8, hole_dia * 0.5 - 0.35)   # self-tapping bore for an M2.5
    solids, bores = _standoffs(plate_th - OVERLAP, standoff_h + OVERLAP,
                               standoff_h * 0.8, bore_r)
    for s in solids:
        body = body.union(s)
    for b in bores:
        body = body.cut(b)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_hat_hood():
    """A vented hood on the same board pattern, clearing a HAT stack.

    Open at the bottom by construction: a closed box would trap a void, and a
    sealed void meshes as two bodies however valid the kernel says the solid is."""
    wall = max(2.0, plate_th * 0.7)
    # Derive the hood from the pattern AND its own wall, so the inner cavity
    # face always clears the bosses by 1 mm. At ALL-MIN the plate-derived size
    # put the boss surface at exactly the cavity wall — tangent, coincident
    # faces, 8 non-manifold edges, and a kernel that reported success.
    hood_w = max(PLATE_W, hole_dx + 2.0 * BOSS_R + 2.0 * wall + 2.0)
    hood_l = max(PLATE_L, hole_dy + 2.0 * BOSS_R + 2.0 * wall + 2.0)

    outer = cq.Workplane("XY").box(hood_w, hood_l, hood_h, centered=(True, True, False))
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, -1.0))
        .box(hood_w - 2.0 * wall, hood_l - 2.0 * wall, hood_h - wall + 1.0,
             centered=(True, True, False))
    )
    body = outer.cut(cavity)

    vw, vl = _vent_window(hood_w, hood_l, wall + 2.0)
    body = _vent(body, hood_h - wall, wall, vw, vl)

    # Bolt bosses hanging INSIDE the hood on the board pattern, straddling the
    # roof they hang from. Each is through-bored so a screw passes.
    boss_h = max(4.0, hood_h - wall - standoff_h)
    boss_z = hood_h - wall - boss_h
    for (x, y) in _hole_points():
        if abs(x) > hood_w / 2.0 - wall - 0.5 or abs(y) > hood_l / 2.0 - wall - 0.5:
            continue
        boss = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, boss_z))
            .circle(BOSS_R)
            .extrude(boss_h + OVERLAP)
        )
        body = body.union(boss)
    thru = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, boss_z - 1.0))
        .pushPoints(_hole_points())
        .circle(max(0.9, hole_dia * 0.5 + 0.2))
        .extrude(hood_h + 2.0)
    )
    body = body.cut(thru)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_riser_frame():
    """A stacking frame that lifts a second board on the same pattern, with a
    cable window through the middle.

    The window is what keeps this printable and what makes it useful: a solid
    riser plate would blind the GPIO header it sits over."""
    frame_th = max(2.5, plate_th * 0.8)
    body = cq.Workplane("XY").box(PLATE_W, PLATE_L, frame_th, centered=(True, True, False))

    # Cable window, bounded INSIDE the standoff ring — not derived from the
    # plate. Deriving it from the plate is what severed the frame: at a large
    # board_margin the plate outgrows the hole pattern, the window then swallows
    # the bosses, and the result is FOUR floating standoffs and a rim. Every one
    # of those five bodies is individually watertight, so `is_watertight` says
    # True and only the body count catches it. Watertight is not connected.
    win_w = hole_dx - 2.0 * BOSS_R - 4.0
    win_l = hole_dy - 2.0 * BOSS_R - 4.0
    if win_w > 6.0 and win_l > 6.0:
        win = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -1.0))
            .box(win_w, win_l, frame_th + 2.0, centered=(True, True, False))
        )
        body = body.cut(win)

    # Standoffs above, straddling the frame; a through bore for a long screw.
    solids, _ = _standoffs(frame_th - OVERLAP, standoff_h + OVERLAP, 0.0, 1.0)
    for s in solids:
        body = body.union(s)
    thru = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, -1.0))
        .pushPoints(_hole_points())
        .circle(max(0.9, hole_dia * 0.5 + 0.2))
        .extrude(frame_th + standoff_h + 3.0)
    )
    body = body.cut(thru)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "rail_carrier": build_rail_carrier,
    "hat_hood": build_hat_hood,
    "riser_frame": build_riser_frame,
}

result = _dispatch.get(target_part, build_rail_carrier)()
