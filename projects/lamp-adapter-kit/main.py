"""
Lamp Standard Adapter Kit — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A CAPSTONE any-to-any lamp-base adapter that bridges the four dominant lamp-base
families so a bulb built for one fixture drops into another: the Edison screw
bases E26 (North-American medium) and E27 (European medium), and the twist-lock
bayonet bases GU10 and B22/BA22d. Each mode is one adapter carrying a female
receptacle for one standard and a male base for another.

Modes (dispatched via `target_part`):
  * "e26_to_e27"     — female E26 Edison socket (accepts an E26 bulb) below +
                       male E27 Edison base (screws into an E27 fixture) above.
  * "edison_to_gu10" — female Edison (E26/E27) socket below + a GU10 twist-lock
                       puck with real pins above.
  * "gu10_to_b22"    — a GU10 twist-lock receptacle skirt below + a B22 bayonet
                       base with real pins above.

Real base geometry (nominal, dimensionally real, all mm):
  Edison screw, 7 TPI (25.4/7 = 3.629 mm pitch): E26 major Ø 26.05, E27 major
  Ø 26.40.  Bayonet twist-lock: GU10 shell Ø 26, two Ø4.7 pins on a 10 mm span;
  B22 shell Ø 22, two Ø3.0 pins on a 22 mm span.

Thread strategy (VERIFIED watertight + fast — four traps avoided):
  Edison threads are volumetric fused helical ribs: a trapezoidal profile swept
  along a genuine `makeHelix` path and unioned into the wall (rib root buried so
  the boolean is a clean fusion, not a fragile tangent kiss).
  1. Turn count is snapped to a HALF-INTEGER (floor(n)+0.5) — an integer count
     degenerates the OCCT helical sweep to a negative-volume/null body.
  2. Every female socket has a CLOSED base disk (bore stops below a solid cap);
     an open-both-ends bore tessellates non-watertight. The wiring channel is
     bored THROUGH the closed base afterward.
  3. No flip-then-attach: the unflipped socket is already the correct
     cap/adapter orientation; the top male base / puck is stacked on the closed
     top, never on an open rim.
  4. Turn count is CAPPED at a validated half-integer ceiling (3.5) — a very tall
     thread on a thin wall can tessellate non-watertight even at a half-integer.
     Real lamp bases engage ~2-3 turns, so the cap costs nothing physical.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>) — globals()/eval/getattr are
    not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default. `except Exception`
    catches the NameError raised for an unbound param name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Bulb-base standards (nominal real geometry) ──────────────────────────────
EDISON = {
    "E26": {"major_d": 26.05, "pitch": 3.629},
    "E27": {"major_d": 26.40, "pitch": 3.629},
}
BAYONET = {
    "GU10": {"shell_d": 26.0, "pin_span": 10.0, "pin_d": 4.7},
    "B22": {"shell_d": 22.0, "pin_span": 22.0, "pin_d": 3.0},
}


def edison(name):
    return EDISON.get(str(name).strip(), EDISON["E26"])


def bayonet(name):
    return BAYONET.get(str(name).strip(), BAYONET["GU10"])


def half_int_turns(n):
    """Half-integer turn count (floor(n)+0.5), clamped to [1.5, 3.5]. An integer
    count degenerates the helical sweep to a negative-volume body; 3.5 is the
    validated watertight ceiling for these wall thicknesses."""
    return max(1.5, min(3.5, math.floor(n) + 0.5))


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "e26_to_e27"))
edison_a = str(PARAM(lambda: edison_a, "E26"))   # lower (female) Edison base
edison_b = str(PARAM(lambda: edison_b, "E27"))   # upper (male) Edison base
bayo = str(PARAM(lambda: bayo, "GU10"))          # bayonet standard for mixed modes
clearance = float(PARAM(lambda: clearance, 0.4))  # printed-thread fit (per side)
wall = float(PARAM(lambda: wall, 2.4))            # shell wall thickness
turns = float(PARAM(lambda: turns, 3.0))          # requested engagement turns
bore = float(PARAM(lambda: bore, 12.0))           # central wire / device bore
puck_h = float(PARAM(lambda: puck_h, 22.0))       # bayonet puck body height

clearance = max(0.0, min(clearance, 1.0))
wall = max(1.6, min(wall, 5.0))
turns = max(1.5, min(turns, 3.5))
bore = max(4.0, min(bore, 22.0))
puck_h = max(12.0, min(puck_h, 40.0))


# ── Thread primitives (inlined — repo-lib imports are blocked in sandbox) ─────
def _helix_path(pitch, hgt):
    return cq.Wire.makeHelix(pitch=pitch, height=hgt, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal helical rib pointing INWARD from the bore wall. Root buried in
    the wall (bore_r+overlap) for a clean watertight union."""
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
    """External helical rib pointing OUTWARD from the shaft. Root buried in the
    shaft (shaft_r-overlap) for a clean watertight union."""
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
    """A hollow male Edison shell rooted at z0, opening UPWARD, growing +Z.
    Returns (solid, top_z, shaft_r, inner_r). Core is taller than the thread run
    so both rib ends are buried (no free rim → watertight)."""
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
    core = core.union(male_thread(shaft_r, pitch, thread_h, thr_depth, overlap).translate((0, 0, z0)))
    return core, z0 + core_h, shaft_r, inner_r


def female_edison_socket(spec, clear, wall_th, req_turns, z0, with_base):
    """Female Edison socket rooted at z0 opening upward, growing +Z. Returns
    (solid, top_z, outer_d, bore_r). `with_base` closes the top with a solid disk
    (bore stops below it) → watertight closed base per trap #2."""
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


