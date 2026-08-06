"""
Parametric Project Enclosure — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A Hammond-style two-part project box for electronics, sized by its INTERIOR
cavity to a PCB. The base carries PCB standoffs at the board corners (bored for
M2.5 / M3 screws), optional rectangular side-port cutouts, and optional vent
slots; the lid closes over the base with either screw tabs or a snap lip.

Modes are dispatched via `target_part`:
  * "base" — the box body with PCB standoffs, port cutouts and vents.
  * "lid"  — the cover: screw-tab holes (or a snap lip) matching the base.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
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


# ── Screw table (metric clearance / tap-ish bore for a self-tapping boss) ─────
# bore = the hole drilled through the standoff pillar for the mounting screw.
# A slightly-under bore lets a thread-forming machine screw bite into plastic.
SCREW_TABLE = {
    "M2.5": {"bore": 2.3, "head": 5.0, "pillar": 5.5},
    "M3":   {"bore": 2.7, "head": 6.0, "pillar": 6.5},
}


def screw_spec(key):
    k = str(key).strip().upper().replace(" ", "")
    if k in ("M2.5", "M25", "2.5", "2.5MM"):
        return SCREW_TABLE["M2.5"]
    return SCREW_TABLE.get("M3", SCREW_TABLE["M3"])


# ── Parameters (interior-driven) ─────────────────────────────────────────────
inner_w   = float(PARAM(lambda: inner_w,   90.0))   # interior X (mm)
inner_d   = float(PARAM(lambda: inner_d,   60.0))   # interior Y (mm)
inner_h   = float(PARAM(lambda: inner_h,   35.0))   # interior Z (mm)
wall      = float(PARAM(lambda: wall,       2.4))   # wall thickness
floor     = float(PARAM(lambda: floor,      2.4))   # floor / lid-plate thickness
corner_r  = float(PARAM(lambda: corner_r,   3.0))   # outer corner radius

pcb_w     = float(PARAM(lambda: pcb_w,     70.0))   # PCB width  (X)
pcb_d     = float(PARAM(lambda: pcb_d,     50.0))   # PCB depth  (Y)
standoff_h = float(PARAM(lambda: standoff_h, 5.0))  # standoff pillar height
screw_size = str(PARAM(lambda: screw_size, "M3"))   # "M2.5" | "M3"

lid_mount = str(PARAM(lambda: lid_mount, "screw"))  # "screw" | "snap"

port_count = int(PARAM(lambda: port_count, 0))      # rectangular side ports
port_w    = float(PARAM(lambda: port_w,    16.0))   # port width  (along X)
port_h    = float(PARAM(lambda: port_h,     8.0))   # port height (along Z)
port_z    = float(PARAM(lambda: port_z,     4.0))   # port bottom above floor

vents     = bool(PARAM(lambda: vents,    False))    # vent slots in the walls

target_part = str(PARAM(lambda: target_part, "base"))  # "base" | "lid"

# ── Derived envelope ─────────────────────────────────────────────────────────
outer_w = inner_w + 2.0 * wall
outer_d = inner_d + 2.0 * wall
base_h  = inner_h + floor                       # base body height (with floor)

corner_r = max(0.0, min(corner_r, min(outer_w, outer_d) / 2.0 - 0.01))
inner_r  = max(0.0, corner_r - wall)

spec = screw_spec(screw_size)
pillar_d = spec["pillar"]
bore_d   = spec["bore"]

# Keep the PCB footprint inside the cavity.
pcb_w = max(6.0, min(pcb_w, inner_w - pillar_d - 1.0))
pcb_d = max(6.0, min(pcb_d, inner_d - pillar_d - 1.0))
standoff_h = max(1.0, min(standoff_h, inner_h - 1.0))

snap_lip_h = 2.4      # height of the snap lip on base / catch on lid
snap_clear = 0.25     # nominal snap interference relief


# ── Helpers ──────────────────────────────────────────────────────────────────
def rounded_block(w, d, h, r):
    """Block on XY, base at z=0, optional rounded vertical edges."""
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


def pcb_corner_points():
    """Board-corner standoff centres, centred on the origin."""
    hx, hy = pcb_w / 2.0, pcb_d / 2.0
    return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]


def port_x_positions(n):
    """Evenly spaced X centres for `n` ports across the front wall span."""
    if n <= 0:
        return []
    span = inner_w - port_w - 2.0
    if span <= 0 or n == 1:
        return [0.0]
    return [-span / 2.0 + span * i / (n - 1) for i in range(n)]


def cut_ports(body):
    """Rectangular cutouts through the FRONT wall (-Y face)."""
    n = max(0, port_count)
    if n <= 0:
        return body
    pw = max(2.0, min(port_w, inner_w - 2.0))
    ph = max(2.0, min(port_h, inner_h - 1.0))
    z0 = floor + max(0.0, min(port_z, inner_h - ph - 0.5))
    y_wall = -outer_d / 2.0
    for x in port_x_positions(n):
        cutter = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y_wall - 1.0, z0 + ph / 2.0))
            .box(pw, wall + 4.0, ph, centered=(True, True, True))
        )
        body = body.cut(cutter)
    return body


def cut_vents(body):
    """A row of vent slots through each SIDE wall (±X faces)."""
    if not vents:
        return body
    slot_w = 2.0
    slot_len = max(6.0, inner_d * 0.5)
    gap = 4.0
    n = max(1, int(inner_d // (slot_w + gap)) - 1)
    z0 = floor + inner_h * 0.5
    pitch = slot_w + gap
    y_start = -((n - 1) * pitch) / 2.0
    for sign in (-1.0, 1.0):
        x_wall = sign * outer_w / 2.0
        for i in range(n):
            y = y_start + i * pitch
            cutter = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x_wall, y, z0))
                .box(wall + 4.0, slot_w, slot_len, centered=(True, True, True))
            )
            body = body.cut(cutter)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_base():
    """Box body: hollow shell + PCB standoffs + ports + vents (+ snap lip)."""
    body = rounded_block(outer_w, outer_d, base_h, corner_r)

    cavity = cq.Workplane("XY").transformed(
        offset=cq.Vector(0, 0, floor)
    ).box(inner_w, inner_d, inner_h + 1.0, centered=(True, True, False))
    if inner_r > 0.05:
        try:
            cavity = cavity.edges("|Z").fillet(inner_r)
        except Exception:
            pass
    body = body.cut(cavity)

    # PCB standoffs: solid pillars rising from the floor, each with a screw bore.
    for (x, y) in pcb_corner_points():
        pillar = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, floor))
            .circle(pillar_d / 2.0)
            .extrude(standoff_h)
        )
        body = body.union(pillar)
    for (x, y) in pcb_corner_points():
        drill = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, floor + standoff_h - min(standoff_h, 6.0)))
            .circle(bore_d / 2.0)
            .extrude(min(standoff_h, 6.0) + 0.5)
        )
        body = body.cut(drill)

    body = cut_ports(body)
    body = cut_vents(body)

    # Snap lip: a thin inward shelf at the top rim that the lid catches under.
    if lid_mount == "snap":
        lip = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, base_h))
            .box(inner_w - 0.4, inner_d - 0.4, snap_lip_h, centered=(True, True, False))
        )
        lip_bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, base_h - 0.1))
            .box(inner_w - 2.0 * wall, inner_d - 2.0 * wall, snap_lip_h + 0.4,
                 centered=(True, True, False))
        )
        body = body.union(lip.cut(lip_bore))

    return body


def build_lid():
    """Cover plate: screw-tab holes, or a downward snap skirt matching the base."""
    plate = rounded_block(outer_w, outer_d, floor, corner_r)

    if lid_mount == "snap":
        # Skirt nests inside the cavity, with a catch groove near its tip.
        skirt_w = inner_w - 2.0 * snap_clear
        skirt_d = inner_d - 2.0 * snap_clear
        s_wall = max(1.2, wall - 0.6)
        skirt_h = snap_lip_h + 2.0
        outer = cq.Workplane("XY").box(skirt_w, skirt_d, skirt_h, centered=(True, True, False))
        inner = cq.Workplane("XY").box(
            skirt_w - 2.0 * s_wall, skirt_d - 2.0 * s_wall, skirt_h + 1.0,
            centered=(True, True, False),
        )
        skirt = outer.cut(inner).translate((0, 0, -skirt_h))
        lid = plate.union(skirt)
    else:
        # Screw tabs: bore + counterbore at the four plate corners.
        head = spec["head"]
        inset = max(pillar_d, 5.0)
        hx = outer_w / 2.0 - inset
        hy = outer_d / 2.0 - inset
        pts = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
        lid = plate
        thru = (
            cq.Workplane("XY").pushPoints(pts).circle(bore_d / 2.0 + 0.3)
            .extrude(floor + 2.0).translate((0, 0, -1.0))
        )
        lid = lid.cut(thru)
        cbore = (
            cq.Workplane("XY").workplane(offset=floor).pushPoints(pts)
            .circle(head / 2.0).extrude(-min(floor - 0.8, 2.0))
        )
        lid = lid.cut(cbore)

    return lid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "lid":
    result = build_lid()
else:
    result = build_base()
