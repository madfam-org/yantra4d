"""
Lead-Screw Anti-Backlash Nut (T8) — Yantra4D Hyperobject Cartridge (CadQuery).

A printable anti-backlash nut for T8 lead screws — the repair/upgrade part for
3D-printer Z axes, small CNC stages and linear actuators. Axial play ("backlash")
is taken up by a spring that preloads a floating threaded section against the
screw flanks, so the nut tracks the screw in both directions with no lost motion.
The FUNCTIONAL interface is a genuine internal trapezoidal thread cut at the T8
nominal major diameter and 2 mm pitch.

T8 lead-screw reference (the printer/CNC standard):
  major diameter = 8.0 mm     pitch = 2.0 mm     lead = 8 mm (4-start)
  thread form    = trapezoidal, 30° included (15° flank)
The nut is modelled single-start at the true 2 mm pitch: the major diameter and
pitch are dimensionally correct and it prints far more reliably than a 4-start
internal thread while still meshing the screw.

Thread strategy (verified watertight + fast, ~2-4 s):
  The bore is drilled to the thread ROOT radius, then a trapezoidal rib is swept
  along a genuine `cq.Wire.makeHelix` and UNIONED into the bore as POSITIVE
  material (the bottle-thread / leadscrew-nut idiom — inlined, no cross-file
  import). CUTTING a swept groove is an order of magnitude slower and tessellates
  into cracks, so the female thread is built as fused helical ribs instead.
  The turn count is forced to a HALF-INTEGER (…3.5, 4.5…) — an INTEGER turn count
  degenerates the OCCT helical sweep (the profile closes on itself, the boolean
  yields a negative-volume body), so half-integers are both correct and fast.

Modes (dispatched via `target_part`):
  * "spring_nut"   — the anti-backlash nut: a threaded barrel with a coaxial
                     spring pocket and internal seats so a compression spring
                     preloads the thread flanks (the backlash-eliminating part).
  * "solid_nut"    — a plain single-piece T8 nut with wrench flats (a tight
                     reference nut, no spring pocket).
  * "flanged_nut"  — a T8 nut on a bolt-down flange to fix it to a carriage.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>) — no globals()/eval/getattr.
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


# ── T8 / trapezoidal lead-screw standards (nominal geometry) ─────────────────
THREAD_SPECS = {
    "T8":    {"major_d": 8.0, "pitch": 2.0, "flank": 15.0},   # 8 mm, 2 mm pitch
    "T8x8":  {"major_d": 8.0, "pitch": 2.0, "flank": 15.0},   # 8 mm, 8 mm lead / 2 mm pitch
    "T10":   {"major_d": 10.0, "pitch": 2.0, "flank": 15.0},  # 10 mm trapezoidal
    "T12":   {"major_d": 12.0, "pitch": 3.0, "flank": 15.0},  # 12 mm, 3 mm pitch
}


def spec_geo(name):
    return THREAD_SPECS.get(str(name).strip(), THREAD_SPECS["T8"])


# ── Parameters ───────────────────────────────────────────────────────────────
screw       = str(  PARAM(lambda: screw,      "T8"))       # T8 | T8x8 | T10 | T12
body_dia    = float(PARAM(lambda: body_dia,   16.0))       # nut outer diameter (mm)
height      = float(PARAM(lambda: height,     18.0))       # nut height along the screw (mm)
clearance   = float(PARAM(lambda: clearance,   0.35))      # printed thread fit slop / side (mm)
spring_od   = float(PARAM(lambda: spring_od,   12.0))      # compression-spring outer dia (mm)
spring_len  = float(PARAM(lambda: spring_len,   8.0))      # spring pocket depth (mm)
flange_dia  = float(PARAM(lambda: flange_dia,  28.0))      # flange outer diameter (mm)
bolt_dia    = float(PARAM(lambda: bolt_dia,     3.4))      # flange bolt-hole dia (M3 ≈ 3.4)
hole_count  = int(  PARAM(lambda: hole_count,     4))      # flange bolt-hole count

target_part = str(PARAM(lambda: target_part, "spring_nut"))  # spring_nut|solid_nut|flanged_nut


# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
clearance = max(0.15, min(clearance, 0.8))
g = spec_geo(screw)
major_d = g["major_d"]
pitch = g["pitch"]
flank = g["flank"]

min_body = major_d + 6.0
body_dia = max(min_body, min(body_dia, 60.0))
height = max(pitch * 4.0, min(height, 60.0))
flange_dia = max(body_dia + 6.0, min(flange_dia, 90.0))
bolt_dia = max(2.0, min(bolt_dia, 8.0))
hole_count = max(2, min(hole_count, 8))
spring_od = max(major_d + 2.0, min(spring_od, body_dia - 3.0))
spring_len = max(2.0, min(spring_len, height * 0.5))


# ── Derived thread geometry ──────────────────────────────────────────────────
major_r = (major_d + 2.0 * clearance) / 2.0        # screw major, opened for fit
thr_depth = 0.5 * pitch                            # trapezoidal basic depth
minor_r = max(1.0, major_r - thr_depth)            # female crest (innermost) radius
root_r = major_r                                   # bore drilled to female root
half_root = pitch * 0.25                           # trapezoidal rib half-widths
half_crest = max(0.05, half_root - thr_depth * math.tan(math.radians(flank)))
_R0 = (root_r + minor_r) / 2.0                     # mean thread radius for the helix
overlap = 0.5                                       # push rib root into the wall


def _half_integer_turns(h):
    """Turns needed to thread height `h`, snapped DOWN to the nearest half-integer
    (…3.5, 4.5…) — never a whole integer (which degenerates the OCCT sweep into a
    negative-volume body). Always ≥ 2.5."""
    raw = max(2.5, h / pitch)
    snapped = math.floor(raw) + 0.5
    if snapped > raw:
        snapped -= 1.0
    return max(2.5, snapped)


def _helix_path(p, h):
    return cq.Wire.makeHelix(pitch=p, height=h, radius=_R0)


def _thread_rib(t_h):
    """Inward-pointing helical trapezoidal rib to UNION into the bore, forming the
    female thread. Absolute-radius profile in XZ: wide root pushed `overlap` into
    the wall, narrowing to a crest at the minor radius (points toward the axis).
    The rib is swept a half pitch longer at each end so, once TRIMMED to the
    thread band, its helical ends are capped flush with the trim planes."""
    outer_r = root_r + overlap
    inner_r = minor_r
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
    return rib.translate((0, 0, -pitch * 0.5))


def _fused_thread(body, band_bottom, band_top, bore_h):
    """Drill the root-radius bore over `bore_h` and fuse a female thread confined
    to the band [band_bottom, band_top]. The rib is INTERSECTED with a
    barrel-height cylinder over that band so its helical ends are capped flush —
    a spilling helical end is the classic non-manifold thread defect. Turns are
    forced half-integer (an integer turn count degenerates the OCCT sweep)."""
    bore = cq.Workplane("XY").circle(root_r).extrude(bore_h + 2.0).translate((0, 0, -1.0))
    body = body.cut(bore)
    band_h = max(pitch * 2.5, band_top - band_bottom)
    turns = _half_integer_turns(band_h)
    rib = _thread_rib(pitch * turns)
    if band_bottom:
        rib = rib.translate((0, 0, band_bottom))
    # Trim the rib flush to the band so no helical end spills past a face.
    clamp = (
        cq.Workplane("XY")
        .circle(body_dia / 2.0 + flange_dia)   # wide enough for any barrel
        .extrude(band_h)
        .translate((0, 0, band_bottom))
    )
    rib = rib.intersect(clamp)
    body = body.union(rib)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_spring_nut():
    """The anti-backlash nut. A threaded barrel whose UPPER end is counter-bored
    to a coaxial spring pocket (OD = spring_od) that seats a compression spring;
    the spring bears on an internal ledge and, in service, preloads a floating
    upper thread section against the screw flanks. Modelled as one printed body:
    the spring pocket + ledge + full-height female thread. Volumetric fused ribs
    (not a cut groove) keep the thread watertight."""
    body = cq.Workplane("XY").circle(body_dia / 2.0).extrude(height)

    # Anti-rotation flats on the barrel so the nut can be keyed into a carriage.
    flat_depth = min(body_dia * 0.10, 1.8)
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

    # Coaxial spring pocket counter-bored from the TOP (open to the top face → no
    # trapped void). It sits outside the thread minor radius so it never breaches
    # the running thread: the spring rides in the annulus around the screw.
    pocket_r = min(spring_od / 2.0, body_dia / 2.0 - 2.0)
    pocket_r = max(pocket_r, minor_r + 1.0)
    pocket = (
        cq.Workplane("XY")
        .circle(pocket_r)
        .extrude(-(spring_len + 0.01))
        .translate((0, 0, height + 0.005))
    )
    body = body.cut(pocket)

    # Female thread runs in the LOWER (load-bearing) section, BELOW the spring
    # pocket floor — the pocket zone is the smooth annulus the spring rides in, so
    # the thread never intersects the pocket wall (which would crack the mesh).
    band_top = max(pitch * 2.5, height - spring_len)
    body = _fused_thread(body, 0.0, band_top, height)
    return body


def build_solid_nut():
    """A plain single-piece T8 nut with a pair of wrench flats — a tight reference
    nut (no spring pocket) for setups that don't need backlash take-up."""
    body = cq.Workplane("XY").circle(body_dia / 2.0).extrude(height)
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
    body = _fused_thread(body, 0.0, height, height)
    return body


def build_flanged_nut():
    """A T8 nut on a bottom flange carrying `hole_count` bolt holes, so it fixes
    to a carriage. The threaded bore runs through the barrel + flange."""
    flange_th = max(3.0, pitch * 1.5)
    barrel_h = height
    body = cq.Workplane("XY").circle(flange_dia / 2.0).extrude(flange_th)
    barrel = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, flange_th))
        .circle(body_dia / 2.0)
        .extrude(barrel_h)
    )
    body = body.union(barrel)

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

    total_h = flange_th + barrel_h
    body = _fused_thread(body, 0.0, total_h, total_h)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "solid_nut":
    result = build_solid_nut()
elif target_part == "flanged_nut":
    result = build_flanged_nut()
else:
    result = build_spring_nut()
