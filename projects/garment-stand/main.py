"""
Garment Stand — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A family of NON-BODY display solids: the honest rigid mounts a Fashion Cabinet
catalog stages its accessories and hardware findings on, when a dress form
would be the wrong (or an absurd) prop. Where `body-form` stages what is worn
ON a body, this cartridge stages what hangs off a body's edges — hats on a head
block, bags on a shoulder yoke, belts on a waist ring — and what is not worn at
all: a finding (zipper, buckle, cord-lock) sitting on a small plinth.

All four mounts share one visual language, seeded by `body-form`'s
`torso_stand`: a plain cylindrical POST rooted into a weighted round BASE with a
built (not cut) chamfer skirt. Three modes are that post/base under a different
top; the fourth — the plinth — is the base's own idea of itself, with no post at
all. Same DNA, one catalog.

Modes (each renders as ONE printable solid):
  - head_block  : a milliner's dome + neck cylinder on the post/base, sized at
                  head_girth — for hats, caps, bucket hats, balaclavas.
  - t_rack      : a bust-less shoulder yoke — a gently curved T-bar with rounded
                  shoulder tips and a slight downward slope — for bags, aprons,
                  harnesses, scarves.
  - waist_ring  : a horizontal ring at waist_girth circumference, carried off the
                  post on a short bridge arm — for belts and waist-hung pieces.
  - mini_plinth : a small stepped pedestal with a chamfered upper step and a
                  shallow top recess (no post) — for staging hardware findings
                  as the objects they are.

Watertight strategy (Yantra4D scar tissue, all respected — and all three traps
below were hit for real while authoring this file, then designed out):
  - The dome is a REVOLVE of a domed profile, never a sphere capped onto a
    cylinder. The profile's crown is TRUNCATED TO A SMALL FLAT and taken
    straight to the axis: a profile whose apex touches the axis at a single
    point revolves into a zero-volume pole shell riding along the solid
    (measured: 2 bodies, one of volume 0.0, is_watertight False). The flat crown
    is the same loft-to-flat discipline `body-form` uses at the neck.
  - The ring is `cq.Solid.makeTorus`. Revolving a small circle about a distant
    axis degenerates in OCCT (`BRep_API: command not done`, or a wedged
    revolve) — the documented Yantra4D workaround is the primitive.
  - Every unioned solid OVERLAPS its neighbour: the post roots INTO the base
    below its top face, the dome's neck sleeves DOWN over the post, the post
    spears through the yoke bar's mid-height, and the bridge arm starts inside
    the post and ends inside the ring's tube. Coplanar touching faces leave
    hairline cracks; real intersection volumes do not.
  - The only cut in the file is the plinth's top recess, and its cutter
    overshoots the top face — a pocket open to air, never a sealed void.
  - No .fillet()/.chamfer() anywhere. Both chamfers (base skirt, plinth step)
    are lofted frusta — chamfer by construction on a clean blank — so OCCT is
    never asked to blend an edge a boolean just produced.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to a top-level `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default. `except Exception`
    catches the NameError the sandbox raises for an unbound param (globals()/
    NameError are not exposed)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (mm) ──────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "head_block"))
# "head_block" | "t_rack" | "waist_ring" | "mini_plinth"

head_girth = float(PARAM(lambda: head_girth, 560.0))          # ISO-8559 head girth
neck_dia = float(PARAM(lambda: neck_dia, 120.0))              # head-block neck Ø
shoulder_width = float(PARAM(lambda: shoulder_width, 430.0))  # yoke point→point
yoke_drop = float(PARAM(lambda: yoke_drop, 25.0))             # shoulder-tip fall
waist_girth = float(PARAM(lambda: waist_girth, 760.0))        # ISO-8559 waist
ring_tube_dia = float(PARAM(lambda: ring_tube_dia, 12.0))     # ring stock Ø

post_dia = float(PARAM(lambda: post_dia, 30.0))               # shared post Ø
post_height = float(PARAM(lambda: post_height, 380.0))        # base top → mount
base_dia = float(PARAM(lambda: base_dia, 220.0))              # weighted base Ø
base_th = float(PARAM(lambda: base_th, 12.0))                 # base thickness

plinth_w = float(PARAM(lambda: plinth_w, 120.0))              # plinth width (X)
plinth_d = float(PARAM(lambda: plinth_d, 80.0))               # plinth depth (Y)
plinth_h = float(PARAM(lambda: plinth_h, 40.0))               # plinth height (Z)

target_material = str(PARAM(lambda: target_material, "polymaker-polylite-pla"))

# ── Clamps (match the manifest slider bounds; keep every solid well-posed) ────
head_girth = max(380.0, min(head_girth, 680.0))
neck_dia = max(60.0, min(neck_dia, 200.0))
shoulder_width = max(240.0, min(shoulder_width, 620.0))
yoke_drop = max(0.0, min(yoke_drop, 90.0))
waist_girth = max(400.0, min(waist_girth, 1400.0))
ring_tube_dia = max(6.0, min(ring_tube_dia, 30.0))
post_dia = max(16.0, min(post_dia, 80.0))
post_height = max(120.0, min(post_height, 900.0))
base_dia = max(120.0, min(base_dia, 520.0))
base_th = max(6.0, min(base_th, 60.0))
plinth_w = max(40.0, min(plinth_w, 300.0))
plinth_d = max(40.0, min(plinth_d, 300.0))
plinth_h = max(15.0, min(plinth_h, 160.0))

# The base must always be wide enough to actually carry the post — otherwise a
# thin base under a fat post reads as a collar, and tips over in the real world.
base_dia = max(base_dia, post_dia * 2.4)

# Datum: z = 0 is the base underside for every post mode (and the plinth's
# underside for the plinth). Everything a mount adds grows upward from there.
Z_BASE_TOP = base_th
Z_MOUNT = Z_BASE_TOP + post_height       # nominal mount height (top of the post)


# ── Shared post + base DNA (seeded by body-form's `torso_stand`) ─────────────
def _base_disc():
    """The weighted round base: a disc whose lower edge is chamfered by a lofted
    frustum. The chamfer is BUILT on a clean blank, never cut-then-blended (the
    OCCT fillet-after-boolean segfault path).

    Deliberately TWO independent solids unioned with a real overlap (the disc
    starts half a skirt down, inside the frustum) rather than one
    `.faces(">Z").wires().toPending()` chain. That chain quietly leaves the
    loft's own top wire pending; drawing a fresh circle on top of it extrudes
    two coincident solids into one invalid compound — which meshes as hundreds
    of shells and reads as `is_watertight False` far downstream. Two clean
    solids and one union cannot do that."""
    r = base_dia / 2.0
    skirt = min(base_th * 0.45, r * 0.10)
    frustum = (
        cq.Workplane("XY")
        .circle(r - skirt)
        .workplane(offset=skirt)
        .circle(r)
        .loft(ruled=True, combine=True)
    )
    disc = (
        cq.Workplane("XY")
        .workplane(offset=skirt * 0.5)          # overlaps the frustum
        .circle(r)
        .extrude(base_th - skirt * 0.5)
    )
    return frustum.union(disc)


def _post(top_z):
    """The shared post: a solid cylinder that ROOTS INTO the base (it starts
    below the base's top face) and rises to `top_z`. A solid post on a solid
    base — one connected body, no trapped cavity, no coplanar seam."""
    root_z = base_th * 0.35                     # deliberately inside the base
    return (
        cq.Workplane("XY")
        .workplane(offset=root_z)
        .circle(post_dia / 2.0)
        .extrude(max(top_z - root_z, 1.0))
    )


def _stand(top_z):
    """Base ∪ post — the DNA every non-plinth mode is built on."""
    return _base_disc().union(_post(top_z))


# ── head_block ───────────────────────────────────────────────────────────────
# Crown flat as a fraction of the head radius. Small enough to read as a dome,
# large enough that the revolve closes on a real circular face instead of a
# single axis point (the pole-singularity trap — measured, not assumed).
CROWN_FLAT = 0.07
DOME_EXP = 2.4          # super-ellipse exponent: flatter crown, fuller side


def _dome_flank(r_head, dome_h):
    """Sampled (x, dz) half-profile of the milliner's dome, crown → equator, as
    a super-ellipse of exponent DOME_EXP:  (x/r)^n + (z/h)^n = 1.

    A hemisphere is the wrong shape for a hat block — too round at the crown,
    too tight at the brow. The super-ellipse gives the flattened crown and full
    side wall a real block has. Points inside the crown flat are dropped; the
    caller closes that flat straight to the axis."""
    steps = 24
    pts = []
    for i in range(steps + 1):
        t = i / float(steps)                    # 0 (crown) → 1 (equator)
        if t < CROWN_FLAT:
            continue
        x = r_head * t
        z = dome_h * max(0.0, 1.0 - t**DOME_EXP) ** (1.0 / DOME_EXP)
        pts.append((x, z))
    return pts


def build_head_block():
    """A milliner's dome + neck on the post/base.

    The whole head is ONE revolve of a closed half-profile walked from the axis:
    neck underside → out to the neck wall → up the neck → out and over the dome
    flank → in across the crown flat → back to the axis. Because the profile is
    closed and meets the axis only along straight radial segments (never at a
    tangent apex), the revolve is watertight by construction, before any union
    happens.

    Revolve convention (established empirically, and easy to get wrong): the
    profile is drawn on the "XZ" workplane and revolved about the GLOBAL Y axis
    — that pairing is the one that lands the solid upright on the Z datum. XZ
    about Z produces a flat zero-volume fan."""
    r_head = head_girth / (2.0 * math.pi)
    dome_h = r_head * 1.18                       # a hat block is taller than round
    r_neck = min(neck_dia / 2.0, r_head * 0.86)
    neck_h = max(r_head * 0.55, 40.0)

    # Sink the neck below the nominal mount so the post ends up embedded in it.
    z_neck_bottom = max(Z_MOUNT - max(30.0, post_dia * 1.2), Z_BASE_TOP + 5.0)
    z_equator = z_neck_bottom + neck_h

    flank = _dome_flank(r_head, dome_h)          # crown-side first
    pts = [(0.0, z_neck_bottom), (r_neck, z_neck_bottom), (r_neck, z_equator)]
    for x, dz in reversed(flank):                # equator → crown flat
        pts.append((x, z_equator + dz))
    pts.append((0.0, z_equator + flank[0][1]))   # across the crown flat, to the axis

    head = (
        cq.Workplane("XZ")
        .polyline(pts)
        .close()
        .revolve(360.0, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    )
    # The post rises INTO the neck (not merely up to it): a quarter of its height.
    return _stand(z_neck_bottom + neck_h * 0.25).union(head)


# ── t_rack ───────────────────────────────────────────────────────────────────
def _yoke_sections(half, bar_w, bar_h):
    """Ordered (x, half_width, half_height, drop) sections from the centre out
    to one shoulder tip. The tip keeps a MINIMUM taper so no wire in the loft
    chain collapses to a point; the fall is quadratic, so the bar leaves the
    post flat and only slopes near the shoulder — how a real shoulder falls."""
    steps = 12
    out = []
    for i in range(steps + 1):
        t = i / float(steps)
        taper = max(0.22, math.sqrt(max(0.0, 1.0 - t**2 * 0.92)))
        out.append((half * t, bar_w * 0.5 * taper, bar_h * 0.5 * taper,
                    yoke_drop * t * t))
    return out


def _half_yoke(sign, sections, z_top):
    """Loft one half of the bar as a SINGLE Workplane chain — each section is an
    ellipse on a YZ plane stepped along X, and the drop is applied by re-centring
    the profile (the plane's local origin travels with the chain, so moving the
    plane would double-count). One chain is what the loft stack needs; add()-ing
    separate Workplanes does not accumulate pending wires."""
    x0, a0, b0, d0 = sections[0]
    wp = cq.Workplane("YZ").workplane(offset=sign * x0)
    wp = wp.center(0.0, z_top - d0).ellipse(a0, b0)
    prev_x, prev_d = x0, d0
    for x, a, b, d in sections[1:]:
        wp = wp.workplane(offset=sign * (x - prev_x))
        wp = wp.center(0.0, -(d - prev_d)).ellipse(a, b)
        prev_x, prev_d = x, d
    return wp.loft(ruled=True, combine=True)


def build_t_rack():
    """A bust-less shoulder yoke: a gently curved T-bar whose tips fall by
    `yoke_drop`, rounded at the shoulders, speared through by the post.

    Built as two mirrored lofts meeting at the centre plane (where they share an
    identical full-size section, so the union is a real overlap, not a kiss).
    No boolean of a bar onto separate end caps, and no fillet after the union."""
    half = shoulder_width / 2.0
    bar_w = max(post_dia * 1.25, 34.0)           # bar thickness front→back (Y)
    bar_h = max(post_dia * 0.95, 26.0)           # bar depth top→bottom (Z)
    z_top = Z_MOUNT

    sections = _yoke_sections(half, bar_w, bar_h)
    bar = _half_yoke(1.0, sections, z_top).union(_half_yoke(-1.0, sections, z_top))

    # The post spears the bar: it ends above the bar's centreline, so post ∩ bar
    # is a real volume rather than a tangent kiss.
    return _stand(z_top + bar_h * 0.15).union(bar)


# ── waist_ring ───────────────────────────────────────────────────────────────
def build_waist_ring():
    """A horizontal ring at `waist_girth` circumference, carried off the post by
    a short bridge arm.

    The ring is `cq.Solid.makeTorus` — a primitive, closed by construction.
    Revolving a small circular profile about a distant axis is the degenerate
    path here (OCCT raised `BRep_API: command not done` on the first attempt),
    which is exactly the swept-arc trap the commons already documents.

    The bridge is a plain box that STARTS at the post axis (so it is fully
    inside the post) and ENDS past the ring's centreline (so it is fully inside
    the tube): post ∪ bridge ∪ ring is one connected solid with two real
    intersection volumes."""
    r_ring = waist_girth / (2.0 * math.pi)
    r_tube = ring_tube_dia / 2.0
    # Keep the ring clear of the post even at a tiny waist on a fat post.
    r_ring = max(r_ring, post_dia * 0.75 + r_tube * 3.0)
    z_ring = Z_MOUNT

    torus = cq.Solid.makeTorus(
        r_ring, r_tube,
        pnt=cq.Vector(0.0, 0.0, z_ring),
        dir=cq.Vector(0.0, 0.0, 1.0),
    )
    ring = cq.Workplane("XY").newObject([torus])

    arm_w = max(ring_tube_dia * 1.6, 14.0)
    arm_h = max(ring_tube_dia * 1.3, 10.0)
    arm_len = r_ring + r_tube * 0.6              # overshoots the ring centreline
    bridge = (
        cq.Workplane("XY")
        .workplane(offset=z_ring - arm_h / 2.0)
        .center(arm_len / 2.0, 0.0)
        .rect(arm_len, arm_w)
        .extrude(arm_h)
    )

    # The post rises past the ring plane so the bridge is fully embedded in it.
    return _stand(z_ring + arm_h).union(bridge).union(ring)


# ── mini_plinth ──────────────────────────────────────────────────────────────
def build_mini_plinth():
    """A small stepped display plinth for hardware findings — no post.

    Two steps: a wide flat foot, and a chamfered upper block built as a loft
    (chamfer by construction on a clean blank). One shallow rectangular recess
    is then cut into the top face; the cutter overshoots that face upward, so
    the pocket is open to air and can never become a sealed internal void. The
    cut is the LAST operation and nothing is blended after it."""
    foot_h = max(plinth_h * 0.28, 4.0)
    body_h = max(plinth_h - foot_h, 6.0)
    cham = min(plinth_w, plinth_d) * 0.10

    foot = cq.Workplane("XY").rect(plinth_w, plinth_d).extrude(foot_h)

    # Upper block: a chamfer-in frustum starting INSIDE the foot, then a straight
    # shaft unioned onto it with a real overlap (same discipline as the base —
    # two clean solids, never a re-pended loft wire).
    z_block_start = foot_h * 0.5
    top_w = plinth_w - cham * 3.2
    top_d = plinth_d - cham * 3.2
    frustum = (
        cq.Workplane("XY")
        .workplane(offset=z_block_start)
        .rect(plinth_w - cham * 2.0, plinth_d - cham * 2.0)
        .workplane(offset=cham)
        .rect(top_w, top_d)
        .loft(ruled=True, combine=True)
    )
    shaft = (
        cq.Workplane("XY")
        .workplane(offset=z_block_start + cham * 0.5)   # overlaps the frustum
        .rect(top_w, top_d)
        .extrude(body_h + cham * 0.5)
    )
    blank = foot.union(frustum).union(shaft)

    # Shallow top recess — the staging tray the finding sits in.
    rec_w = plinth_w - cham * 5.0
    rec_d = plinth_d - cham * 5.0
    rec_depth = min(plinth_h * 0.18, body_h * 0.5)
    if rec_w > 6.0 and rec_d > 6.0 and rec_depth > 1.0:
        z_top = z_block_start + cham + body_h
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=z_top - rec_depth)
            .rect(rec_w, rec_d)
            .extrude(rec_depth + 5.0)              # overshoots the top face
        )
        blank = blank.cut(cutter)
    return blank


def build():
    builders = {
        "head_block": build_head_block,
        "t_rack": build_t_rack,
        "waist_ring": build_waist_ring,
        "mini_plinth": build_mini_plinth,
    }
    fn = builders.get(target_part, build_head_block)
    return fn()


result = build()
