"""
Raised-Bed / Planter Corner Bracket — Yantra4D Hyperobject Cartridge (CadQuery).

Joins dimensional lumber into a raised garden bed or planter box without metal
brackets or angled cuts. Each arm is a three-sided channel (the CDG "Board Slot")
that a board end slides into; screws through the pilot holes lock it. Three parts:
a 90° corner joining two boards, a tall stackable corner for deep beds, and a tee
that lets a board cross the middle of a long side.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `board_t`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "corner_90"))  # corner_90 | corner_tall | tee_join

board_t     = float(PARAM(lambda: board_t,   38.0))   # board thickness (e.g. 1.5in ~ 38 mm)
board_w     = float(PARAM(lambda: board_w,  140.0))   # board width / face height (e.g. 6in ~ 140 mm)
slot_depth  = float(PARAM(lambda: slot_depth, 60.0))  # how far the board end slides into the arm
wall        = float(PARAM(lambda: wall,       6.0))   # channel wall thickness
clearance   = float(PARAM(lambda: clearance,  0.6))   # slot slack around the board (per side)
corner_r    = float(PARAM(lambda: corner_r,   5.0))   # outer vertical corner rounding
screw_dia   = float(PARAM(lambda: screw_dia,  4.5))   # pilot-hole diameter
stack_lug   = bool( PARAM(lambda: stack_lug, True))   # stacking spigot/socket (corner_tall)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
board_t    = max(12.0, min(board_t, 90.0))
board_w    = max(60.0, min(board_w, 300.0))
slot_depth = max(25.0, min(slot_depth, 150.0))
wall       = max(3.0, min(wall, 14.0))
clearance  = max(0.2, min(clearance, 1.5))
corner_r   = max(0.0, min(corner_r, 12.0))
screw_dia  = max(2.5, min(screw_dia, 8.0))

# Slot inner size = board + clearance per side.
slot_t = board_t + 2.0 * clearance
# Arm footprint (in the horizontal plane) = slot + walls on both faces.
arm_thick = slot_t + 2.0 * wall
# Arm reach from the corner axis along its direction.
arm_len = slot_depth + wall


def _arm(height, base_z=0.0):
    """One board channel along +X: a solid block hollowed by a board-shaped slot
    open on the +X end and the top. Origin at the inner corner; the channel wall
    faces are perpendicular to Y. Returns the arm solid.

    The block spans x:[0, arm_len], centered on Y with total width arm_thick,
    z:[base_z, base_z+height]. The slot (board pocket) spans x:[wall, arm_len+1]
    open toward +X, centered on Y with width slot_t, full height (open top)."""
    block = (
        cq.Workplane("XY")
        .box(arm_len, arm_thick, height, centered=(False, True, False))
        .translate((0, 0, base_z))
    )
    # Board slot: open on +X end. Leave a back stop of `wall` at the corner side.
    slot = (
        cq.Workplane("XY")
        .box(arm_len, slot_t, height + 2.0, centered=(False, True, False))
        .translate((wall, 0, base_z - 1.0))
    )
    block = block.cut(slot)
    return block


def _screws_on_arm(solid, height, base_z, direction):
    """Drill two pilot holes through the OUTER face of an arm so screws bite into
    the board edge. `direction` is 'x' (arm along +X, drill along Y) or 'y'."""
    z1 = base_z + height * 0.30
    z2 = base_z + height * 0.70
    xs = arm_len * 0.55
    for zc in (z1, z2):
        if direction == "x":
            hole = (
                cq.Workplane("XZ")
                .circle(screw_dia / 2.0)
                .extrude(arm_thick + 4.0)
                .translate((xs, arm_thick / 2.0 + 2.0, zc))
            )
        else:  # arm along +Y, drill through X faces
            hole = (
                cq.Workplane("YZ")
                .circle(screw_dia / 2.0)
                .extrude(arm_thick + 4.0)
                .translate((arm_thick / 2.0 + 2.0, xs, zc))
            )
        solid = solid.cut(hole)
    return solid


def _round_outer(solid):
    """Soften the free vertical outer corners for comfort and print quality."""
    if corner_r > 0.3:
        try:
            solid = solid.edges("|Z").fillet(min(corner_r, wall * 0.8, arm_thick * 0.2))
        except Exception:
            pass  # fillet is cosmetic — never fatal
    return solid


def _l_corner(height, base_z=0.0):
    """Two arms meeting at 90°: one along +X, one along +Y, sharing a solid corner
    post so the joint is rigid."""
    arm_x = _arm(height, base_z)
    arm_y = _arm(height, base_z).rotate((0, 0, 0), (0, 0, 1), 90)  # now along +Y
    # Solid corner post fills the shared inner square so the two channels fuse.
    post = (
        cq.Workplane("XY")
        .box(arm_thick, arm_thick, height, centered=(False, False, False))
        .translate((-arm_thick / 2.0, -arm_thick / 2.0, base_z))
    )
    body = post.union(arm_x).union(arm_y)
    body = _screws_on_arm(body, height, base_z, "x")
    body = _screws_on_arm(body, height, base_z, "y")
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_corner_90():
    """Standard single-height 90° corner for one board course."""
    return _round_outer(_l_corner(board_w))


def build_corner_tall():
    """A deep-bed corner: full board height plus optional stacking lugs so two
    courses of board stack with a second bracket seated on top."""
    body = _l_corner(board_w)
    if stack_lug:
        lug_r = max(4.0, wall * 0.7)
        lug_h = 8.0
        # A spigot rising from the corner post top and a matching socket bored into
        # the post bottom, so an identical bracket stacks on top.
        spigot = (
            cq.Workplane("XY")
            .circle(lug_r).extrude(lug_h)
            .translate((0, 0, board_w))
        )
        socket = (
            cq.Workplane("XY")
            .circle(lug_r + 0.35).extrude(lug_h + 1.0)
            .translate((0, 0, -0.5))
        )
        body = body.union(spigot).cut(socket)
    body = _round_outer(body)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_tee_join():
    """A tee: a straight run channel (a board passing THROUGH, along X in both
    directions) with a third channel branching at 90° along +Y — lets a cross
    board or divider tie into the middle of a long side."""
    height = board_w
    # Straight run: one long channel along X centered on the origin. The board
    # slides in from EITHER open end. The slot is inset from the block ends by
    # `wall`, leaving solid end caps that tie the front (+Y) and back (-Y) channel
    # walls together — otherwise a full-length through-slot would sever the back
    # wall into a loose second piece.
    run_len = 2.0 * arm_len
    run_block = (
        cq.Workplane("XY")
        .box(run_len, arm_thick, height, centered=(True, True, False))
    )
    run_slot = (
        cq.Workplane("XY")
        .box(run_len - 2.0 * wall, slot_t, height + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    run = run_block.cut(run_slot)

    # Branch channel along +Y. Its back-stop wall (the `wall` of solid `_arm`
    # leaves at the corner side) overlaps the run's front wall, so the branch
    # fuses to the run into one connected body — no separate web plate needed
    # (a detached web would print as a loose second piece).
    branch = _arm(height).rotate((0, 0, 0), (0, 0, 1), 90)

    body = run.union(branch)
    body = _screws_on_arm(body, height, 0.0, "y")
    # Pilot holes into the run board through the -Y back wall.
    for xc in (-arm_len * 0.55, arm_len * 0.55):
        hole = (
            cq.Workplane("XZ")
            .circle(screw_dia / 2.0).extrude(arm_thick + 4.0)
            .translate((xc, arm_thick / 2.0 + 2.0, height * 0.5))
        )
        body = body.cut(hole)
    body = _round_outer(body)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "corner_tall":
    result = build_corner_tall()
elif target_part == "tee_join":
    result = build_tee_join()
else:
    result = build_corner_90()
