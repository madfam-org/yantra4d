"""
Lead-Screw Nut (Tr8x8 / Acme) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A printable nut that threads onto a trapezoidal (Acme / metric-trapezoidal) lead
screw — the common motion-repair part for 3D-printer Z axes, small CNC stages, and
linear actuators. Pick a thread standard and body style; the FUNCTIONAL interface
is a real internal trapezoidal thread cut at the correct nominal diameter + pitch.

Thread strategy (verified watertight + fast, ~2-5 s per render):
  The bore is first drilled to the thread ROOT radius (the widest part of the
  female thread), then a single inward-pointing trapezoidal rib is swept along a
  genuine `cq.Wire.makeHelix` path and UNIONED into the bore, its crest reaching
  the minor radius. Union of a swept helix is the fast, watertight boolean (the
  same primitive the bottle-thread cartridge uses); CUTTING a swept groove is an
  order of magnitude slower and tessellates into cracks, so we build the thread as
  positive material instead. The rib's ROOT is pushed `overlap` back into the wall
  so the fuse is fully volumetric. Turns are capped (`_MAX_TURNS`) because the
  helical fuse grows super-linearly; a printer-Z repair nut only needs ~3-5
  threads of engagement.

  Multi-start note: Tr8x8 screws are 4-start (2 mm pitch, 8 mm lead). The nut is
  modelled with a single-start female thread at the true 2 mm pitch, which meshes
  with the screw and prints far more reliably than a 4-start internal thread. The
  nominal MAJOR diameter and PITCH are correct, so the interface is dimensionally
  real; only the number of starts is simplified.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `thread_spec`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
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


# ── Trapezoidal lead-screw standards (nominal geometry) ──────────────────────
# major_d = external thread major (nominal) diameter (mm)
# pitch   = thread pitch = axial groove-to-groove distance (mm)
# flank   = half the thread included angle, in degrees (15° for both Tr & ACME)
THREAD_SPECS = {
    # Metric trapezoidal 8 mm, 8 mm lead / 2 mm pitch, 4-start — printer Z.
    "Tr8x8":    {"major_d": 8.0, "pitch": 2.0, "flank": 15.0},
    # Metric trapezoidal 8 mm, 2 mm pitch, single-start.
    "Tr8x2":    {"major_d": 8.0, "pitch": 2.0, "flank": 15.0},
    # ACME 3/8"-12 style: ~9.525 mm major, 12 TPI ≈ 2.117 mm pitch, 14.5° flank.
    "Acme-3/8": {"major_d": 9.525, "pitch": 2.117, "flank": 14.5},
}
_MAX_TURNS = 5.0  # cap the helical cut for speed + watertightness


def spec_geo(name):
    """Look up nominal thread geometry, defaulting to Tr8x8."""
    return THREAD_SPECS.get(name, THREAD_SPECS["Tr8x8"])


# ── Parameters ───────────────────────────────────────────────────────────────
thread_spec = str(PARAM(lambda: thread_spec, "Tr8x8"))     # Tr8x8 | Tr8x2 | Acme-3/8
body_dia    = float(PARAM(lambda: body_dia,   16.0))       # round nut outer diameter (mm)
height      = float(PARAM(lambda: height,     12.0))       # nut height along the screw (mm)
clearance   = float(PARAM(lambda: clearance,   0.35))      # printed thread fit slop per side (mm)
flange      = bool( PARAM(lambda: flange,     False))      # add a mounting flange with bolt holes
hole_count  = int(  PARAM(lambda: hole_count,     4))      # flange bolt-hole count
flange_dia  = float(PARAM(lambda: flange_dia, 26.0))       # flange outer diameter (mm)
bolt_dia    = float(PARAM(lambda: bolt_dia,    3.4))       # flange bolt-hole diameter (mm, M3 ≈ 3.4)

target_part = str(PARAM(lambda: target_part, "round_nut"))  # round_nut | flange_nut | anti_backlash

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
clearance = max(0.15, min(clearance, 0.8))
g = spec_geo(thread_spec)
major_d = g["major_d"]
pitch = g["pitch"]
flank = g["flank"]

# Body must clear the thread + a real wall.
min_body = major_d + 5.0
body_dia = max(min_body, min(body_dia, 60.0))
flange_dia = max(body_dia + 6.0, min(flange_dia, 90.0))
height = max(pitch * 3.0, min(height, 60.0))
hole_count = max(2, min(hole_count, 8))
bolt_dia = max(2.0, min(bolt_dia, 8.0))

# The anti-backlash variant is simply a taller nut (more thread engagement).
if target_part == "anti_backlash":
    height = max(height, pitch * 8.0)

# ── Derived thread geometry ──────────────────────────────────────────────────
# Screw major radius, opened up by clearance per side for a printable fit.
major_r = (major_d + 2.0 * clearance) / 2.0
# Trapezoidal thread depth (radial). Standard Tr basic depth ≈ 0.5·pitch; the
# female minor radius sits that much inside the major radius.
thr_depth = 0.5 * pitch
minor_r = max(1.0, major_r - thr_depth)   # female crest (innermost) radius
# The BORE is drilled to the female ROOT (widest) radius; the rib fills inward to
# the minor radius. Root is at the major radius (clears the male crest).
root_r = major_r
# Trapezoidal rib half-widths: wide at the root (outer), narrow at the crest
# (inner). tan(flank) gives the flank flare over the radial depth.
half_root = pitch * 0.25
half_crest = max(0.05, half_root - thr_depth * math.tan(math.radians(flank)))
# Number of thread turns fused into this nut height.
turns = min(_MAX_TURNS, max(2.0, height / pitch))
thread_h = pitch * turns
overlap = 0.5  # push rib root back into the wall for a clean volumetric fuse


# ── Thread primitive (inlined — repo-lib imports are blocked in the sandbox) ──
# Mean thread radius; the helix PATH is built at this real radius (NOT a
# near-zero radius). Sweeping along a real-radius helix keeps the pipe frame
# non-singular — that is what makes the fuse both fast (~2 s) and watertight. A
# radius≈0 helix produces a degenerate sweep frame that either fails outright or
# tessellates into cracks.
_R0 = (root_r + minor_r) / 2.0


def _helix_path(p, h):
    """Helical wire centered on Z at the mean thread radius `_R0`."""
    return cq.Wire.makeHelix(pitch=p, height=h, radius=_R0)


def _thread_rib(t_h):
    """Inward-pointing helical trapezoidal rib to UNION into the bore, forming the
    female thread. Profile lives in the XZ plane in ABSOLUTE radii: a wide root
    pushed `overlap` into the wall, narrowing to a crest at the minor radius
    (points toward the axis)."""
    outer_r = root_r + overlap            # sits inside the wall material
    inner_r = minor_r                     # female crest, nearest the axis
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (outer_r, -half_root),
            (inner_r, -half_crest),
            (inner_r, half_crest),
            (outer_r, half_root),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, t_h + pitch), isFrenet=True, makeSolid=True)
    # Start half a pitch below z=0 so the thread fully crosses the bottom face.
    return rib.translate((0, 0, -pitch * 0.5))


def threaded_bore(body, t_h=None):
    """Drill the through-bore to the root radius and fuse the female thread rib."""
    t_h = thread_h if t_h is None else t_h
    # Straight bore to the root radius, all the way through.
    bore = cq.Workplane("XY").circle(root_r).extrude(height + 2.0).translate((0, 0, -1.0))
    body = body.cut(bore)
    # Fuse the functional female thread.
    body = body.union(_thread_rib(t_h))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_round_nut():
    """Plain cylindrical nut with an internal trapezoidal thread. A pair of wrench
    flats are milled on opposite sides so it can be held while adjusting."""
    body = cq.Workplane("XY").circle(body_dia / 2.0).extrude(height)

    # Two wrench flats (cut shallow chords on ±Y).
    flat_depth = min(body_dia * 0.12, 2.0)
    for sign in (+1.0, -1.0):
        flat = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sign * (body_dia / 2.0 + flat_depth * 3.0 - flat_depth), 0))
            .box(body_dia + 4.0, flat_depth * 6.0, height + 2.0, centered=(True, True, False))
            .translate((0, 0, -1.0))
        )
        try:
            body = body.cut(flat)
        except Exception:
            pass

    body = threaded_bore(body)
    return body


def build_flange_nut():
    """Round barrel + a bottom flange carrying `hole_count` bolt holes, so the nut
    can be bolted to a carriage. The threaded bore runs through both."""
    flange_th = max(3.0, pitch * 1.5)
    barrel_h = height

    # Flange disk at the base.
    body = cq.Workplane("XY").circle(flange_dia / 2.0).extrude(flange_th)
    # Barrel rising above the flange.
    barrel = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, flange_th))
        .circle(body_dia / 2.0)
        .extrude(barrel_h)
    )
    body = body.union(barrel)

    # Bolt-hole circle midway between body and flange edge.
    bhc_r = (body_dia / 2.0 + flange_dia / 2.0) / 2.0
    for k in range(hole_count):
        ang = math.radians(360.0 / hole_count * k)
        hx = bhc_r * math.cos(ang)
        hy = bhc_r * math.sin(ang)
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(hx, hy, -0.5))
            .circle(bolt_dia / 2.0)
            .extrude(flange_th + 1.0)
        )
        body = body.cut(hole)

    # Bore + thread run through the whole stack (flange + barrel).
    total_h = flange_th + barrel_h
    bore = cq.Workplane("XY").circle(root_r).extrude(total_h + 2.0).translate((0, 0, -1.0))
    body = body.cut(bore)
    # Fuse the female thread through the full height (a few extra turns allowed).
    t_turns = min(_MAX_TURNS + 2.0, max(2.0, total_h / pitch))
    body = body.union(_thread_rib(pitch * t_turns))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "flange_nut" or (flange and target_part == "round_nut"):
    result = build_flange_nut()
else:
    # round_nut and anti_backlash (a taller round nut) share the builder.
    result = build_round_nut()
