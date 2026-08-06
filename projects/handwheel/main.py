"""
Machine Handwheel / Crank — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A replacement handwheel, crank, or adjust knob for a machine shaft. The shaft
bore is modelled per bore type so it drives the real shaft: plain round,
D-flat (circle + chord), keyway (circle + rectangular keyseat), or hex (across-
flats socket). A radial setscrew locks the boss to the shaft.

Three parts, dispatched by `target_part`:
  - handwheel : a spoked (or solid) wheel with a hub and rim, plus an optional
                revolving handle knob on the rim.
  - crank     : a single offset crank arm from the hub to a handle knob (no rim).
  - knob      : a small round fluted knob for fine adjustment.

Bore fit: printed holes come out undersize — `bore_fit` adds per-side clearance
so the boss slips onto the shaft; tolerance_by_material is declared.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bore_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr. Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
bore_dia    = float(PARAM(lambda: bore_dia,     10.0))  # shaft diameter
bore_type   = str(  PARAM(lambda: bore_type, "round"))  # round|dflat|keyway|hex
bore_fit    = float(PARAM(lambda: bore_fit,      0.2))  # per-side bore clearance
wheel_dia   = float(PARAM(lambda: wheel_dia,    90.0))  # wheel outer diameter
rim_t       = float(PARAM(lambda: rim_t,        12.0))  # rim thickness (radial section)
rim_w       = float(PARAM(lambda: rim_w,        14.0))  # rim/hub width (axial thickness)
hub_dia     = float(PARAM(lambda: hub_dia,      26.0))  # hub outer diameter
hub_len     = float(PARAM(lambda: hub_len,      22.0))  # hub length along shaft
spokes      = int(  PARAM(lambda: spokes,          3))  # spoke count (0 = solid disc)
spoke_w     = float(PARAM(lambda: spoke_w,      10.0))  # spoke width
handle      = bool( PARAM(lambda: handle,       True))  # revolving handle knob
handle_off  = float(PARAM(lambda: handle_off,   34.0))  # handle offset from centre
handle_dia  = float(PARAM(lambda: handle_dia,   12.0))  # handle knob diameter
handle_len  = float(PARAM(lambda: handle_len,   28.0))  # handle knob length
setscrew    = bool( PARAM(lambda: setscrew,     True))  # radial setscrew hole
setscrew_d  = float(PARAM(lambda: setscrew_d,    4.0))  # setscrew hole (tap) diameter
crank_len   = float(PARAM(lambda: crank_len,    70.0))  # crank arm centre-to-handle

target_part = str(PARAM(lambda: target_part, "handwheel"))

# Effective bore radius with fit clearance.
bore_r = bore_dia / 2.0 + max(0.0, bore_fit)


# ── Bore cutter (per type) ───────────────────────────────────────────────────
def bore_cutter(length):
    """A through-bore cutter of `length`, base at z=0, shaped per bore_type."""
    if bore_type == "hex":
        # Hex socket across-flats = bore_dia; circumradius = AF / sqrt(3).
        af = bore_dia + 2.0 * max(0.0, bore_fit)
        cr = af / math.sqrt(3.0)
        pts = [(cr * math.cos(math.radians(60 * k)), cr * math.sin(math.radians(60 * k))) for k in range(6)]
        return (
            cq.Workplane("XY").polyline(pts).close().extrude(length + 2.0).translate((0, 0, -1.0))
        )

    cutter = cq.Workplane("XY").circle(bore_r).extrude(length + 2.0).translate((0, 0, -1.0))

    if bore_type == "dflat":
        # D-flat: shave a chord off the round bore. Flat sits at ~0.8·radius.
        flat_at = bore_r * 0.8
        slab = (
            cq.Workplane("XY")
            .box(bore_dia * 2.0, bore_dia * 2.0, length + 4.0, centered=(True, True, True))
            .translate((flat_at + bore_dia, 0, length / 2.0))
        )
        cutter = cutter.union(slab)
    elif bore_type == "keyway":
        # Keyway: add a rectangular keyseat outward from the bore.
        key_w = max(2.0, bore_dia * 0.25)
        key_depth = max(1.5, bore_dia * 0.12)
        key = (
            cq.Workplane("XY")
            .box(key_w, bore_r + key_depth, length + 2.0, centered=(True, False, False))
            .translate((0, 0, -1.0))
        )
        cutter = cutter.union(key)
    return cutter


def add_bore_and_setscrew(solid, boss_len):
    """Cut the shaft bore through the hub and an optional radial setscrew hole."""
    solid = solid.cut(bore_cutter(boss_len))
    if setscrew and setscrew_d > 0.1:
        # Radial hole from the hub OD into the bore, centred on the hub height.
        ss = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, boss_len * 0.5), rotate=cq.Vector(0, 90, 0))
            .circle(setscrew_d / 2.0)
            .extrude(hub_dia / 2.0 + 1.0)
        )
        solid = solid.cut(ss)
    return solid


# ── Handle knob (shared by wheel and crank) ──────────────────────────────────
def handle_knob(offset, base_w):
    """An upright revolving handle: a barrelled post revolved as ONE solid so the
    union with the wheel is a single clean interface. Stands on the face at
    radius `offset`; base_w = axial thickness it stands on."""
    r = handle_dia / 2.0
    h = handle_len
    neck = max(1.5, r * 0.55)          # waisted neck near the base for grip
    # Half-profile in the XZ plane (x = radius from post axis, y = height),
    # revolved 360° about the Z axis → a smooth barrelled knob with a domed top.
    profile = [
        (0.0, 0.0),
        (neck, 0.0),
        (r, h * 0.30),
        (r, h * 0.72),
        (r * 0.80, h * 0.92),
        (r * 0.42, h),
        (0.0, h),
    ]
    knob = (
        cq.Workplane("XZ")
        .polyline(profile)
        .close()
        .revolve(360)
    )
    # revolve about X gives axis along X; reorient so height runs along +Z.
    knob = knob.rotate((0, 0, 0), (1, 0, 0), 90)
    return knob.translate((offset, 0, base_w))


# ── Handwheel ────────────────────────────────────────────────────────────────
def build_handwheel():
    outer_r = wheel_dia / 2.0
    rim_inner_r = outer_r - rim_t

    # Hub.
    hub = cq.Workplane("XY").cylinder(hub_len, hub_dia / 2.0).translate((0, 0, hub_len / 2.0))

    # Rim as a ring (outer cylinder minus inner cylinder), width rim_w.
    rim_outer = cq.Workplane("XY").cylinder(rim_w, outer_r).translate((0, 0, rim_w / 2.0))
    rim_bore = cq.Workplane("XY").cylinder(rim_w + 2.0, rim_inner_r).translate((0, 0, rim_w / 2.0 - 1.0))
    rim = rim_outer.cut(rim_bore)

    body = hub.union(rim)

    # Spokes (0 = solid disc web instead).
    if spokes <= 0:
        disc = cq.Workplane("XY").cylinder(rim_w * 0.6, rim_inner_r + 0.5).translate((0, 0, rim_w * 0.6 / 2.0))
        body = body.union(disc)
    else:
        for i in range(spokes):
            ang = 360.0 / spokes * i
            length = rim_inner_r + 2.0
            spoke = (
                cq.Workplane("XY")
                .box(length, spoke_w, rim_w * 0.7, centered=(False, True, False))
                .translate((0, 0, 0))
                .rotate((0, 0, 0), (0, 0, 1), ang)
            )
            body = body.union(spoke)

    # Optional revolving handle on the rim face.
    if handle:
        off = min(handle_off, rim_inner_r - handle_dia / 2.0 - 1.0)
        off = max(off, hub_dia / 2.0 + handle_dia / 2.0 + 1.0)
        body = body.union(handle_knob(off, rim_w))

    body = add_bore_and_setscrew(body, hub_len)
    return body


# ── Crank ────────────────────────────────────────────────────────────────────
def build_crank():
    # Hub.
    hub = cq.Workplane("XY").cylinder(hub_len, hub_dia / 2.0).translate((0, 0, hub_len / 2.0))

    # Arm: a flat bar from centre out to the handle position.
    arm_w = max(spoke_w, hub_dia * 0.5)
    arm_t = rim_w
    arm = (
        cq.Workplane("XY")
        .box(crank_len + arm_w, arm_w, arm_t, centered=(False, True, False))
        .translate((-arm_w / 2.0, 0, 0))
    )
    # Round the outboard end.
    end_boss = cq.Workplane("XY").cylinder(arm_t, arm_w / 2.0).translate((crank_len, 0, arm_t / 2.0))
    body = hub.union(arm).union(end_boss)

    # Handle knob always present at the crank end (that's the point of a crank).
    body = body.union(handle_knob(crank_len, arm_t))

    body = add_bore_and_setscrew(body, hub_len)
    return body


# ── Knob ─────────────────────────────────────────────────────────────────────
def build_knob():
    # A short fluted knob for fine adjustment: cylinder with scalloped flutes.
    knob_r = max(hub_dia / 2.0, bore_r + 6.0)
    knob_h = max(hub_len, 18.0)
    body = cq.Workplane("XY").cylinder(knob_h, knob_r).translate((0, 0, knob_h / 2.0))

    # Flutes: subtract a ring of small cylinders around the edge for grip.
    flute_n = max(8, int(knob_r * 1.2))
    flute_r = knob_r * 0.14
    for k in range(flute_n):
        ang = 360.0 / flute_n * k
        fx = knob_r * math.cos(math.radians(ang))
        fy = knob_r * math.sin(math.radians(ang))
        flute = cq.Workplane("XY").cylinder(knob_h + 2.0, flute_r).translate((fx, fy, knob_h / 2.0))
        body = body.cut(flute)

    # Soften the top edge.
    try:
        body = body.faces(">Z").chamfer(min(1.5, knob_r * 0.15))
    except Exception:
        pass

    body = add_bore_and_setscrew(body, knob_h)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "crank":
    result = build_crank()
elif target_part == "knob":
    result = build_knob()
else:
    result = build_handwheel()
