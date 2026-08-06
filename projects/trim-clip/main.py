"""
Trim Panel Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Replaces the brittle plastic clips that always snap when you pull a door card,
trim panel, or under-tray. A retention barb passes through a panel hole and
springs open behind it; three body styles suit different holes:

  * "push_clip"  — a fir-tree push clip: a stack of tapered conical barbs that
                   ratchet through a round hole and grip a range of panel
                   thicknesses.
  * "edge_clip"  — a U-shaped clip that slides over a panel EDGE (spring arms),
                   for flanges and trim lips.
  * "rivet_clip" — an expanding rivet: a hollow barbed shank that a centre pin
                   spreads to lock into a hole (models the shank/barb envelope).

The barb-through-hole is the Common Denominator Geometry — sized to the panel
hole diameter and thickness, so one clip family fits thousands of trim panels.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `hole_dia`).
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
hole_dia     = float(PARAM(lambda: hole_dia,      8.0))   # panel hole diameter (round)
hole_shape   = str(  PARAM(lambda: hole_shape, "round")) # "round" | "square"
panel_t      = float(PARAM(lambda: panel_t,       2.5))   # panel thickness the clip grips
head_dia     = float(PARAM(lambda: head_dia,     16.0))   # top flange (retainer) diameter
head_thick   = float(PARAM(lambda: head_thick,    2.0))   # flange thickness
barb_count   = int(  PARAM(lambda: barb_count,      3))   # fir-tree barb rings (push clip)
barb_grip    = float(PARAM(lambda: barb_grip,     1.6))   # how far each barb overhangs the hole (per side)
shank_len    = float(PARAM(lambda: shank_len,    14.0))   # shank length below the flange
wall         = float(PARAM(lambda: wall,          2.0))   # generic wall thickness

edge_gap     = float(PARAM(lambda: edge_gap,      2.5))   # edge_clip: panel-edge slot gap (= panel_t)
edge_reach   = float(PARAM(lambda: edge_reach,   16.0))   # edge_clip: how far arms grip over the edge

target_part  = str(  PARAM(lambda: target_part, "push_clip"))
# "push_clip" | "edge_clip" | "rivet_clip"


# ── Derived / clamped geometry ───────────────────────────────────────────────
hole_dia = max(3.0, hole_dia)
panel_t = max(0.8, panel_t)
hole_r = hole_dia / 2.0
# The shank core is a touch under the hole so it inserts; barbs flare wider.
core_r = max(1.0, hole_r - 0.4)
barb_grip = max(0.3, min(barb_grip, hole_r))
barb_r = hole_r + barb_grip
head_dia = max(hole_dia + 4.0, head_dia)
head_r = head_dia / 2.0
wall = max(1.0, wall)


# ── Shared helper: tapered barb / stem (reused across the automotive set) ─────
def tapered_stem(bottom_r, top_r, height, z0=0.0):
    """A vertical frustum from z0 (radius bottom_r) up to z0+height (radius
    top_r). Two-circle loft with a cylinder fallback. Watertight solid."""
    b = max(0.4, bottom_r)
    t = max(0.4, top_r)
    if abs(b - t) < 0.05:
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(b)
            .extrude(height)
        )
    try:
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(b)
            .workplane(offset=height)
            .circle(t)
            .loft(combine=True)
        )
    except Exception:
        r = (b + t) / 2.0
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(r)
            .extrude(height)
        )


def head_flange():
    """The top retainer flange, top face at z=head_thick (grows downward barbs)."""
    flange = (
        cq.Workplane("XY")
        .circle(head_r)
        .extrude(head_thick)
    )
    try:
        flange = flange.edges(">Z").fillet(min(1.2, head_thick * 0.4))
    except Exception:
        pass
    return flange


# ── push_clip (fir-tree) ──────────────────────────────────────────────────────
def _shank_core(radius, height, z0):
    """The central shank of a clip. A `round` hole gets a cylinder; a `square`
    hole gets a square prism (anti-rotation), sized to the same inscribed radius.
    Both are solid and watertight."""
    if hole_shape.strip().lower().startswith("sq"):
        side = radius * 2.0 * 0.9  # square that inserts into the round/square hole
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .box(side, side, height, centered=(True, True, False))
        )
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(radius)
        .extrude(height)
    )


def build_push_clip():
    """Fir-tree push clip: flange on top, then a shank carrying `barb_count`
    tapered barb rings. Each barb is a cone widening downward-to-up so it
    ratchets in and resists pull-out. Fully solid → watertight."""
    body = head_flange()

    # Central shank running down from the flange underside.
    body = body.union(_shank_core(core_r, shank_len, -shank_len))

    n = max(1, min(barb_count, 6))
    barb_h = min(3.5, (shank_len - 2.0) / n)
    # First barb sits about one panel thickness below the flange so the panel
    # nips between the flange and the top barb.
    z_top = -panel_t - 1.0
    for i in range(n):
        z_ring_top = z_top - i * (barb_h + 1.2)
        z_ring_bot = z_ring_top - barb_h
        if z_ring_bot < -shank_len + 0.5:
            break
        # Cone: wide (barb_r) at the top edge, tapering to core_r at the bottom,
        # so pushing IN slides over it and pulling OUT catches the wide lip.
        barb = tapered_stem(core_r, barb_r, barb_h, z0=z_ring_bot)
        body = body.union(barb)

    # Rounded lead-in tip.
    tip = tapered_stem(0.8, core_r, 2.0, z0=-shank_len)
    body = body.union(tip)
    return body


# ── edge_clip ─────────────────────────────────────────────────────────────────
def build_edge_clip():
    """U-shaped clip that slides over a panel EDGE: two arms separated by a slot
    of `edge_gap` (the panel thickness), with a small inward barb on each arm to
    grip. Solid U-channel → watertight."""
    gap = max(0.6, edge_gap)
    arm_t = wall
    reach = max(6.0, edge_reach)
    width = max(hole_dia + 6.0, head_dia)  # clip width across the edge
    outer_h = gap + 2.0 * arm_t

    # Solid block, then slot it into a U from one side.
    block = (
        cq.Workplane("XY")
        .box(reach, width, outer_h, centered=(True, True, True))
    )
    try:
        block = block.edges("|Y").fillet(min(2.0, arm_t))
    except Exception:
        pass

    # Slot: open at +X, depth = reach - back_wall.
    back_wall = max(2.0, wall)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector((reach - (reach - back_wall)) / 2.0 + 0.5, 0, 0))
        .box(reach - back_wall + 2.0, width + 2.0, gap, centered=(True, True, True))
    )
    body = block.cut(slot)

    # Inward grip barbs: a small bump on each inner arm face, near the opening.
    for zc in (gap / 2.0, -gap / 2.0):
        bump = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(reach / 2.0 - 3.0, 0, zc))
            .box(3.0, width * 0.7, 1.2, centered=(True, True, True))
        )
        body = body.union(bump)
    return body


# ── rivet_clip ────────────────────────────────────────────────────────────────
def build_rivet_clip():
    """Expanding rivet: a flange, a hollow barbed shank (bore for the spreader
    pin), and a single large retention barb. Models the installed envelope; the
    hollow keeps it a clean watertight shell."""
    body = head_flange()

    # Barbed shank: a downward frustum widening to a retention lip then tapering
    # to a lead-in tip. Built as a union of two frusta.
    lip_z = -panel_t - 1.5
    upper = tapered_stem(core_r, core_r, panel_t + 1.5, z0=lip_z)  # straight neck
    body = body.union(upper)
    barb = tapered_stem(core_r, barb_r, 3.0, z0=lip_z - 3.0)
    body = body.union(barb)
    lower = tapered_stem(0.8, core_r, shank_len - (panel_t + 4.5),
                         z0=-shank_len)
    body = body.union(lower)

    # Central pin bore (the spreader), open at both ends → still watertight as a
    # tube because it fully traverses.
    bore_r = max(0.8, core_r - wall)
    if bore_r > 0.8:
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -shank_len - 1.0))
            .circle(bore_r)
            .extrude(shank_len + head_thick + 2.0)
        )
        body = body.cut(bore)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "edge_clip":
    result = build_edge_clip()
elif target_part == "rivet_clip":
    result = build_rivet_clip()
else:  # "push_clip"
    result = build_push_clip()
