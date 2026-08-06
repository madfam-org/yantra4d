"""
Raspberry Pi / SBC Case — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A case for a single-board computer. A board table gives the correct PCB
footprint and the 4 mounting-hole spacing for common boards (Raspberry Pi 4 / 5,
Pi Zero) or a fully parametric generic board. The case models the board's
mounting standoffs at the right hole rectangle, a base tray with walls, and a
large rectangular opening on the port edge for the USB / HDMI connectors.

Modes are dispatched via `target_part`:
  * "base" — the tray with standoffs and the port-edge opening (walls included).
  * "lid"  — a vented cover that drops over the base walls.
  * "tray" — the bottom tray only (floor + standoffs, no walls).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `board`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Board table (RPi 40-pin form factor family) ──────────────────────────────
# pcb_w/pcb_d : board outline (X × Y, mm)
# hole_x/hole_d: mounting-hole rectangle spacing (X × Y between hole centres, mm)
# hole_dia    : mounting-hole diameter (mm)
BOARD_TABLE = {
    "rpi4":     {"pcb_w": 85.0, "pcb_d": 56.0, "hole_x": 58.0, "hole_y": 49.0, "hole_dia": 2.7},
    "rpi5":     {"pcb_w": 85.0, "pcb_d": 56.0, "hole_x": 58.0, "hole_y": 49.0, "hole_dia": 2.7},
    "rpi_zero": {"pcb_w": 65.0, "pcb_d": 30.0, "hole_x": 58.0, "hole_y": 23.0, "hole_dia": 2.75},
}


def board_spec(key):
    k = str(key).strip().lower().replace(" ", "").replace("-", "_")
    if k in ("rpi4", "rpi_4", "pi4", "rpi4b"):
        return dict(BOARD_TABLE["rpi4"])
    if k in ("rpi5", "rpi_5", "pi5"):
        return dict(BOARD_TABLE["rpi5"])
    if k in ("rpi_zero", "rpizero", "pizero", "zero", "rpi0"):
        return dict(BOARD_TABLE["rpi_zero"])
    return None  # generic → use params


# ── Parameters ───────────────────────────────────────────────────────────────
board       = str(PARAM(lambda: board, "rpi4"))     # rpi4|rpi5|rpi_zero|generic
gen_pcb_w   = float(PARAM(lambda: gen_pcb_w,  80.0))  # generic board size X
gen_pcb_d   = float(PARAM(lambda: gen_pcb_d,  55.0))  # generic board size Y
gen_hole_x  = float(PARAM(lambda: gen_hole_x, 70.0))  # generic hole spacing X
gen_hole_y  = float(PARAM(lambda: gen_hole_y, 45.0))  # generic hole spacing Y

wall        = float(PARAM(lambda: wall,       2.4))   # wall thickness
floor       = float(PARAM(lambda: floor,      2.4))   # floor / lid thickness
clearance   = float(PARAM(lambda: clearance,  1.5))   # gap board edge → wall
standoff_h  = float(PARAM(lambda: standoff_h, 4.0))   # board height above floor
wall_h      = float(PARAM(lambda: wall_h,    18.0))   # base wall height
port_cutout = bool(PARAM(lambda: port_cutout, True))  # port-edge opening
vents       = bool(PARAM(lambda: vents,      True))   # lid vent slots

target_part = str(PARAM(lambda: target_part, "base"))  # base|lid|tray

# ── Resolve board ────────────────────────────────────────────────────────────
spec = board_spec(board)
if spec is None:
    spec = {
        "pcb_w": max(20.0, gen_pcb_w),
        "pcb_d": max(20.0, gen_pcb_d),
        "hole_x": max(8.0, min(gen_hole_x, gen_pcb_w - 4.0)),
        "hole_y": max(8.0, min(gen_hole_y, gen_pcb_d - 4.0)),
        "hole_dia": 2.75,
    }

pcb_w = spec["pcb_w"]
pcb_d = spec["pcb_d"]
hole_x = spec["hole_x"]
hole_y = spec["hole_y"]
hole_dia = spec["hole_dia"]

wall = max(1.2, wall)
floor = max(1.2, floor)
clearance = max(0.3, clearance)
standoff_h = max(1.5, standoff_h)
wall_h = max(standoff_h + 3.0, wall_h)

# Interior tray footprint holds the board plus clearance on every side.
inner_w = pcb_w + 2.0 * clearance
inner_d = pcb_d + 2.0 * clearance
outer_w = inner_w + 2.0 * wall
outer_d = inner_d + 2.0 * wall

boss_d = max(hole_dia + 3.0, 6.0)   # standoff outer diameter
lid_clear = 0.3                     # lid-to-wall slip fit


# ── Helpers ──────────────────────────────────────────────────────────────────
def hole_points():
    """The four mounting-hole centres, centred on the origin."""
    hx, hy = hole_x / 2.0, hole_y / 2.0
    return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]


def add_standoffs(body, base_z):
    for (x, y) in hole_points():
        pillar = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, base_z))
            .circle(boss_d / 2.0)
            .extrude(standoff_h)
        )
        body = body.union(pillar)
    for (x, y) in hole_points():
        drill = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, base_z + standoff_h - min(standoff_h, 5.0)))
            .circle(hole_dia / 2.0)
            .extrude(min(standoff_h, 5.0) + 0.5)
        )
        body = body.cut(drill)
    return body


def cut_port_edge(body):
    """Large rectangular opening on the +X wall (the connector edge)."""
    if not port_cutout:
        return body
    open_w = inner_d - 6.0            # span across the edge (Y)
    open_h = min(wall_h - 2.0, standoff_h + 12.0)
    z0 = floor + standoff_h + open_h / 2.0 - 1.0
    x_wall = outer_w / 2.0
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x_wall, 0, z0))
        .box(wall + 4.0, open_w, open_h, centered=(True, True, True))
    )
    return body.cut(cutter)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_tray():
    """Floor + standoffs only (no walls)."""
    body = cq.Workplane("XY").box(outer_w, outer_d, floor, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(wall, 2.0))
    except Exception:
        pass
    body = add_standoffs(body, floor)
    return body


def build_base():
    """Tray + surrounding walls + port-edge opening."""
    outer = cq.Workplane("XY").box(outer_w, outer_d, floor + wall_h, centered=(True, True, False))
    try:
        outer = outer.edges("|Z").fillet(min(wall, 2.0))
    except Exception:
        pass
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor))
        .box(inner_w, inner_d, wall_h + 1.0, centered=(True, True, False))
    )
    body = outer.cut(cavity)
    body = add_standoffs(body, floor)
    body = cut_port_edge(body)
    return body


def build_lid():
    """A cover that drops over the base walls, optionally vented."""
    lid_w = outer_w + 2.0 * (wall + lid_clear)
    lid_d = outer_d + 2.0 * (wall + lid_clear)
    skirt_h = 6.0

    top = cq.Workplane("XY").box(lid_w, lid_d, floor, centered=(True, True, False))
    try:
        top = top.edges("|Z").fillet(min(wall, 2.0))
    except Exception:
        pass

    # Downward skirt hugging the outside of the base walls.
    outer_sk = cq.Workplane("XY").box(lid_w, lid_d, skirt_h, centered=(True, True, False))
    inner_sk = cq.Workplane("XY").box(
        outer_w + 2.0 * lid_clear, outer_d + 2.0 * lid_clear, skirt_h + 1.0,
        centered=(True, True, False),
    )
    skirt = outer_sk.cut(inner_sk).translate((0, 0, -skirt_h))
    lid = top.union(skirt)

    if vents:
        slot_w = 2.5
        gap = 4.0
        n = max(1, int(inner_w // (slot_w + gap)) - 1)
        pitch = slot_w + gap
        x0 = -((n - 1) * pitch) / 2.0
        slot_len = inner_d * 0.55
        for i in range(n):
            x = x0 + i * pitch
            cutter = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, 0, -1.0))
                .box(slot_w, slot_len, floor + 2.0, centered=(True, True, False))
            )
            lid = lid.cut(cutter)
    return lid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "lid":
    result = build_lid()
elif target_part == "tray":
    result = build_tray()
else:
    result = build_base()
