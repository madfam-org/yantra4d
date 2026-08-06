"""
Bottle-Thread Cap & Coupler — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Turns any discarded PET bottle into infrastructure. Generates screw caps,
bottle-to-bottle couplers, and spout adapters whose FUNCTIONAL interface is a
real single-start helical thread matched to standard bottle-neck finishes
(PCO-1881, PCO-1810, 28-410, 38-400). This is the input side of the Faircap
water-filter ecosystem: a bottle is the vessel, the thread is the connector.

Thread strategy (verified watertight + fast, ~1-4 s per render):
  Bottle necks are short, so we sweep a trapezoidal profile along a genuine
  `makeHelix` path for only ~1-2 turns. The rib's ROOT radius is pushed a little
  way into the surrounding wall material (the `overlap`), so the union with the
  bore wall is a clean volumetric boolean instead of a fragile tangent kiss —
  that is what keeps the mesh watertight. (A rib whose root sits exactly on the
  bore surface tessellates into cracks; overlapping it fixes that.)

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `neck_standard`).
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


# ── Bottle-neck finish standards (nominal geometry) ──────────────────────────
# major_d = thread outer (major) diameter in mm; pitch = thread pitch in mm.
# Values are dimensionally sensible nominal figures for each finish series so the
# mating interface is real; printed threads add the user `clearance` on top.
NECK_STANDARDS = {
    # PCO-1881: the ubiquitous soda / water bottle finish. Short single-start
    # buttress-ish thread, ~1 turn. This is the default.
    "PCO-1881": {"major_d": 27.4, "pitch": 2.7, "turns": 1.0},
    # PCO-1810: same neck family, taller thread engagement (~1.5 turns).
    "PCO-1810": {"major_d": 27.4, "pitch": 2.7, "turns": 1.5},
    # 28-410: personal-care / trigger-spray finish, ~28 mm, 8-TPI-ish pitch.
    "28-410":   {"major_d": 28.0, "pitch": 3.18, "turns": 1.5},
    # 38-400: wide-mouth finish (jars, large containers), coarse pitch.
    "38-400":   {"major_d": 38.0, "pitch": 4.2, "turns": 1.25},
}


def neck_geo(name):
    """Look up nominal neck geometry, defaulting to PCO-1881."""
    return NECK_STANDARDS.get(name, NECK_STANDARDS["PCO-1881"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part   = str(  PARAM(lambda: target_part,   "cap"))      # cap | coupler | spout_adapter
neck_standard = str(  PARAM(lambda: neck_standard,  "PCO-1881"))  # primary neck finish
neck_standard_b = str(PARAM(lambda: neck_standard_b, "PCO-1881")) # second end (coupler only)

clearance   = float(PARAM(lambda: clearance,   0.4))   # printed-thread fit slop (per side, mm)
wall        = float(PARAM(lambda: wall,        2.6))   # side wall thickness (mm)
top_th      = float(PARAM(lambda: top_th,      2.2))   # cap top / web thickness (mm)
extra_turns = float(PARAM(lambda: extra_turns, 0.0))   # add engagement turns beyond nominal
grip_knurl  = bool( PARAM(lambda: grip_knurl,  True))  # outer grip facets on cap
domed_top   = bool( PARAM(lambda: domed_top,   False)) # dome the cap top instead of flat
vent_hole   = bool( PARAM(lambda: vent_hole,   False)) # small vent hole through cap top
vent_dia    = float(PARAM(lambda: vent_dia,    3.0))   # vent hole diameter (mm)
spout_dia   = float(PARAM(lambda: spout_dia,   9.0))   # spout adapter nozzle bore (mm)
spout_len   = float(PARAM(lambda: spout_len,  22.0))   # spout adapter nozzle length (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
clearance = max(0.0, min(clearance, 1.0))
wall = max(1.6, min(wall, 6.0))
top_th = max(1.2, min(top_th, 6.0))
extra_turns = max(0.0, min(extra_turns, 2.0))


# ── Thread primitives (inlined — imports of repo libs are blocked in sandbox) ─
def _helix_path(pitch, height):
    """A helical wire centered on Z. Radius ~0 so the swept profile (already at
    the target radius in its own plane) traces the true helix."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib. Ridges point INWARD from the bore wall to
    grab a male bottle thread. Root radius = bore_r + overlap so the rib bites
    into the wall material (clean, watertight union). Crest at bore_r - thr_depth."""
    root_r = bore_r + overlap
    crest_r = max(0.5, bore_r - thr_depth)
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32),
            (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14),
            (root_r, pitch * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, thread_h), isFrenet=True)
    # Nudge up half a pitch so the rib starts inside the wall, not at the open rim.
    return rib.translate((0, 0, pitch * 0.5))


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    """External (male) helical rib. Root at shaft surface (bites in by overlap),
    crest sticks OUT to shaft_r + thr_depth."""
    root_r = max(0.5, shaft_r - overlap)
    crest_r = shaft_r + thr_depth
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32),
            (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14),
            (root_r, pitch * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, thread_h), isFrenet=True)
    return rib.translate((0, 0, pitch * 0.5))


def threaded_socket(std_name, extra_t, clear, wall_th, base_th, with_base):
    """A cylindrical socket with an internal female thread for `std_name`.

    Returns (solid, socket_height, outer_d, bore_r, thread_h). The socket opens
    at z=0 (bottom); `with_base` closes the top with a `base_th` disk. Geometry
    is built so the caller can stack/flip it for caps, couplers, and adapters."""
    g = neck_geo(std_name)
    # Real bottle necks engage ~1-1.5 turns; cap the total at 2.5 turns. Beyond
    # that the helical-rib/bore boolean union grows super-linearly (a 3+ turn
    # fuse costs ~20 s), and the extra turns are not physically meaningful.
    turns = min(2.5, g["turns"] + extra_t)
    pitch = g["pitch"]
    # Female bore is the male major diameter plus clearance per side.
    thr_major = g["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall_th * 0.35 + 0.2)
    thread_h = pitch * turns

    outer_d = thr_major + 2.0 * wall_th
    body_h = thread_h + (base_th if with_base else 0.0) + 1.5

    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    # Hollow the bore from the bottom up to (but not through) the base.
    bore_depth = thread_h + (0.0 if with_base else 2.0) + 0.6
    bore = cq.Workplane("XY").circle(bore_r).extrude(bore_depth)
    body = body.cut(bore)
    # Add the functional female thread.
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r, thread_h


def apply_knurl(solid, outer_d, height, teeth=24, depth=0.7):
    """Cut shallow vertical flutes around the outside for grip. Built as a single
    polar-array cutter (one boolean) so it stays cheap and watertight."""
    r = outer_d / 2.0
    try:
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=r, startAngle=0, angle=360, count=teeth)
            .rect(depth, depth * 3.0)
            .extrude(height + 2.0)
            .translate((0, 0, -1.0))
        )
        solid = solid.cut(cutter)
    except Exception:
        pass  # knurl is cosmetic — never fatal
    return solid


# ── Part builders ────────────────────────────────────────────────────────────
def build_cap():
    """Screw cap: internal female thread on the selected neck, flat or domed top,
    optional grip knurl, optional vent hole."""
    body, body_h, outer_d, bore_r, thread_h = threaded_socket(
        neck_standard, extra_turns, clearance, wall, top_th, with_base=True
    )

    if domed_top:
        # Round the top with a low truncated cone (a clean loft, unioned with a
        # small overlap so the boolean is watertight). Reads as a domed cap and
        # avoids the axis-pole meshing artifacts of a revolved/sphere dome.
        R = outer_d / 2.0
        dome_h = R * 0.30
        tip_r = R * 0.55
        ov = 0.8
        try:
            cone = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, body_h - ov))
                .circle(R)
                .workplane(offset=dome_h + ov)
                .circle(tip_r)
                .loft(combine=True)
            )
            body = body.union(cone)
            body_h = body_h + dome_h
            try:
                body = body.edges(">Z").fillet(min(tip_r * 0.6, dome_h * 0.6))
            except Exception:
                pass  # tip rounding is optional
        except Exception:
            pass  # dome is aesthetic — fall back to flat top

    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)

    if vent_hole:
        vr = max(0.5, min(vent_dia, bore_r * 1.2) / 2.0)
        vent = cq.Workplane("XY").circle(vr).extrude(body_h + 10.0).translate((0, 0, -1.0))
        body = body.cut(vent)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_coupler():
    """Bottle-to-bottle coupler: female thread on BOTH ends so two bottles join
    neck-to-neck. `neck_standard_b` sets the second end (dissimilar coupler)."""
    web = max(1.6, top_th)

    # Bottom end: female socket opening downward. Build it opening up, then flip.
    segA, hA, odA, brA, thA = threaded_socket(
        neck_standard, extra_turns, clearance, wall, 0.0, with_base=False
    )
    segA = segA.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, hA))

    # Central web disk between the two ends.
    max_od = max(odA, 0.0)

    # Top end: female socket opening upward, stacked above the web.
    segB, hB, odB, brB, thB = threaded_socket(
        neck_standard_b, extra_turns, clearance, wall, 0.0, with_base=False
    )
    max_od = max(odA, odB)
    web_disk = cq.Workplane("XY").circle(max_od / 2.0).extrude(web).translate((0, 0, hA))
    segB = segB.translate((0, 0, hA + web))

    coupler = segA.union(web_disk).union(segB)

    # Through channel so liquid passes between the two bottles.
    chan_r = max(1.0, min(brA, brB) - 1.4)
    channel = (
        cq.Workplane("XY")
        .circle(chan_r)
        .extrude(hA + web + hB + 2.0)
        .translate((0, 0, -1.0))
    )
    coupler = coupler.cut(channel)

    try:
        coupler = coupler.clean()
    except Exception:
        pass
    return coupler


def build_spout_adapter():
    """Female bottle thread on the bottom, a reduced nozzle/spout on top. Turns a
    bottle into a squeeze / pour vessel."""
    # Base: female socket opening downward onto the bottle neck.
    segA, hA, odA, brA, thA = threaded_socket(
        neck_standard, extra_turns, clearance, wall, top_th, with_base=True
    )
    # segA opens upward with a closed base on top; flip so it screws DOWN onto the
    # bottle and the closed shoulder faces up to carry the spout.
    segA = segA.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, hA))

    shoulder_z = hA  # top surface of the flipped socket (the closed base)

    # Nozzle: a tapered tube rising from the shoulder.
    s_bore = max(1.5, min(spout_dia, odA - 3.0)) / 2.0
    s_len = max(6.0, min(spout_len, 60.0))
    nozzle_wall = max(1.4, wall - 0.6)
    base_outer_r = min(odA / 2.0 - 0.5, s_bore + nozzle_wall + 3.0)
    tip_outer_r = s_bore + nozzle_wall

    # Outer tapered cone (loft between base and tip radius).
    nozzle_outer = (
        cq.Workplane("XY")
        .circle(base_outer_r)
        .workplane(offset=s_len)
        .circle(tip_outer_r)
        .loft(combine=True)
        .translate((0, 0, shoulder_z))
    )
    body = segA.union(nozzle_outer)

    # Bore the spout channel through the nozzle AND the shoulder into the bottle.
    channel = (
        cq.Workplane("XY")
        .circle(s_bore)
        .extrude(s_len + top_th + 2.0)
        .translate((0, 0, shoulder_z - top_th - 1.0))
    )
    body = body.cut(channel)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "coupler":
    result = build_coupler()
elif target_part == "spout_adapter":
    result = build_spout_adapter()
else:
    result = build_cap()
