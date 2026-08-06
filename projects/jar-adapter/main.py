"""
Wide-Mouth Jar Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Cross-links the mason-jar family with the PCO-1881 bottle family. Screw the adapter
onto a standard mason jar (70 mm regular-mouth or ~83 mm wide-mouth continuous
thread) and it presents a PCO-1881 MALE stub on top — so any PCO-1881 cap, coupler,
or spout (from the `bottle-thread`, `bird-feeder`, `faircap-filter`, `pet-dispenser`
cartridges) now fits a mason jar. Also generates a plain mason sealing lid and a
perforated sifter/shaker lid.

Two real helical threads:
  * a large mason-jar FEMALE thread (coarse continuous thread), and
  * a PCO-1881 MALE thread on the transfer stub.
Both are volumetric fused helical ribs swept along a genuine `makeHelix` path and
unioned into the wall, with the rib root pushed into the wall for a clean boolean.
Turn count is forced to a HALF-INTEGER (floor(n)+0.5): a whole-integer turn count
degenerates the OCCT helical sweep into a negative-volume / null body.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals; read them via
    PARAM(lambda: <name>, <default>).
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Thread finish standards (nominal geometry) ───────────────────────────────
# major_d = male thread outer (major) diameter; pitch = thread pitch; turns
# modeled at a physically sensible engagement, always snapped to a half-integer.
PCO1881 = {"major_d": 27.43, "pitch": 2.7, "turns": 3.5}
MASON = {
    # Regular-mouth mason: "70-450" / G70 continuous thread, coarse.
    "70mm": {"major_d": 70.0, "pitch": 6.0, "turns": 1.5},
    # Wide-mouth mason: "86-450" / G86; the thread crest OD is ~83 mm.
    "86mm": {"major_d": 83.0, "pitch": 6.0, "turns": 1.5},
}


def mason_geo(name):
    return MASON.get(name, MASON["70mm"])


def half_turns(n):
    """Nearest lower half-integer, never a whole integer (whole → null sweep)."""
    return math.floor(max(0.5, n)) + 0.5


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "jar_to_pco"))  # jar_to_pco|jar_cap|jar_sifter
jar_size = str(PARAM(lambda: jar_size, "70mm"))              # 70mm | 86mm

clearance = float(PARAM(lambda: clearance, 0.5))    # printed-thread fit slop (per side, mm)
wall = float(PARAM(lambda: wall, 3.0))              # radial wall around the jar thread (mm)
top_th = float(PARAM(lambda: top_th, 2.6))          # shoulder / lid thickness (mm)
jar_turns = float(PARAM(lambda: jar_turns, 1.5))    # mason-jar engagement turns
pco_turns = float(PARAM(lambda: pco_turns, 3.5))    # PCO-1881 stub engagement turns
pco_clearance = float(PARAM(lambda: pco_clearance, 0.3))  # PCO male-thread fit slop (mm)
bore_dia = float(PARAM(lambda: bore_dia, 18.0))     # transfer bore through the adapter (mm)

# Sifter lid
hole_dia = float(PARAM(lambda: hole_dia, 4.0))      # sifter hole diameter (mm)
hole_rings = float(PARAM(lambda: hole_rings, 3.0))  # concentric rings of holes

clearance = max(0.0, min(clearance, 1.2))
wall = max(2.0, min(wall, 6.0))
top_th = max(1.6, min(top_th, 6.0))
jar_turns = max(1.5, min(jar_turns, 3.5))
pco_turns = max(1.5, min(pco_turns, 4.5))
pco_clearance = max(0.0, min(pco_clearance, 1.0))
bore_dia = max(6.0, min(bore_dia, 40.0))
hole_dia = max(1.5, min(hole_dia, 10.0))
hole_rings = max(1.0, min(hole_rings, 5.0))


# ── Thread primitives (inlined — repo-lib imports blocked in sandbox) ─────────
def _helix_path(pitch, height):
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal female helical rib; root bites into the wall for a clean union."""
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
    return rib.translate((0, 0, pitch * 0.5))


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    """External male helical rib. Root bites into the shaft; crest sticks out."""
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


