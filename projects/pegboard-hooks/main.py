"""
Pegboard Hook Set — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Wall-storage accessories that snap onto a standard perforated pegboard. The peg /
insert geometry is modeled to the real board pitch so a printed part actually
seats in the holes. Two board standards are supported:

  * "us_1inch" — the North-American 1-inch pegboard (Wall Control / DuraBoard):
                 25.4 mm hole pitch on a square grid, ~6 mm round holes, boards
                 typically 4.5–6 mm thick. Round pegs enter two vertically
                 stacked holes.
  * "skadis"   — IKEA SKÅDIS: a 40 mm horizontal pitch with rows 40 mm apart and
                 offset by half a pitch; the perforations are ~5 mm-wide rounded
                 vertical slots. Accessories use an upper peg that hooks over a
                 slot and a lower retention nub that presses into the slot below.

Three parts (dispatched through `target_part`):
  * "hook"        — a J-hook to hang tools/cables, with 1–2 pegs behind it.
  * "bin"         — a small open bin that hangs on the pegs.
  * "tool_holder" — a back plate with a bored hole of `tool_dia` that cradles a
                    round tool (screwdriver, pliers handle, marker) on its pegs.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `hook_reach`).
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


# ── Board standard table ─────────────────────────────────────────────────────
# pitch_x / pitch_y : hole grid spacing (mm).
# peg_dia           : diameter of the round peg that enters a US hole.
# slot_w / slot_h   : SKÅDIS slot width/height (mm) for the flat tongue peg.
# board_t           : nominal board thickness the peg reaches behind.
# kind              : "round" (US round hole) | "slot" (SKÅDIS vertical slot).
BOARD_TABLE = {
    "us_1inch": {
        "pitch_x": 25.4, "pitch_y": 25.4,
        "peg_dia": 5.6, "board_t": 5.0, "kind": "round",
        "slot_w": 0.0, "slot_h": 0.0,
    },
    "skadis": {
        "pitch_x": 40.0, "pitch_y": 40.0,
        "peg_dia": 0.0, "board_t": 5.0, "kind": "slot",
        "slot_w": 4.6, "slot_h": 14.5,
    },
}


def board_spec(key):
    """Look up a board standard, tolerant of stray case / spacing."""
    k = str(key).strip().lower().replace(" ", "").replace("-", "_")
    if k in ("1inch", "us", "us1inch", "pegboard", "wallcontrol"):
        k = "us_1inch"
    elif k in ("ikea", "skadis", "skådis"):
        k = "skadis"
    return BOARD_TABLE.get(k, BOARD_TABLE["us_1inch"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "hook"))   # hook | bin | tool_holder
board_standard = str(PARAM(lambda: board_standard, "us_1inch"))

peg_count = int(PARAM(lambda: peg_count, 2))             # vertical pegs behind part (1-2)
plate_thick = float(PARAM(lambda: plate_thick, 4.0))     # back plate thickness (mm)
plate_w = float(PARAM(lambda: plate_w, 26.0))            # back plate width (mm)

hook_reach = float(PARAM(lambda: hook_reach, 35.0))      # how far the hook sticks out
hook_dia = float(PARAM(lambda: hook_dia, 6.0))           # hook bar diameter (round stock)
hook_up = float(PARAM(lambda: hook_up, 14.0))            # upward return at the tip

bin_w = float(PARAM(lambda: bin_w, 60.0))                # bin interior width (mm)
bin_d = float(PARAM(lambda: bin_d, 45.0))                # bin depth out from board (mm)
bin_h = float(PARAM(lambda: bin_h, 45.0))                # bin height (mm)
bin_wall = float(PARAM(lambda: bin_wall, 2.4))           # bin wall thickness

tool_dia = float(PARAM(lambda: tool_dia, 20.0))          # tool shaft diameter to cradle
tool_ring = float(PARAM(lambda: tool_ring, 6.0))         # ring wall around the tool hole

spec = board_spec(board_standard)
peg_count = max(1, min(2, peg_count))
plate_thick = max(2.5, plate_thick)

# The back plate must be wide/tall enough to reach the pegs it carries.
pitch_y = spec["pitch_y"]
if peg_count >= 2:
    plate_h_min = pitch_y + 16.0
else:
    plate_h_min = 22.0


# ── Peg / insert helpers ─────────────────────────────────────────────────────
def _peg_y_positions():
    """Vertical centres (Z, measured from plate base) of the pegs on the plate."""
    if peg_count >= 2:
        base = (plate_height() - pitch_y) / 2.0
        return [base, base + pitch_y]
    return [plate_height() / 2.0]


def plate_height():
    """Back-plate height used by every part (>= reach to the pegs)."""
    if target_part == "bin":
        return max(plate_h_min, min(bin_h, pitch_y + 24.0))
    return plate_h_min


def round_peg(z):
    """US round peg: a horizontal cylinder that enters the hole, plus a short
    downward hook lip at the tip so it cannot lift out. Built pointing +Y
    (into the board, away from the front face at y=0)."""
    depth = spec["board_t"] + 3.0
    r = spec["peg_dia"] / 2.0
    peg = (
        cq.Workplane("XZ")
        .center(0, z)
        .circle(r)
        .extrude(depth)               # extrudes toward +Y
    )
    # Retention lip: a small downward tab at the far end of the peg.
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, depth - r, z - r - 1.2))
        .box(spec["peg_dia"], r * 1.4, 3.0, centered=(True, True, False))
    )
    return peg.union(lip)


def slot_peg(z):
    """SKÅDIS tongue: a flat vertical tab (sized to the ~5 mm slot) that passes
    through the slot, then a hook that returns downward behind the board to
    catch the web between slots. Built into +Y."""
    t = min(spec["slot_w"] - 0.6, 3.6)          # tongue thickness (fits the slot)
    w = min(spec["slot_h"] - 2.0, 11.0)          # tongue width (along Z, up the slot)
    reach = spec["board_t"] + 2.5
    tongue = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z - w / 2.0))
        .box(t, reach, w, centered=(True, True, False))
    )
    # Downward catch behind the board.
    catch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, reach - t, z - w / 2.0 - 6.0))
        .box(t, t + 1.2, 6.0 + w, centered=(True, True, False))
    )
    return tongue.union(catch)


def add_pegs(body):
    """Union the appropriate pegs for the active board standard onto `body`.
    The front face of the plate is at y=0; pegs grow toward +Y."""
    make = round_peg if spec["kind"] == "round" else slot_peg
    for z in _peg_y_positions():
        body = body.union(make(z))
    return body


def back_plate(w, h):
    """A flat back plate whose FRONT face sits at y=0, thickness toward -Y,
    base at z=0. Pegs grow from the front face into the board (+Y)."""
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -plate_thick, 0))
        .box(w, plate_thick, h, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Y").fillet(min(2.0, w / 4.0, h / 4.0))
    except Exception:
        pass
    return plate


# ── Part builders ─────────────────────────────────────────────────────────────
def build_hook():
    """Back plate + pegs + a J-hook projecting forward (-Y) with an up-return."""
    h = plate_height()
    body = back_plate(plate_w, h)
    body = add_pegs(body)

    r = max(2.5, hook_dia / 2.0)
    reach = max(hook_dia * 2.0, hook_reach)
    up = max(hook_dia, hook_up)
    # Seat the bar root where NO peg sits: for two pegs, the mid-band between
    # them; for one peg, well clear of that peg's Z-band. Coincident or tangent
    # faces between the forward bar and a rear peg make OCC emit a non-manifold
    # shell, so we force a real Z gap of >= r + 3 mm to the nearest peg feature.
    pegs = _peg_y_positions()
    if spec["kind"] == "slot":
        peg_half = spec["slot_h"] / 2.0          # tongue spans ~slot_h up the Z
    else:
        peg_half = spec["peg_dia"] / 2.0 + 2.0   # peg body + retention lip band
    if len(pegs) >= 2:
        z0 = (pegs[0] + pegs[1]) / 2.0
    else:
        z0 = pegs[0] - peg_half - r - 3.0
        if z0 < r + 2.0:                          # no room below → go above the peg
            z0 = pegs[0] + peg_half + r + 3.0

    # Build the J (bar + up-return) as ONE solid, overlapping ~2 mm INTO the
    # plate (from y=+2 back into the plate body) so the plate union is a deep
    # volumetric overlap, never a surface tangency.
    overlap = 2.0
    bar = (
        cq.Workplane("XZ")
        .center(0, z0)
        .circle(r)
        .extrude(-(reach + overlap))
        .translate((0, overlap, 0))
    )
    ret = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -reach, z0))
        .circle(r)
        .extrude(up + r)
    )
    try:
        ret = ret.edges(">Z").fillet(min(r - 0.4, up / 2.0))
    except Exception:
        pass
    jhook = bar.union(ret)
    body = body.union(jhook)
    return body


def build_bin():
    """Back plate + pegs + a forward open box (walls + floor) hanging on it."""
    h = plate_height()
    body = back_plate(plate_w if plate_w >= bin_w else bin_w, h)
    body = add_pegs(body)

    w = max(20.0, bin_w)
    d = max(15.0, bin_d)
    ht = max(20.0, min(bin_h, h))
    wall = max(1.6, bin_wall)

    # Outer box grows forward (-Y): y from 0 to -d, base at z=0.
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -d, 0))
        .box(w, d, ht, centered=(True, True, False))
    )
    # Hollow the cavity, leaving the back wall (against the plate) and a floor.
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -d + wall, wall))
        .box(w - 2.0 * wall, d - 2.0 * wall, ht, centered=(True, True, False))
    )
    box = outer.cut(cavity)
    # Drain / visibility slot in the front face keeps it light and printable.
    box = _bin_front_slot(box, w, d, ht, wall)
    body = body.union(box)
    return body


def _bin_front_slot(box, w, d, ht, wall):
    slot_w = w * 0.5
    slot_h = ht * 0.4
    if slot_w < 6 or slot_h < 6:
        return box
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -d - 1.0, wall + 4.0))
        .box(slot_w, wall + 2.0, slot_h, centered=(True, True, False))
    )
    try:
        return box.cut(cutter)
    except Exception:
        return box


def build_tool_holder():
    """Back plate + pegs + a forward tongue with a bored hole of `tool_dia`
    that a round tool drops through and hangs by its head/handle."""
    h = plate_height()
    body = back_plate(plate_w, h)
    body = add_pegs(body)

    ring = max(3.0, tool_ring)
    d_hole = max(4.0, tool_dia)
    pad_r = d_hole / 2.0 + ring
    depth = pad_r * 2.0                           # tongue depth out from the plate
    z0 = min(14.0, h / 2.0)                        # tongue centre height

    # Forward tongue: a slab centred at z0, growing -Y.
    tongue = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -depth, z0 - pad_r))
        .box(pad_r * 2.0, depth, pad_r * 2.0, centered=(True, True, False))
    )
    try:
        tongue = tongue.edges("|Z").fillet(min(pad_r - 0.5, ring))
    except Exception:
        pass
    # Bore the tool hole vertically through the tongue.
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -pad_r, z0 - pad_r - 1.0))
        .circle(d_hole / 2.0)
        .extrude(pad_r * 2.0 + 2.0)
    )
    tongue = tongue.cut(bore)
    body = body.union(tongue)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bin":
    result = build_bin()
elif target_part == "tool_holder":
    result = build_tool_holder()
else:
    result = build_hook()
