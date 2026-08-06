"""
Centrifuge Tube Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Step-down sleeves that let a centrifuge rotor bored for one tube size carry a
smaller tube. The outer diameter matches the rotor bore; the inner bore matches
the tube (Falcon 15 mL ≈ 17 mm, Falcon 50 mL ≈ 29 mm) with a conical seat so the
tube's tapered bottom is fully supported for balanced spinning.

  * "adapter_15"       — 50 mL rotor bore stepped down to a 15 mL tube
                         (target_part == "adapter_15").
  * "adapter_50"       — a large rotor bore stepped down to a 50 mL tube
                         (target_part == "adapter_50").
  * "microtube_adapter"— a 15 mL bore stepped down to a 1.5 mL microtube
                         (target_part == "microtube_adapter").

Watertight strategy: one solid outer cylinder; a straight bore for the tube body
plus a conical seat at the bottom, cut as one union of cutters. The bottom stays
closed by `floor`, so the sleeve is a single manifold solid. Balance is
preserved because the sleeve is axisymmetric.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

Printable lab AIDS for personal / educational use — verify balance and rated
speed before spinning; not a certified medical device.
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


# ── Tube standards (nominal outer diameters, mm) ─────────────────────────────
TUBES = {
    "falcon_50": {"dia": 29.0, "cone": True},   # 50 mL conical
    "falcon_15": {"dia": 17.0, "cone": True},   # 15 mL conical
    "micro_1p5": {"dia": 11.0, "cone": False},  # 1.5 mL microtube (round bottom)
}


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "adapter_15"))  # adapter_15 | adapter_50 | microtube_adapter

rotor_bore = float(PARAM(lambda: rotor_bore, 30.0))   # rotor pocket bore diameter (mm)
clearance  = float(PARAM(lambda: clearance,   0.4))   # outer slip into rotor + inner slip (per side)
wall_min   = float(PARAM(lambda: wall_min,    2.5))   # min wall left around the tube bore
depth      = float(PARAM(lambda: depth,      70.0))   # how far the tube seats (sleeve length)
floor      = float(PARAM(lambda: floor,       3.0))   # closed bottom thickness

# ── Clamps ───────────────────────────────────────────────────────────────────
rotor_bore = max(12.0, min(rotor_bore, 60.0))
clearance  = max(0.0,  min(clearance, 1.5))
wall_min   = max(1.5,  min(wall_min, 8.0))
depth      = max(20.0, min(depth, 120.0))
floor      = max(2.0,  min(floor, 10.0))


def tube_for(part):
    if part == "adapter_50":
        return TUBES["falcon_50"]
    if part == "microtube_adapter":
        return TUBES["micro_1p5"]
    return TUBES["falcon_15"]


# ── Builder ──────────────────────────────────────────────────────────────────
def build_adapter(part):
    tube = tube_for(part)
    tube_bore = tube["dia"] + 2.0 * clearance
    outer_d = rotor_bore - 2.0 * clearance      # sleeve outer slips into rotor
    # Guarantee a real wall: if the tube bore would leave too little wall, grow
    # the outer to the minimum needed (the user can still see the requested rotor
    # bore is too small via the constraint warning).
    outer_d = max(outer_d, tube_bore + 2.0 * wall_min)
    outer_r = outer_d / 2.0
    bore_r = tube_bore / 2.0

    total_h = depth + floor
    body = cq.Workplane("XY").circle(outer_r).extrude(total_h)

    # Straight bore for the cylindrical tube body, leaving `floor` at the bottom.
    seat_z = floor
    straight = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, seat_z))
        .circle(bore_r)
        .extrude(depth + 1.0)
    )
    body = body.cut(straight)

    # Conical seat for a conical Falcon bottom (a downward cone into the floor),
    # or a rounded-ish smaller step for a microtube. Built as a loft so it merges
    # cleanly with the straight bore and never leaves a zero-thickness lip.
    if tube["cone"]:
        cone_h = min(bore_r * 1.6, depth * 0.35)
        cone = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, seat_z))
            .circle(bore_r)
            .workplane(offset=cone_h)
            .circle(max(0.6, bore_r * 0.12))
            .loft(combine=True)
        )
        # Point the cone DOWN (tip toward the floor) so it cradles the tube tip.
        cone = cone.mirror("XY").translate((0, 0, seat_z + cone_h))
        body = body.cut(cone)
    else:
        # Rounded bottom: a short taper to a small flat.
        step = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, 1.0))
            .circle(bore_r * 0.7)
            .extrude(seat_z + 0.5)
        )
        body = body.cut(step)

    # A retaining lip/flange at the top so the sleeve sits on the rotor rim and
    # can't drop through — a thin ring wider than the bore, unioned on top.
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, total_h - 2.0))
        .circle(outer_r + 1.6)
        .circle(bore_r)
        .extrude(2.0)
    )
    body = body.union(lip)

    # Chamfer the top bore mouth so the tube guides in (non-fatal).
    try:
        body = body.faces(">Z").edges(cq.selectors.RadiusNthSelector(0)).chamfer(min(1.2, wall_min * 0.4))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
result = build_adapter(target_part)
