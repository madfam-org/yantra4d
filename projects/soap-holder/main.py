"""
Soap / Sponge Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A draining dish for a bar of soap or a sponge: an open tray whose floor carries a
lattice of drain holes so water runs out instead of pooling. An optional lip/spout
tips runoff toward the sink, and a wall-mount variant adds a hook clip plus a
suction-cup boss.

  * "dish"      — freestanding drain tray (target_part == "dish").
  * "wall_dish" — the same tray with a wall clip and a suction-cup mounting boss.

Watertight strategy: the tray is a solid block hollowed to a bowl (floor left
intact), then the drain holes are bored COMPLETELY through the floor. Full
through-cuts keep the mesh manifold / watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "dish"))  # "dish" | "wall_dish"

width   = float(PARAM(lambda: width,   100.0))   # tray X (mm)
depth   = float(PARAM(lambda: depth,    75.0))   # tray Y (mm)
height  = float(PARAM(lambda: height,   22.0))   # tray Z (mm)
wall    = float(PARAM(lambda: wall,      2.4))   # side + floor thickness
drain_density = float(PARAM(lambda: drain_density, 1.0))  # 0.5 sparse … 2.0 dense
mount   = str(  PARAM(lambda: mount,  "freestanding"))    # "freestanding" | "wall_clip"
spout   = bool( PARAM(lambda: spout,    True))   # notch/lip that drains toward the sink

# The studio dispatches the wall variant through target_part; keep `mount` in sync.
if target_part == "wall_dish":
    mount = "wall_clip"

# ── Clamps ───────────────────────────────────────────────────────────────────
width  = max(40.0, width)
depth  = max(40.0, depth)
height = max(10.0, height)
wall   = max(1.6, min(wall, min(width, depth) / 6.0))
drain_density = max(0.5, min(drain_density, 2.0))

floor = wall
inner_w = width - 2.0 * wall
inner_d = depth - 2.0 * wall
inner_h = height - floor


# ── Helpers ──────────────────────────────────────────────────────────────────
def block(w, d, h, z0=0.0):
    """Axis-aligned block on XY, centred in X/Y, base at z0."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .box(w, d, h, centered=(True, True, False))
    )


def build_tray():
    """Solid outer, hollowed to a bowl with the floor intact."""
    body = block(width, depth, height)
    cavity = block(inner_w, inner_d, inner_h + 1.0, z0=floor)
    body = body.cut(cavity)
    return body


def drain_points():
    """Grid of drain-hole centres across the floor, staying inside the bowl."""
    pitch = 9.0 / drain_density         # denser → smaller pitch
    margin = wall + 3.0
    max_x = inner_w / 2.0 - 2.0
    max_y = inner_d / 2.0 - 2.0
    nx = int((width - 2.0 * margin) / pitch)
    ny = int((depth - 2.0 * margin) / pitch)
    nx = max(1, nx)
    ny = max(1, ny)
    pts = []
    for i in range(nx + 1):
        x = -((nx) * pitch) / 2.0 + i * pitch
        if abs(x) > max_x:
            continue
        for j in range(ny + 1):
            y = -((ny) * pitch) / 2.0 + j * pitch
            if abs(y) > max_y:
                continue
            pts.append((x, y))
    return pts


def drill_drains(body):
    """Bore drain holes fully through the floor (watertight through-cuts)."""
    pts = drain_points()
    if not pts:
        return body
    hole_d = min(5.0, max(2.5, 4.0 / (drain_density ** 0.5)))
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .pushPoints(pts)
        .circle(hole_d / 2.0)
        .extrude(floor + 2.0)
    )
    return body.cut(cutter)


def add_spout(body):
    """Notch the front rim so water drains toward the sink."""
    if not spout:
        return body
    notch_w = min(inner_w * 0.5, 30.0)
    # A shallow slot cut from the top of the FRONT wall (−Y side), down to just
    # above the floor so runoff spills over the lowered lip.
    slot_h = inner_h * 0.6
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -depth / 2.0 + wall / 2.0, height - slot_h))
        .box(notch_w, wall + 2.0, slot_h + 1.0, centered=(True, True, False))
    )
    return body.cut(slot)


def add_wall_clip(body):
    """Add a hook clip over the top rear rim plus a suction-cup boss.
    A hook is an inverted-U so the dish hangs on a rail / cabinet edge; the
    suction boss is a small ring on the back face for a suction cup."""
    parts = [body]
    rear_y = depth / 2.0

    # Hook: vertical spine up the back + a lip that folds forward over a rail.
    hook_w = min(width * 0.4, 40.0)
    hook_t = max(3.0, wall)
    rail_gap = 6.0     # accommodates a ~6 mm cabinet lip / rail
    spine_h = 18.0
    spine = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, rear_y - hook_t / 2.0, height))
        .box(hook_w, hook_t, spine_h, centered=(True, True, False))
    )
    top_lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, rear_y - hook_t / 2.0 - rail_gap / 2.0, height + spine_h - hook_t))
        .box(hook_w, hook_t + rail_gap, hook_t, centered=(True, True, False))
    )
    return_lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, rear_y - hook_t / 2.0 - rail_gap, height + spine_h - hook_t - 6.0))
        .box(hook_w, hook_t, 8.0, centered=(True, True, False))
    )
    parts += [spine, top_lip, return_lip]

    # Suction boss: a low ring on the back face (a suction cup snaps into it).
    boss_outer = 16.0
    boss = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, height / 2.0, -rear_y))
        .circle(boss_outer / 2.0)
        .circle(boss_outer / 2.0 - 2.5)
        .extrude(3.0)
    )
    parts.append(boss)

    out = parts[0]
    for p in parts[1:]:
        out = out.union(p)
    return out


# ── Build ────────────────────────────────────────────────────────────────────
def build():
    body = build_tray()
    body = drill_drains(body)
    body = add_spout(body)
    if mount == "wall_clip":
        body = add_wall_clip(body)
    # Soften the top inner/outer rim; non-fatal if degenerate.
    try:
        body = body.edges(">Z").fillet(min(0.8, wall * 0.3))
    except Exception:
        pass
    return body


result = build()
