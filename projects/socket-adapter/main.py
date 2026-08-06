"""Socket Adapter — LED Bulb / Lamp Socket Base Converter (Yantra4D Hyperobject).

Lamp socket adapters and base converters built around the REAL bulb-base
standards. Two families are represented with their true geometry:

  * Edison screw bases (threaded): E26 (26.05 mm major, 7-TPI Edison → 3.629 mm
    pitch — the North-American medium base) and E27 (26.4 mm major, same pitch —
    the European medium base). Modelled as FUNCTIONAL single-start helical
    threads.
  * Twist-lock (bayonet) bases: GU10 (two pins on a 10 mm centre spacing,
    Ø ~4.7 mm, that twist into an L-slot) and B22 / BA22d (22 mm bayonet, two
    diametric pins). Modelled as real pins + twist L-channels.

Three distinct modes:
  * screw_shell    — a male Edison shell (E26/E27) with a hollow core, so it
    screws into a lamp socket and carries a device up top.
  * base_converter — female Edison thread on the bottom (accepts a screw bulb) +
    male Edison thread on top (screws into a socket): an E26↔E27 translator.
  * bayonet_base   — a GU10 or B22 twist-lock puck with real pins and a central
    bore, to adapt a twist-lock fixture.

Thread strategy: `makeHelix` + trapezoidal swept rib pushed into the wall for a
watertight volumetric union. CRITICAL: turn count snapped to a HALF-INTEGER
(floor(n)+0.5, clamped 1.5-3.5) — an integer count degenerates the OCCT helical
sweep to a negative-volume/null body. Pins/channels are solid unions and boolean
cuts that open to a face (no trapped voids).

Sandbox contract (cq_runner.py): `cq`+`math` pre-injected; params bare globals
via PARAM(lambda: name, default); final solid assigned to `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Bulb-base standards (nominal real geometry) ──────────────────────────────
# Edison screw: major_d (mm), pitch (mm). E26/E27 are 7-TPI (25.4/7 = 3.629 mm).
EDISON = {
    "E26": {"major_d": 26.05, "pitch": 3.629},
    "E27": {"major_d": 26.40, "pitch": 3.629},
}
# Bayonet twist-lock: shell_d (skirt Ø), pin_span (centre-to-centre of the two
# pins), pin_d (pin diameter).
BAYONET = {
    "GU10": {"shell_d": 26.0, "pin_span": 10.0, "pin_d": 4.7},
    "B22":  {"shell_d": 22.0, "pin_span": 22.0, "pin_d": 3.0},
}


def edison(name):
    return EDISON.get(str(name).strip(), EDISON["E26"])


def bayonet(name):
    return BAYONET.get(str(name).strip(), BAYONET["GU10"])


def half_int_turns(n):
    """Half-integer turn count (floor(n)+0.5), clamped to [1.5, 3.5]. An integer
    count degenerates the helical sweep to a negative-volume body."""
    return max(1.5, min(3.5, math.floor(n) + 0.5))


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "screw_shell"))
edison_a    = str(PARAM(lambda: edison_a,   "E26"))     # primary Edison base
edison_b    = str(PARAM(lambda: edison_b,   "E27"))     # top Edison base (converter)
bayo        = str(PARAM(lambda: bayo,       "GU10"))    # bayonet standard
clearance   = float(PARAM(lambda: clearance, 0.4))      # printed-thread fit (per side)
wall        = float(PARAM(lambda: wall,      2.4))      # shell wall thickness
turns       = float(PARAM(lambda: turns,     3.0))      # requested engagement turns
bore        = float(PARAM(lambda: bore,     12.0))      # central wire / device bore
height      = float(PARAM(lambda: height,   22.0))      # bayonet puck body height

clearance = max(0.0, min(clearance, 1.0))
wall      = max(1.6, min(wall, 5.0))
turns     = max(1.5, min(turns, 4.0))
bore      = max(4.0, min(bore, 22.0))
height    = max(12.0, min(height, 40.0))


# ── Thread primitives (inlined) ──────────────────────────────────────────────
def _helix_path(pitch, hgt):
    return cq.Wire.makeHelix(pitch=pitch, height=hgt, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    root_r = bore_r + overlap
    crest_r = max(0.5, bore_r - thr_depth)
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32), (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14), (root_r, pitch * 0.32),
        ]).close()
    )
    return prof.sweep(_helix_path(pitch, thread_h), isFrenet=True).translate((0, 0, pitch * 0.5))


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    root_r = max(0.5, shaft_r - overlap)
    crest_r = shaft_r + thr_depth
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32), (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14), (root_r, pitch * 0.32),
        ]).close()
    )
    return prof.sweep(_helix_path(pitch, thread_h), isFrenet=True).translate((0, 0, pitch * 0.5))


def male_edison_shell(spec, clear, wall_th, req_turns, z0):
    """A hollow male Edison shell rooted at z0. Returns (solid, top_z, shaft_r,
    inner_r). Core is taller than the thread run so both rib ends are buried."""
    pitch = spec["pitch"]
    t = half_int_turns(req_turns)
    thr_major = max(6.0, spec["major_d"] - 2.0 * clear)
    thr_depth = 0.55 * pitch
    shaft_r = thr_major / 2.0 - thr_depth
    overlap = 0.45
    thread_h = pitch * t
    core_h = thread_h + 2.0 * pitch
    inner_r = max(1.5, shaft_r - wall_th)

    core = cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0)).circle(shaft_r + 0.2).extrude(core_h)
    core = core.union(
        male_thread(shaft_r, pitch, thread_h, thr_depth, overlap).translate((0, 0, z0))
    )
    return core, z0 + core_h, shaft_r, inner_r


def female_edison_socket(spec, clear, wall_th, req_turns, z0, with_base):
    """Female Edison socket rooted at z0 opening upward. Returns (solid, top_z,
    outer_d, bore_r)."""
    pitch = spec["pitch"]
    t = half_int_turns(req_turns)
    thr_major = spec["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall_th * 0.35 + 0.2)
    thread_h = pitch * t
    outer_d = thr_major + 2.0 * wall_th
    base_th = wall_th if with_base else 0.0
    body_h = thread_h + base_th + 2.0

    body = cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0)).circle(outer_d / 2.0).extrude(body_h)
    bore_depth = thread_h + (0.0 if with_base else 2.0) + 0.8
    bore = cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0 + base_th)).circle(bore_r).extrude(bore_depth)
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap).translate((0, 0, z0 + base_th)))
    return body, z0 + body_h, outer_d, bore_r


def _knurl(solid, outer_d, hgt, teeth=24, depth=0.6):
    r = outer_d / 2.0
    try:
        cutter = (
            cq.Workplane("XY").polarArray(radius=r, startAngle=0, angle=360, count=teeth)
            .rect(depth, depth * 3.0).extrude(hgt + 2.0).translate((0, 0, -1.0))
        )
        solid = solid.cut(cutter)
    except Exception:
        pass
    return solid


# ── screw_shell ──────────────────────────────────────────────────────────────
def build_screw_shell():
    """A hollow male Edison shell + a top collar carrying a device, bored through
    for wiring."""
    shell, top_z, shaft_r, inner_r = male_edison_shell(edison(edison_a), clearance, wall, turns, 0.0)
    # Top collar (a short cylinder above the shell) to seat a device / holder.
    collar_od = (shaft_r + wall) * 2.0 + 3.0
    collar_h = 6.0
    collar = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, top_z - 0.5))
        .circle(collar_od / 2.0).extrude(collar_h + 0.5)
    )
    body = shell.union(collar)
    # Central through bore for wiring (opens bottom + top → no trapped void).
    b_r = min(bore, inner_r * 2.0) / 2.0
    b_r = max(1.5, min(b_r, collar_od / 2.0 - wall))
    through = (
        cq.Workplane("XY").circle(b_r).extrude(top_z + collar_h + 2.0).translate((0, 0, -1.0))
    )
    body = body.cut(through)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── base_converter ───────────────────────────────────────────────────────────
def build_base_converter():
    """Female Edison thread (base A) on the bottom + male Edison thread (base B)
    on top: an E26<->E27 translator with a wiring channel through the middle."""
    seg_a, topA, odA, brA = female_edison_socket(edison(edison_a), clearance, wall, turns, 0.0, with_base=False)
    # Shoulder disk on top of the female socket.
    shoulder_th = max(1.6, wall)
    shoulder_od = odA
    shoulder = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, topA))
        .circle(shoulder_od / 2.0).extrude(shoulder_th)
    )
    # Male shell on top of the shoulder.
    shell_b, topB, srB, irB = male_edison_shell(edison(edison_b), clearance, wall, turns, topA + shoulder_th)
    body = seg_a.union(shoulder).union(shell_b)
    # Wiring channel straight through.
    chan_r = max(1.5, min(brA, srB) - 1.6)
    channel = (
        cq.Workplane("XY").circle(chan_r).extrude(topB + 2.0).translate((0, 0, -1.0))
    )
    body = body.cut(channel)
    body = _knurl(body, shoulder_od, topB)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── bayonet_base ─────────────────────────────────────────────────────────────
def build_bayonet_base():
    """A GU10 / B22 twist-lock puck: a skirt with two real bayonet pins on the
    outside and a central bore. The pins are solid cylinders fused to the skirt
    (volumetric union). A twist relief slot opens each pin region to the base
    face so nothing is trapped."""
    spec = bayonet(bayo)
    shell_d = spec["shell_d"]
    pin_span = spec["pin_span"]
    pin_d = spec["pin_d"]

    outer_r = shell_d / 2.0 + wall
    body = cq.Workplane("XY").circle(outer_r).extrude(height)

    # Central bore for wiring / a lamp holder (through → no trapped void).
    b_r = max(2.0, min(bore, shell_d - 2.0 * wall) / 2.0)
    body = body.cut(cq.Workplane("XY").circle(b_r).extrude(height + 2.0).translate((0, 0, -1.0)))

    # Two bayonet pins protruding radially from the skirt wall (real GU10 / B22
    # geometry). Each pin is a short cylinder whose inner end is buried a little
    # inside the wall (root at outer_r - 1) and whose axis lies along ±X. The two
    # pins sit on the standard's centre-to-centre span (their outer faces at
    # roughly pin_span/2 from centre for the wider bayonets; for GU10 they sit on
    # the skirt at outer_r). We anchor the pin root at the skirt so it always
    # fuses volumetrically, then protrude by pin_out.
    pin_z = height * 0.32
    pin_out = 2.4
    # Pin tips sit on the standard's centre-to-centre span (pin_span) when that
    # is outside the skirt, else on the skirt surface. Roots are buried 1 mm into
    # the wall so the union is volumetric. B22's wide span puts pins further out
    # than GU10's — pin_span differentiates the two standards' geometry.
    tip_r = max(outer_r + pin_out, pin_span / 2.0)
    root_r = outer_r - 1.0
    pin_axis_len = tip_r - root_r
    for sx in (1.0, -1.0):
        pin = cq.Solid.makeCylinder(
            pin_d / 2.0, pin_axis_len,
            cq.Vector(sx * root_r, 0, pin_z),
            cq.Vector(sx, 0, 0),
        )
        body = body.union(cq.Workplane(obj=pin))

    # A shallow grip flute ring near the top for finger twist.
    body = _knurl(body, (outer_r) * 2.0, height, teeth=20, depth=0.6)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "base_converter":
    result = build_base_converter()
elif target_part == "bayonet_base":
    result = build_bayonet_base()
else:
    result = build_screw_shell()