def mason_socket(size, clear, wall_th, base_th, n_turns):
    """A cylindrical socket with an internal mason-jar female thread and a closed
    base disk on top. Opens at z=0. Returns (solid, height, outer_d, bore_r)."""
    g = mason_geo(size)
    tt = half_turns(n_turns)
    pitch = g["pitch"]
    thr_major = g["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.5 * pitch
    overlap = min(0.8, wall_th * 0.35 + 0.25)
    thread_h = pitch * tt

    outer_d = thr_major + 2.0 * wall_th
    body_h = thread_h + base_th + 1.5

    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    bore = cq.Workplane("XY").circle(bore_r).extrude(thread_h + 0.6)
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r


def pco_male_stub(clear, n_turns, wall_th, from_z):
    """A PCO-1881 MALE-threaded stub rising from z=`from_z`. Returns
    (solid, stub_top_z, shaft_r). The stub is a solid shaft plus the male rib; the
    caller bores the transfer channel through it afterward."""
    g = PCO1881
    tt = half_turns(n_turns)
    pitch = g["pitch"]
    # Male major = neck major minus clearance per side (so a female cap fits over it).
    thr_major = g["major_d"] - 2.0 * clear
    shaft_r = thr_major / 2.0 - 0.55 * pitch  # shaft to the thread ROOT
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall_th * 0.35 + 0.2)
    thread_h = pitch * tt

    # The rib spans z ∈ [pitch*0.5, pitch*0.5 + thread_h] within the stub. The shaft
    # MUST be tall enough to bury the rib's top crest — otherwise the free rib tip
    # pokes past the shaft top and the mesh is non-watertight (fails > ~1.5 turns).
    shaft_h = thread_h + pitch + 1.0
    shaft = (
        cq.Workplane("XY").circle(shaft_r).extrude(shaft_h).translate((0, 0, from_z))
    )
    rib = male_thread(shaft_r, pitch, thread_h, thr_depth, overlap).translate((0, 0, from_z))
    stub = shaft.union(rib)
    return stub, from_z + shaft_h, shaft_r


# ── Part builders ────────────────────────────────────────────────────────────
def build_jar_to_pco():
    """Female mason-jar thread (bottom) + male PCO-1881 stub (top). Screw onto a
    mason jar; screw any PCO-1881 cap/coupler/spout onto the stub."""
    base, base_h, outer_d, jar_bore_r = mason_socket(
        jar_size, clearance, wall, top_th, jar_turns
    )
    # Socket opens DOWN at z=0 (screws onto the jar); closed shoulder at z≈base_h,
    # which carries the PCO stub. (Do NOT flip: flipping moves the closed shoulder
    # to the open rim and the stub would sever when the transfer bore is cut.)
    shoulder_z = base_h

    stub, stub_top_z, shaft_r = pco_male_stub(pco_clearance, pco_turns, wall, shoulder_z)
    body = base.union(stub)

    # Transfer bore straight through the stub and shoulder into the jar.
    br = max(2.0, min(bore_dia, 2.0 * shaft_r - 3.0) / 2.0)
    channel = (
        cq.Workplane("XY")
        .circle(br)
        .extrude(stub_top_z + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(channel)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_jar_cap():
    """A plain sealed mason-jar lid: female mason thread, solid top disk."""
    base, base_h, outer_d, jar_bore_r = mason_socket(
        jar_size, clearance, wall, top_th, jar_turns
    )
    # Socket opens DOWN at z=0; the sealed lid face is the top at z≈base_h.
    # Grip flutes around the skirt for hand tightening (single boolean).
    r = outer_d / 2.0
    try:
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=r, startAngle=0, angle=360, count=32)
            .rect(0.8, 2.4)
            .extrude(base_h + 2.0)
            .translate((0, 0, -1.0))
        )
        base = base.cut(cutter)
    except Exception:
        pass
    try:
        base = base.clean()
    except Exception:
        pass
    return base


def build_jar_sifter():
    """A mason-jar sifter / shaker lid: female mason thread, top disk perforated
    with concentric rings of holes (for spices, flour, seeds, dry goods)."""
    base, base_h, outer_d, jar_bore_r = mason_socket(
        jar_size, clearance, wall, top_th, jar_turns
    )
    # Socket opens DOWN at z=0; the perforated face is the sealed top at z≈base_h.
    # Perforate the top disk. Holes live inside the bore radius so the skirt stays
    # solid. Build all holes as one fused cutter, then a single boolean cut.
    hr = hole_dia / 2.0
    rings = int(round(hole_rings))
    max_r = jar_bore_r - hr - 2.0
    cutter = None
    # centre hole
    c0 = cq.Workplane("XY").circle(hr).extrude(top_th + 4.0).translate((0, 0, base_h - top_th - 2.0))
    cutter = c0
    for ring in range(1, rings + 1):
        rr = max_r * ring / rings
        count = max(4, int(round(2.0 * math.pi * rr / (hr * 4.0))))
        holes = (
            cq.Workplane("XY")
            .polarArray(radius=rr, startAngle=0, angle=360, count=count)
            .circle(hr)
            .extrude(top_th + 4.0)
            .translate((0, 0, base_h - top_th - 2.0))
        )
        cutter = cutter.union(holes)
    base = base.cut(cutter)
    try:
        base = base.clean()
    except Exception:
        pass
    return base


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "jar_cap":
    result = build_jar_cap()
elif target_part == "jar_sifter":
    result = build_jar_sifter()
else:
    result = build_jar_to_pco()
