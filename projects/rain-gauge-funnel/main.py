"""
Rain Gauge Funnel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A calibrated rain-gauge collector that screws onto an ordinary PET bottle. Citizen
hydrology needs one thing a bottle cannot supply on its own: a KNOWN collection
area. Rainfall is depth (mm), not volume — a bottle catches whatever its own neck
happens to be, which is both tiny and unknown, so the water it collects means
nothing. Give the bottle a funnel of known aperture and the collected volume
converts to depth exactly:

    depth_mm = collected_mL * 1000 / aperture_area_mm2

The funnel therefore reports its own calibration constant. For the default 100 mm
aperture the area is 7853.98 mm2, so 1 mm of rain = 7.854 mL, i.e. 0.1273 mm/mL.
That ratio is printed into the README and is a pure function of `aperture` — the
one number that has to be right for the instrument to be an instrument.

The outlet lands on the published PCO-1881 bottle-neck interface (the ubiquitous
soda/water bottle finish), reusing the same female helical thread the bottle-thread
family established rather than inventing a new attachment.

Modes are dispatched via `target_part`:
  * "funnel"      — the calibrated collector: a knife-edged aperture, a conical
                    throat, and a female PCO-1881 thread that screws onto a bottle.
  * "splash_ring" — a drop-in insert that sits in the throat and stops splash-out
                    in heavy rain (the classic source of under-reading).
  * "mount_clip"  — a post/rail clip that holds the bottle upright and level, since
                    a gauge that is not level does not measure what it claims.

Standards encoded (mm):
  PCO-1881 bottle finish: thread major Ø 27.4, pitch 2.7, ~1 turn (matches the
  published bottle-thread NECK_STANDARDS entry exactly).
  Aperture: 50-200 mm Ø. WMO guidance for manual gauges favours a sharp-rimmed
  aperture of at least 100 mm diameter set 300-500 mm above ground; the knife edge
  matters because a thick blunt rim collects its own share of drops and over-reads.

Watertightness strategy (a funnel as a closed manifold):
  The funnel is built as ONE revolved profile — outer wall up, knife rim, inner
  cone down to the throat — so the wall has real thickness everywhere and there is
  no shell/offset operation to fail. The profile never touches the rotation axis at
  a single point (which would revolve into a pole singularity and split the mesh
  into two shells); the throat bore carries it across the axis as a finite opening.
  The thread rib's ROOT is pushed INTO the surrounding wall by `overlap`, so its
  union with the bore is a volumetric boolean rather than a tangent kiss. Fillets
  are wrapped in try/except so a crashed blend degrades to a sharp edge.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Bottle-neck finish standards (shared with the published bottle-thread) ────
NECK_STANDARDS = {
    "PCO-1881": {"major_d": 27.4, "pitch": 2.7, "turns": 1.0},
    "PCO-1810": {"major_d": 27.4, "pitch": 2.7, "turns": 1.5},
    "28-410":   {"major_d": 28.0, "pitch": 3.18, "turns": 1.5},
    "38-400":   {"major_d": 38.0, "pitch": 4.2, "turns": 1.25},
}


def neck_geo(name):
    """Look up nominal neck geometry, defaulting to PCO-1881."""
    return NECK_STANDARDS.get(name, NECK_STANDARDS["PCO-1881"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "funnel"))
neck_standard = str(PARAM(lambda: neck_standard, "PCO-1881"))
aperture = float(PARAM(lambda: aperture, 100.0))       # collector aperture Ø (mm) — THE calibration
cone_angle = float(PARAM(lambda: cone_angle, 55.0))    # cone half-angle from horizontal (deg)
throat_dia = float(PARAM(lambda: throat_dia, 12.0))    # throat bore Ø (mm)
wall = float(PARAM(lambda: wall, 2.4))                 # funnel wall (mm)
rim_t = float(PARAM(lambda: rim_t, 0.8))               # knife-rim tip thickness (mm)
clearance = float(PARAM(lambda: clearance, 0.4))       # printed-thread fit slop (mm)
skirt_len = float(PARAM(lambda: skirt_len, 16.0))      # threaded skirt length (mm)
post_dia = float(PARAM(lambda: post_dia, 25.0))        # mount post Ø (mm)
bottle_dia = float(PARAM(lambda: bottle_dia, 65.0))    # bottle body Ø at the clip (mm)

# Clamp so extreme UI values still build watertight.
aperture = max(50.0, min(aperture, 200.0))
cone_angle = max(25.0, min(cone_angle, 75.0))
throat_dia = max(5.0, min(throat_dia, 30.0))
wall = max(1.6, min(wall, 6.0))
rim_t = max(0.4, min(rim_t, 3.0))
clearance = max(0.0, min(clearance, 1.0))
skirt_len = max(8.0, min(skirt_len, 40.0))
post_dia = max(10.0, min(post_dia, 80.0))
bottle_dia = max(40.0, min(bottle_dia, 120.0))


# ── Calibration ──────────────────────────────────────────────────────────────
def aperture_area_mm2():
    """Collection area (mm2). This is the number the instrument depends on."""
    return math.pi * (aperture / 2.0) ** 2


def ml_per_mm_rain():
    """Millilitres collected per millimetre of rainfall."""
    return aperture_area_mm2() / 1000.0


# ── Thread primitives (inlined — repo lib imports are blocked in the sandbox) ─
def _helix_path(pitch, height):
    """A helical wire centered on Z. Radius ~0 so the swept profile (already at the
    target radius in its own plane) traces the true helix."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib, ridges pointing INWARD to grab a bottle's male
    thread. Root radius = bore_r + overlap so the rib bites into the wall material —
    a clean volumetric union instead of a fragile tangent kiss."""
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


# ── Part builders ─────────────────────────────────────────────────────────────
def build_funnel():
    """The calibrated collector: knife-edged aperture, conical throat, and a female
    bottle thread. Built as ONE revolved profile so the wall is real everywhere."""
    g = neck_geo(neck_standard)
    pitch = g["pitch"]
    # Bore that accepts the bottle's male thread, plus printed-fit slop.
    bore_r = g["major_d"] / 2.0 + clearance
    skirt_out_r = bore_r + wall

    ap_r = aperture / 2.0
    th_r = max(2.5, min(throat_dia / 2.0, ap_r - wall - 2.0))
    # Ensure the skirt is never wider than the aperture (which would make the
    # profile self-intersect and revolve into garbage).
    ap_r = max(ap_r, skirt_out_r + 3.0)

    # Cone height from the half-angle: the drop from rim to throat.
    cone_h = max(6.0, (ap_r - th_r) * math.tan(math.radians(cone_angle)))
    z_throat = 0.0                      # top of the threaded skirt
    z_rim = z_throat + cone_h           # the aperture rim

    # Revolved profile, walked as a closed loop in (radius, z):
    #   inner cone from throat up to rim, knife tip, outer cone back down,
    #   then down the outside of the skirt, across the bottom, and up the bore.
    rim_half = rim_t / 2.0
    prof = (
        cq.Workplane("XZ")
        .moveTo(th_r, z_throat)                     # throat lip, inner side
        .lineTo(ap_r - rim_half, z_rim)             # up the inner cone to the rim
        .lineTo(ap_r + rim_half, z_rim)             # across the knife tip
        .lineTo(th_r + wall * 1.6, z_throat)        # back down the outer cone
        .lineTo(skirt_out_r, z_throat)              # out to the skirt wall
        .lineTo(skirt_out_r, z_throat - skirt_len)  # down the outside of the skirt
        .lineTo(bore_r, z_throat - skirt_len)       # across the skirt's bottom rim
        .lineTo(bore_r, z_throat)                   # up the bore
        .lineTo(th_r, z_throat)                     # close along the throat shoulder
        .close()
    )
    body = prof.revolve(360, (0, 0, 0), (0, 1, 0))

    # Female bottle thread inside the skirt bore.
    thr_depth = min(pitch * 0.32, wall * 0.6)
    overlap = min(0.6, wall * 0.35)
    thread_h = min(skirt_len - pitch * 0.6, pitch * (g["turns"] + 0.5))
    if thread_h > pitch * 0.5:
        rib = female_thread(bore_r, pitch, thread_h, thr_depth, overlap)
        rib = rib.translate((0, 0, z_throat - skirt_len + pitch * 0.4))
        try:
            body = body.union(rib)
        except Exception:
            pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_splash_ring():
    """A drop-in insert for the throat: a short tube with an inward lip that breaks
    the jet and stops splash-out in heavy rain (a classic cause of under-reading)."""
    th_r = max(2.5, throat_dia / 2.0)
    out_r = th_r + wall
    height = max(8.0, th_r * 2.4)
    lip_depth = min(th_r * 0.45, wall * 1.5)
    lip_h = max(1.2, wall * 0.8)

    body = cq.Workplane("XY").circle(out_r).extrude(height)
    # Main bore, open both faces.
    bore = (
        cq.Workplane("XY").workplane(offset=-1.0)
        .circle(th_r).extrude(height + 2.0)
    )
    body = body.cut(bore)

    # Inward lip near the top: a ring of material added back, overlapping the wall
    # volumetrically so the union is never a tangent kiss.
    lip_r = max(1.2, th_r - lip_depth)
    lip = (
        cq.Workplane("XY")
        .workplane(offset=height - lip_h)
        .circle(out_r).circle(lip_r)
        .extrude(lip_h)
    )
    body = body.union(lip)

    # Cosmetic edge break. The radius is tied to the SMALLEST local feature (the lip
    # land and the ring wall), not a flat constant: on a minimum-throat ring a fixed
    # 0.8 mm blend consumes the whole lip land and OCC returns a self-degenerate face
    # — which does NOT raise, it just quietly comes back non-watertight. Anything
    # under a tenth of a millimetre is not worth the risk, so it is skipped instead.
    lip_land = max(0.0, th_r - lip_r)
    fr = min(0.8, wall * 0.3, lip_land * 0.35, lip_h * 0.35)
    if fr >= 0.1:
        try:
            body = body.edges("%CIRCLE").fillet(fr)
        except Exception:
            pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_mount_clip():
    """A post clip that holds the bottle upright and level. A gauge that is not level
    does not measure what it claims, so the cradle and the post jaw are one part.

    The blank is derived FROM the two bores rather than guessed independently: the
    post jaw sits entirely left of the web and the cradle entirely right of it, and
    the slab is then sized to enclose both with a full `wall` of material all round.
    Sizing the blank from a separate 'span' formula is what let a max-diameter post
    bore run off the end of the slab and shatter the part into loose arcs."""
    post_r = post_dia / 2.0
    bot_r = bottle_dia / 2.0
    depth = max(20.0, min(bot_r, 45.0))     # clip length along the bottle axis
    web = max(3.0, wall * 1.5)

    # Bore centres, measured out from the shared web at x = 0.
    x_post = -(web / 2.0 + post_r + wall)
    x_bot = +(web / 2.0 + bot_r + wall)

    # Slab bounds: every bore plus a full wall, so no bore can reach an edge.
    x_min = x_post - post_r - wall
    x_max = x_bot + bot_r + wall
    half_y = max(post_r, bot_r) + wall
    cx = (x_min + x_max) / 2.0
    slab_w = x_max - x_min

    body = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0.0, 0.0))
        .box(slab_w, 2.0 * half_y, depth, centered=(True, True, False))
    )
    try:
        body = body.edges("|Z").fillet(min(4.0, wall * 2.0))
    except Exception:
        pass

    reach = slab_w + 4.0 * max(post_r, bot_r) + 20.0

    # Post bore, opened to the -X face by a mouth slot (never a sealed void). The
    # mouth is capped below the jaw's own opening so the two legs always survive.
    post_bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x_post, 0.0, -1.0))
        .circle(post_r).extrude(depth + 2.0)
    )
    body = body.cut(post_bore)
    mouth_w = max(1.5, min(post_r * 1.1, 2.0 * post_r - 0.8))
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x_post - reach / 2.0, 0.0, -1.0))
        .box(reach, mouth_w, depth + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # Bottle cradle, opened to the +X face the same way.
    bot_bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x_bot, 0.0, -1.0))
        .circle(bot_r).extrude(depth + 2.0)
    )
    body = body.cut(bot_bore)
    mouth_b = max(1.5, min(bot_r * 1.05, 2.0 * bot_r - 0.8))
    slot_b = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x_bot + reach / 2.0, 0.0, -1.0))
        .box(reach, mouth_b, depth + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot_b)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "funnel": build_funnel,
    "splash_ring": build_splash_ring,
    "mount_clip": build_mount_clip,
}

result = _dispatch.get(target_part, build_funnel)()
