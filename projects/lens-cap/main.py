"""
Lens / Filter Cap & Step Ring — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Front lens caps, rear body caps and step-up/step-down rings for the universal
photographic filter-thread system. Filter threads run in a handful of nominal
diameters (49/52/58/67/72/77/82 mm) at a fine 0.75 mm pitch; every lens front
and screw-in filter shares them. This cartridge builds a pinch/press snap cap
sized to a filter OD, a step ring that threads one filter size to another, and a
rear body cap blank.

Filter thread standard (nominal, dimensionally real):
  - major diameter = the nominal size (49, 52, 58, 67, 72, 77, 82 mm)
  - pitch          ≈ 0.75 mm (the common fine filter-thread pitch)
  - male crest sits at the major diameter; female bore = major + fit clearance.

Thread strategy — COSMETIC by default (these are fit threads, not structural):
  A serrated (sawtooth) radial profile is revolved 360°, so male crests trace
  the nominal major diameter and the female bore relief traces a matching
  minor. One `revolve` per thread (no per-turn booleans) is fast and inherently
  watertight — the right idiom for a light, quick-screwing filter thread.

Watertight strategy:
  Threads are single solids of revolution. The step-ring bore is a THROUGH-hole
  (open both ends → vents to outside). The snap cap's grip relief is a shallow
  internal groove that opens to the cap mouth. No tangent unions, no post-cut
  fillets on complex features.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `filter_thread`).
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


# ── Filter thread table (nominal major dia in mm; fine pitch) ────────────────
FILTER = {
    "49": {"major": 49.0, "pitch": 0.75},
    "52": {"major": 52.0, "pitch": 0.75},
    "58": {"major": 58.0, "pitch": 0.75},
    "67": {"major": 67.0, "pitch": 0.75},
    "72": {"major": 72.0, "pitch": 0.75},
    "77": {"major": 77.0, "pitch": 0.75},
    "82": {"major": 82.0, "pitch": 0.75},
}


def filt(name, fallback="58"):
    """Look up a filter-thread spec, defaulting to 58 mm."""
    return FILTER.get(str(name), FILTER[fallback])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "snap_cap"))
# "snap_cap" | "step_ring" | "body_cap"
filter_thread = str(PARAM(lambda: filter_thread, "58"))  # nominal filter size

thread_a = str(PARAM(lambda: thread_a, "58"))  # step ring: FEMALE (bottom) size
thread_b = str(PARAM(lambda: thread_b, "52"))  # step ring: MALE (top) size

clearance = float(PARAM(lambda: clearance, 0.3))   # printed-thread fit slop (per side)
wall = float(PARAM(lambda: wall, 2.4))             # side wall thickness (mm)
cap_depth = float(PARAM(lambda: cap_depth, 7.0))   # snap-cap skirt depth (mm)
top_th = float(PARAM(lambda: top_th, 2.2))         # cap top / ring web thickness (mm)
grip_teeth = int(PARAM(lambda: grip_teeth, 0))     # optional grip flutes on the cap rim (0=off)
thread_turns = float(PARAM(lambda: thread_turns, 4.0))  # step-ring thread engagement turns
body_cap_d = float(PARAM(lambda: body_cap_d, 42.0))  # rear body-cap bayonet OD (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
clearance = max(0.1, min(clearance, 0.8))
wall = max(1.6, min(wall, 5.0))
cap_depth = max(3.0, min(cap_depth, 20.0))
top_th = max(1.2, min(top_th, 6.0))
grip_teeth = max(0, min(grip_teeth, 80))
thread_turns = max(2.0, min(thread_turns, 8.0))
body_cap_d = max(20.0, min(body_cap_d, 80.0))


# ── Cosmetic thread solids of revolution ─────────────────────────────────────
def cosmetic_male_ring(major, pitch, length, z0, turns):
    """Male filter thread as a single solid of revolution: a serrated radial
    profile revolved 360°, crest at major/2, root at (major-2*depth)/2. Base at
    z=z0, grows +Z. Watertight by construction (one revolve)."""
    depth = 0.55 * pitch
    r_maj = major / 2.0
    r_min = r_maj - depth
    n = max(1, int(round(min(turns, length / pitch))))
    tooth = length / n
    pts = [(0.0, 0.0), (r_min, 0.0)]
    for i in range(n):
        z_lo = i * tooth
        pts.append((r_maj, z_lo + tooth * 0.5))
        pts.append((r_min, z_lo + tooth))
    pts.append((0.0, length))
    section = cq.Workplane("XZ").polyline(pts).close()
    solid = section.revolve(360, (0, 0, 0), (0, 1, 0))
    return solid.translate((0, 0, z0))


def female_bore_cutter(major, pitch, length, z0, turns, clear):
    """A cutter matching a female filter thread: a serrated solid of revolution
    sized so that subtracting it from a tube leaves internal threads whose crests
    sit near the male minor diameter. Bore major = male major + 2*clear."""
    bore_major = major + 2.0 * clear
    depth = 0.55 * pitch
    r_maj = bore_major / 2.0            # relief (root of internal thread) outer
    r_min = r_maj - depth               # crest of internal thread (grabs male)
    n = max(1, int(round(min(turns, length / pitch))))
    tooth = length / n
    # Cutter outline: from axis out to r_maj, serrate inward to r_min per tooth.
    pts = [(0.0, 0.0), (r_maj, 0.0)]
    for i in range(n):
        z_lo = i * tooth
        pts.append((r_min, z_lo + tooth * 0.5))
        pts.append((r_maj, z_lo + tooth))
    pts.append((0.0, length))
    section = cq.Workplane("XZ").polyline(pts).close()
    solid = section.revolve(360, (0, 0, 0), (0, 1, 0))
    return solid.translate((0, 0, z0))


def apply_flutes(solid, outer_d, height, teeth, depth=0.6):
    """Shallow vertical grip flutes around the outside (one polar-array cut)."""
    if teeth <= 0:
        return solid
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
        pass
    return solid


# ── Part builders ────────────────────────────────────────────────────────────
def build_snap_cap():
    """A pinch/press front cap sized to a lens's filter-thread OD. A shallow cup
    (closed top, open skirt) whose inner wall carries a small retaining bead that
    snaps over the filter-thread crest — the classic centre-pinch lens cap style,
    here as a simple press fit. The grip bead is an internal groove open to the
    cap mouth (vents to outside)."""
    g = filt(filter_thread)
    # Cap slips OVER the male filter threads, so its bore = filter major + a
    # press clearance; the retaining bead pinches slightly under the crest.
    bore_r = (g["major"] + 2.0 * clearance) / 2.0
    outer_r = bore_r + wall
    total_h = cap_depth + top_th

    # Solid outer cup.
    body = cq.Workplane("XY").circle(outer_r).extrude(total_h)
    # Hollow the skirt from the bottom up to the top web.
    bore = (
        cq.Workplane("XY")
        .circle(bore_r)
        .extrude(cap_depth)
    )
    body = body.cut(bore)

    # Retaining bead: a shallow inward ring near the mouth that snaps under the
    # outermost filter-thread crest. Modelled as a thin torus-like ridge via a
    # revolved triangle pushed inward — kept as a single revolve, unioned with a
    # small overlap into the wall so it stays watertight.
    bead_z = cap_depth * 0.4
    bead_proj = min(0.6, clearance + 0.3)
    ridge_pts = [
        (bore_r + 0.05, bead_z - 0.9),
        (bore_r - bead_proj, bead_z),
        (bore_r + 0.05, bead_z + 0.9),
    ]
    ridge = (
        cq.Workplane("XZ")
        .polyline(ridge_pts)
        .close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
    )
    try:
        body = body.union(ridge)
    except Exception:
        pass

    body = apply_flutes(body, 2.0 * outer_r, total_h, grip_teeth)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_step_ring():
    """A step-up / step-down ring: FEMALE filter thread on the bottom (`thread_a`,
    screws onto a lens) and MALE filter thread on top (`thread_b`, accepts a
    filter of size B). A short web joins them; a clear through-bore lets light
    pass. Uses cosmetic threads for a fast, light-duty screw."""
    ga = filt(thread_a)
    gb = filt(thread_b)

    pa, pb = ga["pitch"], gb["pitch"]
    thr_a_h = pa * thread_turns
    thr_b_h = pb * thread_turns

    # Female section outer diameter: bore major (A) + 2 walls; make the ring
    # body big enough to host the female threads and support the male stub.
    a_bore_major = ga["major"] + 2.0 * clearance
    female_od = a_bore_major + 2.0 * wall
    b_major = gb["major"]
    # Male stub root tube must be wide enough to carry the B threads; its outer
    # (crest) diameter is b_major.
    male_root_od = b_major - 2.0 * (0.55 * pb) - 0.2

    female_h = thr_a_h + 1.0
    web_h = max(top_th, 1.6)
    male_h = thr_b_h + 1.0
    total_h = female_h + web_h + male_h

    # --- Female tube (bottom): a tube whose bore carries internal A threads. ---
    female_body = (
        cq.Workplane("XY")
        .circle(female_od / 2.0)
        .extrude(female_h + web_h)
    )
    # Cut the female bore relief + threads from the bottom up (open at bottom →
    # vents to outside). Bore goes up only through the female section, leaving
    # the web.
    fem_cutter = female_bore_cutter(ga["major"], pa, female_h + 0.6, -0.01, thread_turns, clearance)
    female_body = female_body.cut(fem_cutter)

    # --- Male stub (top): a tube at the male root OD with external B threads. ---
    male_tube = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, female_h + web_h - 0.01))
        .circle(male_root_od / 2.0)
        .extrude(male_h + 0.01)
    )
    male_threads = cosmetic_male_ring(b_major, pb, male_h, female_h + web_h, thread_turns)
    male = male_tube.union(male_threads)

    ring = female_body.union(male)

    # Clear central through-bore so light passes (smaller of the two openings,
    # minus a light lip). Through the whole stack → vented.
    light_r = max(3.0, min(ga["major"], gb["major"]) / 2.0 - wall - 1.0)
    channel = (
        cq.Workplane("XY")
        .circle(light_r)
        .extrude(total_h + 2.0)
        .translate((0, 0, -1.0))
    )
    ring = ring.cut(channel)

    try:
        ring = ring.clean()
    except Exception:
        pass
    return ring


def build_body_cap():
    """A rear body-cap blank: a disc with a shallow locating lip and a stiffening
    rib ring — a printable blank to plug a camera body or lens rear. Sized by the
    bayonet OD (`body_cap_d`); the user trims/notches for their specific mount."""
    outer_r = body_cap_d / 2.0
    disc_h = top_th + 1.5

    # Main disc.
    body = cq.Workplane("XY").circle(outer_r).extrude(disc_h)

    # Locating lip: a raised ring near the rim that seats into the bayonet mouth.
    lip_h = 3.0
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, disc_h - 0.01))
        .circle(outer_r - wall)
        .circle(outer_r - wall - 2.0)
        .extrude(lip_h)
    )
    body = body.union(lip)

    # Stiffening rib ring on the flat back to resist warping (raised ring).
    rib = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, disc_h - 0.01))
        .circle(outer_r * 0.45)
        .circle(outer_r * 0.45 - 2.0)
        .extrude(1.4)
    )
    body = body.union(rib)

    body = apply_flutes(body, 2.0 * outer_r, disc_h, grip_teeth)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "step_ring":
    result = build_step_ring()
elif target_part == "body_cap":
    result = build_body_cap()
else:
    result = build_snap_cap()