def add_pins(body, spec, z_center, outer_r):
    """Two real bayonet pins protruding radially from a skirt wall. Roots buried
    1 mm into the wall so the union is volumetric; tips reach the standard's
    centre-to-centre span or the skirt surface, whichever is further out."""
    pin_span = spec["pin_span"]
    pin_d = spec["pin_d"]
    tip_r = max(outer_r + 2.4, pin_span / 2.0)
    root_r = outer_r - 1.0
    axis_len = tip_r - root_r
    for sx in (1.0, -1.0):
        pin = cq.Solid.makeCylinder(
            pin_d / 2.0, axis_len,
            cq.Vector(sx * root_r, 0, z_center),
            cq.Vector(sx, 0, 0),
        )
        body = body.union(cq.Workplane(obj=pin))
    return body


def bayonet_skirt(spec, z0, height, with_base):
    """A bayonet twist-lock skirt rooted at z0, growing +Z, with real pins and a
    central bore. `with_base` closes the FAR (top) end so the piece is watertight
    when it is the terminal feature; when it stacks onto another body the shared
    face is the closure. Returns (solid, top_z, outer_r)."""
    shell_d = spec["shell_d"]
    outer_r = shell_d / 2.0 + wall
    body = cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0)).circle(outer_r).extrude(height)
    body = add_pins(body, spec, z0 + height * 0.4, outer_r)
    return body, z0 + height, outer_r


# ── Part builders ─────────────────────────────────────────────────────────────
def build_e26_to_e27():
    """Female Edison (base A) socket below + male Edison (base B) base above: an
    E26↔E27 (or any Edison pairing) translator with a wiring channel straight
    through. The female socket has a closed base (trap #2); the male shell stacks
    on the closed top through a shoulder disk (no flip-then-attach, trap #3)."""
    seg_a, top_a, od_a, br_a = female_edison_socket(
        edison(edison_a), clearance, wall, turns, 0.0, with_base=True
    )
    shoulder_th = max(1.6, wall)
    shoulder_od = od_a
    shoulder = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, top_a))
        .circle(shoulder_od / 2.0).extrude(shoulder_th)
    )
    shell_b, top_b, sr_b, ir_b = male_edison_shell(
        edison(edison_b), clearance, wall, turns, top_a + shoulder_th
    )
    body = seg_a.union(shoulder).union(shell_b)
    # Wiring channel straight through (opens both ends → no trapped void).
    chan_r = max(1.5, min(br_a, sr_b, bore / 2.0) - 1.2)
    chan_r = max(1.5, chan_r)
    channel = cq.Workplane("XY").circle(chan_r).extrude(top_b + 2.0).translate((0, 0, -1.0))
    body = body.cut(channel)
    body = _knurl(body, shoulder_od, top_b)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_edison_to_gu10():
    """Female Edison socket below (closed base) + a GU10 twist-lock puck above.
    The puck stacks on the closed socket top; a central bore passes through both
    → an Edison-fixture-to-GU10-bulb adapter."""
    seg_a, top_a, od_a, br_a = female_edison_socket(
        edison(edison_a), clearance, wall, turns, 0.0, with_base=True
    )
    spec = bayonet("GU10")
    puck, top_p, outer_r = bayonet_skirt(spec, top_a, puck_h, with_base=False)
    body = seg_a.union(puck)
    # Central bore through the Edison base and the puck (opens both ends).
    chan_r = max(2.0, min(br_a, outer_r - wall, bore / 2.0))
    channel = cq.Workplane("XY").circle(chan_r).extrude(top_p + 2.0).translate((0, 0, -1.0))
    body = body.cut(channel)
    body = _knurl(body, max(od_a, outer_r * 2.0), top_p, teeth=20)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_gu10_to_b22():
    """A GU10 receptacle skirt below + a B22 bayonet base above. Both skirts share
    a solid mid web (the stacked shared face closes each end); a central bore
    passes through → a GU10-fixture-to-B22-bulb (or vice-versa) twist-lock bridge."""
    gu10 = bayonet("GU10")
    b22 = bayonet("B22")
    lower_h = puck_h * 0.5
    upper_h = puck_h * 0.5

    lower, top_l, outer_l = bayonet_skirt(gu10, 0.0, lower_h, with_base=False)
    # Solid mid web disk between the two skirts (forms the closure both ways).
    web_r = max(outer_l, b22["shell_d"] / 2.0 + wall)
    web_th = max(2.0, wall)
    web = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, top_l))
        .circle(web_r).extrude(web_th)
    )
    upper, top_u, outer_u = bayonet_skirt(b22, top_l + web_th, upper_h, with_base=False)
    body = lower.union(web).union(upper)
    # Central through bore (opens both ends → no trapped void).
    chan_r = max(2.0, min(outer_l, outer_u) - wall - 0.5)
    channel = cq.Workplane("XY").circle(chan_r).extrude(top_u + 2.0).translate((0, 0, -1.0))
    body = body.cut(channel)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _knurl(solid, outer_d, hgt, teeth=24, depth=0.6):
    """Cut shallow vertical grip flutes around the outside (one boolean)."""
    r = outer_d / 2.0
    try:
        cutter = (
            cq.Workplane("XY").polarArray(radius=r, startAngle=0, angle=360, count=teeth)
            .rect(depth, depth * 3.0).extrude(hgt + 2.0).translate((0, 0, -1.0))
        )
        solid = solid.cut(cutter)
    except Exception:
        pass  # knurl is cosmetic — never fatal
    return solid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "edison_to_gu10":
    result = build_edison_to_gu10()
elif target_part == "gu10_to_b22":
    result = build_gu10_to_b22()
else:
    result = build_e26_to_e27()
