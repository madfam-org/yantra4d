"""
IV Pole Clamp — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The mounting spine of the ward. A split clamp that grips a round IV pole
(19–25 mm is the usual range) and presents a DOVETAIL accessory face. Anything
that speaks the same dovetail — starting with `drip-chamber-holder` — slides on
and locks without a second tool.

The pole-diameter series is published as a CDG socket interface, so a clamp and
an accessory generated at the same `pole_dia` are guaranteed to share a pole;
the dovetail is published separately so accessories can be authored against the
face without knowing the pole size at all.

Modes:
  - dovetail_clamp : split clamp + pinch bolt + dovetail accessory face.
  - hook_clamp     : the same clamp carrying a bag hook instead of a dovetail.
  - dovetail_shoe  : the mating shoe on its own — the piece an accessory
                     inherits so it can ride any dovetail_clamp.

Watertight strategy: the clamp is ONE extruded solid. The pole bore is a single
through-cut; the split kerf is one thin slot from the bore out to the rim; the
pinch-bolt hole is one cross-drill through the two ears, drilled after the ears
are unioned on. The dovetail is a trapezoid prism UNIONED to the back with a
deliberate 0.2 mm overlap, so it can never be a separate body. Every derived
radius is clamped so the bore + kerf can never sever the ring.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

A printed clamp is a convenience mount. Do NOT hang an infusion pump, a
patient-load device, or anything whose fall would injure someone; verify the
grip under the intended load first.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "dovetail_clamp"))
# "dovetail_clamp" | "hook_clamp" | "dovetail_shoe"

pole_dia   = float(PARAM(lambda: pole_dia,  22.0))  # IV pole OUTER diameter
grip_fit   = float(PARAM(lambda: grip_fit,   0.3))  # per-side bore clearance
wall       = float(PARAM(lambda: wall,       6.0))  # clamp ring wall thickness
clamp_h    = float(PARAM(lambda: clamp_h,   26.0))  # clamp height along the pole
kerf       = float(PARAM(lambda: kerf,       2.2))  # split-kerf width
bolt_dia   = float(PARAM(lambda: bolt_dia,   5.3))  # M5 clearance for the pinch bolt
nut_af     = float(PARAM(lambda: nut_af,     8.1))  # M5 nut across-flats pocket
dove_w     = float(PARAM(lambda: dove_w,    18.0))  # dovetail width at its widest
dove_h     = float(PARAM(lambda: dove_h,     8.0))  # dovetail projection depth
dove_angle = float(PARAM(lambda: dove_angle, 60.0)) # dovetail flank angle
hook_len   = float(PARAM(lambda: hook_len,  26.0))  # bag-hook reach (hook_clamp)

# ── Clamps ───────────────────────────────────────────────────────────────────
pole_dia   = max(10.0, min(pole_dia, 60.0))
grip_fit   = max(0.0,  min(grip_fit, 2.0))
wall       = max(2.5,  min(wall, 20.0))
clamp_h    = max(8.0,  min(clamp_h, 90.0))
kerf       = max(0.8,  min(kerf, 10.0))
bolt_dia   = max(2.0,  min(bolt_dia, 12.0))
nut_af     = max(3.0,  min(nut_af, 22.0))
dove_w     = max(6.0,  min(dove_w, 80.0))
dove_h     = max(2.0,  min(dove_h, 40.0))
dove_angle = max(40.0, min(dove_angle, 80.0))
hook_len   = max(8.0,  min(hook_len, 90.0))

# ── Derived, clamped so the ring can never be severed ────────────────────────
R_BORE = pole_dia / 2.0 + grip_fit
R_OUT = R_BORE + wall
# Kerf must be narrower than the wall it passes through, or the ring falls open.
KERF = min(kerf, wall * 0.9, R_BORE * 1.2)
KERF = max(0.4, KERF)

# Pinch ears stand off the +Y side of the ring, straddling the kerf.
EAR_W = max(bolt_dia + 3.0, wall * 1.2)
EAR_L = max(bolt_dia * 2.2, wall * 2.0)
EAR_GAP = KERF          # the ears are split by the same kerf
# Bolt cross-drills through the ears along X.
BOLT_R = min(bolt_dia / 2.0, EAR_W / 2.0 - 1.0, clamp_h / 4.0)
BOLT_R = max(0.6, BOLT_R)
NUT_AF = min(nut_af, EAR_W - 1.0)
NUT_AF = max(2.0 * BOLT_R + 0.6, NUT_AF)
BOLT_Z = clamp_h / 2.0
EAR_Y = R_OUT + EAR_L / 2.0 - 0.4   # overlaps the ring by 0.4 mm

# Dovetail on the -Y (back) face. Narrow at the face, wide at the tip.
DOVE_W = min(dove_w, 2.0 * R_OUT * 0.9)
DOVE_W = max(3.0, DOVE_W)
DOVE_H = min(dove_h, R_OUT * 1.5)
DOVE_H = max(1.0, DOVE_H)
FLANK = math.radians(90.0 - dove_angle)
DOVE_NARROW = max(1.5, DOVE_W - 2.0 * DOVE_H * math.tan(FLANK))
DOVE_NARROW = min(DOVE_NARROW, DOVE_W - 0.4)

# Hook geometry.
HOOK_T = max(2.5, wall * 0.5)
HOOK_L = hook_len


# ── Helpers ──────────────────────────────────────────────────────────────────
def clamp_ring():
    """Ring + pinch ears as ONE solid, before any cut."""
    ring = cq.Workplane("XY").circle(R_OUT).extrude(clamp_h)
    ears = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, EAR_Y, 0))
        .box(EAR_W, EAR_L, clamp_h, centered=(True, True, False))
    )
    return ring.union(ears)


def pole_bore():
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(R_BORE)
        .extrude(clamp_h + 2.0)
    )


def kerf_cut():
    """One slot from the bore out through the ears, splitting the +Y side."""
    length = EAR_Y + EAR_L / 2.0 + 2.0
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(KERF, length, clamp_h + 2.0, centered=(True, False, False))
    )


def bolt_cut():
    """Cross-drill through the ears along X, with a hex nut pocket on -X."""
    span = EAR_W + 6.0
    cyl = cq.Workplane("XY").circle(BOLT_R).extrude(span)
    cyl = cyl.rotate((0, 0, 0), (0, 1, 0), 90.0)
    cyl = cyl.translate((-span / 2.0, EAR_Y, BOLT_Z))
    # Hex nut pocket: a hexagonal prism on the -X face of the ear.
    pocket_d = min(EAR_W * 0.4, NUT_AF * 0.8)
    hexp = (
        cq.Workplane("YZ")
        .polygon(6, NUT_AF / math.cos(math.pi / 6.0))
        .extrude(pocket_d + 0.5)
    )
    hexp = hexp.translate((-EAR_W / 2.0 - 0.5, EAR_Y, BOLT_Z))
    return cyl.union(hexp)


def dovetail():
    """Trapezoid prism on the -Y face, narrow at the clamp and wide at the tip.

    Sketched flat on XY (X = width, Y = projection depth) and extruded along Z
    to the clamp height — so the trapezoid's parallel faces run up the pole.
    Its inboard edge sits 0.2 mm INSIDE the ring, so the union always overlaps
    and yields a single body."""
    y_face = -R_OUT + 0.2
    prof = (
        cq.Workplane("XY")
        .polyline(
            [
                (-DOVE_NARROW / 2.0, 0.0),
                (DOVE_NARROW / 2.0, 0.0),
                (DOVE_W / 2.0, -DOVE_H),
                (-DOVE_W / 2.0, -DOVE_H),
            ]
        )
        .close()
        .extrude(clamp_h)
    )
    return prof.translate((0, y_face, 0))


# ── Part builders ────────────────────────────────────────────────────────────
def build_dovetail_clamp():
    body = clamp_ring()
    body = body.union(dovetail())
    body = body.cut(pole_bore())
    body = body.cut(kerf_cut())
    body = body.cut(bolt_cut())
    return body


def build_hook_clamp():
    """Same clamp carrying a J-hook on the back for hanging an IV bag."""
    body = clamp_ring()
    # Hook: a vertical stem down the -Y face, then a J that curls back up.
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -R_OUT - HOOK_L / 2.0 + 0.2, 0))
        .box(max(4.0, HOOK_T * 1.6), HOOK_L, HOOK_T, centered=(True, True, False))
    )
    body = body.union(stem)
    # Upturned lip at the far end so the bag cannot slide off.
    lip_h = max(4.0, HOOK_L * 0.3)
    lip = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(0, -R_OUT - HOOK_L + HOOK_T / 2.0 + 0.2, 0)
        )
        .box(max(4.0, HOOK_T * 1.6), HOOK_T, lip_h, centered=(True, True, False))
    )
    body = body.union(lip)
    body = body.cut(pole_bore())
    body = body.cut(kerf_cut())
    body = body.cut(bolt_cut())
    return body


def build_dovetail_shoe():
    """The mating socket: a plate with the dovetail groove cut into it, plus
    two mounting holes. Accessories inherit this face."""
    plate_w = DOVE_W + 2.0 * max(3.0, wall * 0.7)
    plate_th = DOVE_H + max(2.5, wall * 0.5)
    body = (
        cq.Workplane("XY")
        .box(plate_w, plate_th, clamp_h, centered=(True, True, False))
    )
    # Groove: the dovetail profile plus a 0.2 mm per-side slide clearance,
    # opening on the +Y face.
    c = 0.2
    groove = (
        cq.Workplane("XY")
        .polyline(
            [
                (-DOVE_NARROW / 2.0 - c, plate_th / 2.0 + 0.5),
                (DOVE_NARROW / 2.0 + c, plate_th / 2.0 + 0.5),
                (DOVE_W / 2.0 + c, plate_th / 2.0 - DOVE_H),
                (-DOVE_W / 2.0 - c, plate_th / 2.0 - DOVE_H),
            ]
        )
        .close()
        .extrude(clamp_h + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(groove)
    # Two mounting holes drilled through the back land along Y, clear of the
    # groove (the groove only opens on +Y and stops at plate_th/2 - DOVE_H).
    hole_r = min(BOLT_R, plate_w / 6.0)
    if hole_r > 0.5 and clamp_h > 4.0 * hole_r + 4.0:
        tool = None
        for sz in (0.28, 0.72):
            h = (
                cq.Workplane("XY")
                .circle(hole_r)
                .extrude(plate_th + 2.0)
                .rotate((0, 0, 0), (1, 0, 0), -90.0)
                .translate((0, -plate_th / 2.0 - 1.0, clamp_h * sz))
            )
            tool = h if tool is None else tool.union(h)
        if tool is not None:
            body = body.cut(tool)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "hook_clamp":
    result = build_hook_clamp()
elif target_part == "dovetail_shoe":
    result = build_dovetail_shoe()
else:  # "dovetail_clamp"
    result = build_dovetail_clamp()
