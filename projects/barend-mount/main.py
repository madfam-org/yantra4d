"""
Motorcycle Bar-End / Mirror Mount — Yantra4D Hyperobject Cartridge (CadQuery).

Handlebar hardware for motorcycles and bicycles: a split clamp that closes
around the bar to carry an accessory, an expanding plug for the hollow bar END
(bar-end weights and mirrors), and a wider clamp with an action-cam / phone
cradle platform.

  * "bar_clamp"    — a split C-clamp that wraps the bar OD, closed by two side
                     bolts, with a flat accessory boss on top drilled for an M-
                     bolt (target_part == "bar_clamp").
  * "bar_end_plug" — a stepped cylindrical plug that inserts into the hollow bar
                     END, with a central bolt bore for a bar-end weight or mirror
                     stud (target_part == "bar_end_plug").
  * "phone_clamp"  — a wider bar clamp carrying a raised platform with a corner
                     lip, for an action-cam / phone-holder base
                     (target_part == "phone_clamp").

Real dimensions (bar diameters — model to the decimal, nominal lies):
  - 7/8 in bar OD = 22.2 mm (JP / sport / dirt; also the universal grip section).
  - 1 in bar OD = 25.4 mm (Harley / cruiser).
  - 31.8 mm oversize clamp (bicycle oversize / 1-1/4 in fat-bar).
  - 35 mm newer MTB oversize.
  - Bar-END inner diameter ~14-19 mm (design plug for ~16 and ~18 mm ID).
  - Bar-end mirror thread commonly M8 / M10 (default M8).

Watertight strategy (the brief's C-section clamp rule): the clamp is a SOLID
block with the bar bore drilled THROUGH (open both ends → vented) and a thin
clamp SLIT sawn to one side (open slot → vented, still one manifold). Two bolt
bores pass through the ears. The accessory boss is unioned onto the block
(overlapping into shared material). The bar-end plug is a stepped SOLID cylinder
with a central through bore. Fillets are applied to clean blanks BEFORE cuts,
wrapped in try/except. Each result is one manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "bar_clamp"))  # bar_clamp | bar_end_plug | phone_clamp

bar_od = float(PARAM(lambda: bar_od, 22.2))       # handlebar outer diameter (mm)
bar_id = float(PARAM(lambda: bar_id, 16.0))       # hollow bar inner diameter (mm, for the plug)
wall = float(PARAM(lambda: wall, 5.0))            # clamp wall / body thickness (mm)
clamp_w = float(PARAM(lambda: clamp_w, 20.0))     # clamp width along the bar (mm)
bolt_d = float(PARAM(lambda: bolt_d, 5.2))        # clamp bolt clearance (M5 ~5.2 mm)
acc_bolt_d = float(PARAM(lambda: acc_bolt_d, 8.4))  # accessory bolt clearance (M8 ~8.4 mm)
plate_len = float(PARAM(lambda: plate_len, 40.0))  # phone platform length (mm)
plate_wid = float(PARAM(lambda: plate_wid, 32.0))  # phone platform width (mm)
clearance = float(PARAM(lambda: clearance, 0.3))  # bar bore slip clearance (per side)

# ── Clamps ───────────────────────────────────────────────────────────────────
bar_od = max(15.0, min(bar_od, 45.0))
bar_id = max(8.0, min(bar_id, bar_od - 3.0))
wall = max(3.0, min(wall, 12.0))
clamp_w = max(10.0, min(clamp_w, 50.0))
bolt_d = max(2.5, min(bolt_d, 8.0))
acc_bolt_d = max(3.0, min(acc_bolt_d, 12.0))
plate_len = max(20.0, min(plate_len, 90.0))
plate_wid = max(20.0, min(plate_wid, 90.0))
clearance = max(0.0, min(clearance, 1.0))

BORE_R = bar_od / 2.0 + clearance
BODY_R = BORE_R + wall


# ── Helpers ──────────────────────────────────────────────────────────────────
def _clamp_block(width, boss_h):
    """A split clamp block: a cylinder around the bar (axis along X) grown into a
    rectangular boss on top, with the bar bore drilled through, a clamp slit to
    one side, and two side bolt bores. Returns the solid; the accessory face sits
    on top at z = BODY_R + boss_h. Vented throughout."""
    # Cylinder hub around the bar (axis X).
    hub = (
        cq.Workplane("YZ")
        .circle(BODY_R)
        .extrude(width)
        .translate((-width / 2.0, 0, 0))
    )
    # Rectangular boss growing UP from the hub to carry the accessory face.
    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, 0))
        .box(width, 2.0 * BODY_R, BODY_R + boss_h, centered=(True, True, False))
    )
    body = hub.union(boss)
    try:
        body = body.edges("|X").fillet(min(2.0, wall * 0.4))
    except Exception:
        pass

    # Bar bore drilled through along X (open both ends → vented).
    bore = (
        cq.Workplane("YZ")
        .circle(BORE_R)
        .extrude(width + 2.0)
        .translate((-width / 2.0 - 1.0, 0, 0))
    )
    body = body.cut(bore)

    # Clamp slit from the bore mouth downward through the bottom (opens the ring
    # so it can pinch; a vented slot, still one manifold).
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -BODY_R - 1.0))
        .box(width + 2.0, max(1.6, wall * 0.35), BODY_R + 1.0, centered=(True, True, False))
    )
    body = body.cut(slit)

    # Two clamp bolt bores across Y, below the bar centre, one each side of the
    # slit, passing through both ears (vented).
    bolt_z = -BORE_R - wall * 0.4
    for _ in (0,):
        bolt = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0, bolt_z, 0))
            .circle(bolt_d / 2.0)
            .extrude(BODY_R + 2.0, both=True)
        )
        body = body.cut(bolt)
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_bar_clamp():
    """Split clamp with a flat accessory boss drilled for an M-bolt on top."""
    boss_h = 6.0
    body = _clamp_block(clamp_w, boss_h)
    # Accessory bolt bored down into the top boss face (a blind-ish hole vented to
    # the top surface — cut from the top down, opening to outside → not trapped).
    top_z = BODY_R + boss_h
    depth = min(boss_h + wall, top_z - BORE_R - 1.0, top_z - 1.0)
    depth = max(3.0, depth)
    acc = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, top_z - depth))
        .circle(acc_bolt_d / 2.0)
        .extrude(depth + 0.5)
    )
    body = body.cut(acc)
    return body


def build_bar_end_plug():
    """A stepped plug for the hollow bar END: a shoulder disc (rests on the bar
    rim) plus an insert cylinder sized to the bar ID, with a central bolt bore
    for a weight / mirror stud. Solid stepped cylinder, central through bore."""
    plug_r = bar_id / 2.0 - clearance
    plug_r = max(3.0, plug_r)
    insert_len = max(12.0, bar_id * 0.9)
    shoulder_r = bar_od / 2.0 + 1.5
    shoulder_h = max(4.0, wall * 0.8)

    # Shoulder disc at z in [0, shoulder_h].
    shoulder = cq.Workplane("XY").circle(shoulder_r).extrude(shoulder_h)
    # Insert cylinder rising from the shoulder top, overlapping down into it.
    insert = (
        cq.Workplane("XY")
        .workplane(offset=shoulder_h - 0.5)
        .circle(plug_r)
        .extrude(insert_len + 0.5)
    )
    body = shoulder.union(insert)
    try:
        body = body.edges(">Z").chamfer(min(1.5, plug_r * 0.3))
    except Exception:
        pass
    # Central bolt bore through the whole plug (open both ends → vented).
    bore = (
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .circle(acc_bolt_d / 2.0)
        .extrude(shoulder_h + insert_len + 1.0)
    )
    body = body.cut(bore)
    return body


def build_phone_clamp():
    """A wider bar clamp carrying a raised rectangular platform with a corner lip,
    an accessory base for an action-cam / phone holder. The platform overlaps
    down onto the clamp boss (volumetric union); a bolt slot lets a mount slide."""
    boss_h = 5.0
    body = _clamp_block(max(clamp_w, 22.0), boss_h)
    top_z = BODY_R + boss_h
    # Platform slab.
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, top_z - 1.0))
        .box(plate_len, plate_wid, 4.0, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Z").fillet(min(4.0, plate_wid * 0.15))
    except Exception:
        pass
    body = body.union(plate)
    # Corner lip: a thin raised rail along one short edge so the device seats.
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-plate_len / 2.0 + 2.0, 0, top_z + 3.0 - 1.0))
        .box(3.0, plate_wid, 6.0, centered=(True, True, False))
    )
    body = body.union(lip)
    # Central mounting slot through the platform (obround, vented).
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, top_z - 1.5))
        .slot2D(max(plate_len * 0.5, acc_bolt_d + 4.0), acc_bolt_d, angle=0)
        .extrude(6.0)
    )
    body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bar_end_plug":
    result = build_bar_end_plug()
elif target_part == "phone_clamp":
    result = build_phone_clamp()
else:  # "bar_clamp"
    result = build_bar_clamp()
