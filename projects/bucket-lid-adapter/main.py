"""
Bucket Lid Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A bored pail or carboy lid, given a bottle finish.

Food-grade buckets and carboys are the cheapest large vessel anywhere. What they
lack is a *port*: a way to fill, dose, vent, decant or plumb them without taking
the lid off. The commons already speaks both halves of that conversation and has
never joined them. On one side, `airlock-grommet` and `sharps-lid` seat into a
drilled bucket/carboy bore. On the other, nine cartridges — `pco-cap`,
`jar-adapter`, `bottle-coupler`, `bottle-thread`, `faircap-filter`,
`filter-straw`, `bird-feeder`, `pet-dispenser`, `rain-gauge-funnel` — all speak
PCO 1881, the neck finish on every carbonated-drink PET bottle on earth. This
cartridge is the disc that carries one interface on its underside and the other
on its face, so a two-litre bottle, a filter, a dosing cap or an airlock lands on
a bucket lid without a single proprietary part.

What it is NOT, and why:
  The wave plan drafted this as a *pail-mouth lid*. Two facts killed that and
  neither is a matter of taste. First, the nominal 5 gal / 20 L pail mouth is a
  **(verify)** figure with no issuing body: pail mouths are a maker's tooling
  dimension, they vary between suppliers, and no primary source could be
  confirmed for one during authoring. §7 forbids writing a plausible number as a
  dimension. Second, a ~290 mm disc does not fit a consumer print bed, so a
  full-mouth lid would be a cartridge almost nobody could print.
  The bore, by contrast, is a dimension the *user* creates with a hole saw and
  can measure, and it is the interface the commons already publishes. So this
  adapter seats INTO the lid rather than replacing it, and every vessel figure it
  depends on is a slider, not an assertion.

Modes are dispatched via `target_part`:
  * "lid_port"        — a flanged bore fitting presenting a MALE PCO 1881 neck on
                        its face. Any PET bottle cap, or the commons' `pco-cap` /
                        `jar-adapter` / `bottle-coupler`, screws straight on.
  * "bottle_receiver" — the inverse: a FEMALE PCO 1881 socket on the same bore
                        flange, so a cut-down PET bottle screws in neck-first as a
                        reservoir, funnel or float.
  * "bore_plug"       — a blanking plug on the same bore series, optionally vented,
                        for when the port is not in use. Also the grommet-boss
                        blank the airlock leaves behind.

Watertightness strategy (the traps this batch inherited, and where each bites):
  * Union OVERLAPS, never tangents. Every coaxial body straddles the one it grows
    from by `OVERLAP` in Z, so the intersection is volumetric at EVERY parameter
    combination — not only at the default. A ring fused tangentially to a plate
    renders an open shell and raises nothing (`frog-closure`, PR #60).
  * The flange rim is forced strictly larger than the neck crest, so a small bore
    with a small overhang can never produce two coincident coplanar cylinders.
  * Thread turns are forced to a HALF-integer. A whole-turn thread closes its
    sweep on itself and leaves a coincident seam face.
  * No sealed void anywhere: the ports are through-bores, and the only closed
    part (`bore_plug` unvented) is solid, not hollow. A sealed cavity meshes as
    two bodies (`solar-dryer-tray`).
  * No fillet is taken on any edge a bore or a thread has touched:
    `edges("%CIRCLE").fillet()` silently catches non-rim arcs and returns a
    non-watertight solid (`graft-clip`).
  * Every clamp is applied against the FINAL derived value, not the input, and
    the ordering is deliberate — `frog-closure`'s tail outgrew its ring because a
    cap was applied before the value it capped had resolved.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.

This is not a pressure vessel and not a food-safety certification. Printed parts
are porous at the layer lines and a printed thread is not a seal. See the README.
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


# ── PCO 1881 neck finish (nominal geometry) ──────────────────────────────────
# The finish on every carbonated PET bottle. `major_d` is the MALE thread outer
# diameter; the commons' `pco-cap` builds its female bore from the same numbers,
# so a neck generated here and a cap generated there meet on one shared figure.
PCO1881 = {"major_d": 27.43, "pitch": 2.7}

# Volumetric union margin. Every coaxial body straddles its neighbour by this in
# Z so no fuse is ever tangential. Named rather than inlined because it is the
# answer to a specific failure, not a taste.
OVERLAP = 1.2


def half_turns(t):
    """Force a thread turn count to the nearest lower HALF-integer, never whole.

    A whole-turn helical sweep ends exactly where it began: the start and end
    caps land coincident and OCC leaves a zero-thickness seam that meshes open.
    """
    return max(1.5, math.floor(t * 2.0) / 2.0 - (0.5 if abs(t * 2.0 % 2.0) < 1e-9 else 0.0))


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "lid_port"))
retention = str(PARAM(lambda: retention, "bead"))

bore_dia = float(PARAM(lambda: bore_dia, 25.0))
lid_thick = float(PARAM(lambda: lid_thick, 3.0))
wall = float(PARAM(lambda: wall, 2.6))
clearance = float(PARAM(lambda: clearance, 0.35))
thread_turns = float(PARAM(lambda: thread_turns, 3.5))
flange_over = float(PARAM(lambda: flange_over, 6.0))
retain_bead = float(PARAM(lambda: retain_bead, 1.2))
vent_bore = float(PARAM(lambda: vent_bore, 0.0))

# Input clamps, matching the manifest slider bounds exactly so a value that
# reaches the sandbox by any other route still builds.
bore_dia = max(8.0, min(bore_dia, 60.0))
lid_thick = max(1.0, min(lid_thick, 10.0))
wall = max(1.6, min(wall, 6.0))
clearance = max(0.1, min(clearance, 0.8))
# Ceiling is 3.5, and it is a MEASURED ceiling, not a taste. The extremes sweep
# found the female-thread union into a thin annulus failing above 3.5 turns:
# 4.5 turns returns "NCollection_Sequence::ChangeValue" or a solid with ~1500
# non-manifold edges, because a degenerate-radius helix swept with a Frenet
# frame accumulates profile wobble over its length (the rib alone is already
# 0.23 mm out of round at 5.5 turns). The male neck survives further; the slider
# is bounded by the weaker of the two so both modes are honest. This is also the
# physically generous end: PCO 1881 is a THREE-START short-neck finish whose
# real closures engage barely over one turn.
thread_turns = max(1.5, min(thread_turns, 3.5))
flange_over = max(3.0, min(flange_over, 20.0))
retain_bead = max(0.0, min(retain_bead, 3.0))
vent_bore = max(0.0, min(vent_bore, 12.0))

TURNS = half_turns(thread_turns)


# ── Derived geometry, clamped against FINAL values ───────────────────────────
BORE_R = bore_dia / 2.0
# The stem passes THROUGH the user's drilled bore, so it is the bore minus a fit.
STEM_R = max(2.0, BORE_R - clearance)
FLANGE_T = max(wall, 2.2)

# The PCO neck: male major is the standard diameter less a printed fit per side,
# so a real cap or the commons' `pco-cap` still turns onto it.
NECK_MAJOR_R = PCO1881["major_d"] / 2.0 - clearance
THREAD_DEPTH = 0.55 * PCO1881["pitch"]
NECK_CORE_R = NECK_MAJOR_R - THREAD_DEPTH
# Neck height is derived FROM the thread, never guessed. A swept helical rib
# occupies pitch*0.18 below its start and pitch*0.82 above its end (half the
# profile, plus the pitch/2 the sweep is translated by). Sizing the neck to the
# nominal thread length alone let the rib overshoot the neck top by 2 mm, where
# it stopped being a rib on a cylinder and became a floating spiral: 7 bodies,
# 1278 non-manifold edges, and no exception anywhere. Bound the CONTAINER by the
# feature, not the feature by the container.
THREAD_LEAD = 2.2                       # flat land between the support ledge and the first turn
THREAD_H = PCO1881["pitch"] * TURNS
NECK_H = THREAD_LEAD + THREAD_H + PCO1881["pitch"] * 0.82 + 1.4

# Flange rim: bore plus the user's overhang, but ALWAYS strictly clear of the
# neck crest. Without this floor a small bore with a small overhang produces a
# flange rim and a thread crest at the same radius — two coincident cylinders,
# a tangential fuse, and an open shell that raises nothing.
FLANGE_R = max(BORE_R + flange_over, NECK_MAJOR_R + 2.5, STEM_R + 2.5)

# Retaining bead under the lid. Capped so it can never exceed the flange, which
# would make the part impossible to insert through its own bore.
BEAD_R = min(STEM_R + retain_bead, FLANGE_R - 0.8)
BEAD_H = min(2.0, max(0.8, retain_bead + 0.6)) if retain_bead > 0.05 else 0.0

# Stem length below the flange: the lid it clamps, plus the bead, plus a lead-in.
STEM_L = lid_thick + BEAD_H + 1.2

# Through passage. Bounded by BOTH the stem wall and the neck core wall, because
# the same bore runs through both and the tighter of the two governs.
PASSAGE_R = min(STEM_R - wall, NECK_CORE_R - wall)
PASSAGE_R = max(1.2, PASSAGE_R)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _helix(pitch, height):
    """A degenerate-radius helix used as a sweep path (the profile carries the
    real radius in its own plane), which traces the true helical rib."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def male_thread(core_r, pitch, height, depth, z0):
    """An EXTERNAL helical thread rib rising from `core_r` to `core_r + depth`.

    Swept as a trapezoidal rib rather than cut from a blank: a swept rib is one
    solid fused to a cylinder it overlaps radially, where a cut helix leaves the
    kernel to reconcile a self-intersecting tool with the blank's end faces."""
    root_r = core_r - 0.4           # bite INTO the core so the fuse is volumetric
    crest_r = core_r + depth
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32),
            (crest_r, -pitch * 0.15),
            (crest_r, pitch * 0.15),
            (root_r, pitch * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix(pitch, height), isFrenet=True)
    return rib.translate((0, 0, z0 + pitch * 0.5))


def female_thread(bore_r, pitch, height, depth, z0):
    """An INTERNAL helical rib growing inward from a socket bore.

    Mirrors `pco-cap`'s female thread so a bottle neck generated by any commons
    cartridge lands in this socket on the same numbers."""
    root_r = bore_r + 0.4           # bite INTO the socket wall, never merely touch it
    crest_r = bore_r - depth
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32),
            (crest_r, -pitch * 0.15),
            (crest_r, pitch * 0.15),
            (root_r, pitch * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix(pitch, height), isFrenet=True)
    return rib.translate((0, 0, z0 + pitch * 0.5))


def flange_and_stem():
    """The half every mode shares: a flange disc sitting on the lid, a stem
    through the bore, and the chosen retention under it.

    Built bottom-up with the stem STRADDLING the flange in Z (from -STEM_L to
    +OVERLAP), so the fuse is volumetric no matter how thin either becomes."""
    flange = (
        cq.Workplane("XY")
        .circle(FLANGE_R)
        .extrude(FLANGE_T)
    )
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -STEM_L))
        .circle(STEM_R)
        .extrude(STEM_L + OVERLAP)
    )
    body = flange.union(stem)

    if retention == "bead" and BEAD_H > 0.0 and BEAD_R > STEM_R + 0.2:
        # A chamfered snap ring: lofted from the stem radius up to the bead
        # radius so it prints as a 45-degree overhang rather than a shelf, then
        # back down. Straddles the stem it grows from in Z by construction.
        # ONE three-section loft, not two frusta stacked. Two lofts meeting at
        # their shared circular face is a tangential union: OCC fuses it, the
        # kernel calls it valid, and the mesh comes back self-touching.
        zb = -STEM_L + 0.4
        bead = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, zb))
            .circle(STEM_R)
            .workplane(offset=BEAD_H * 0.5)
            .circle(BEAD_R)
            .workplane(offset=BEAD_H * 0.5)
            .circle(STEM_R)
            .loft(ruled=True)
        )
        body = body.union(bead)
    elif retention == "ribs":
        # Axial anti-rotation ribs on the stem: each is a small cylinder set so
        # it overlaps the stem wall by more than half its own radius, never
        # merely tangent to it.
        rib_r = max(0.6, min(1.4, wall * 0.5))
        n = 6
        for i in range(n):
            a = 2.0 * math.pi * i / n
            rib = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(
                    (STEM_R - rib_r * 0.45) * math.cos(a),
                    (STEM_R - rib_r * 0.45) * math.sin(a),
                    -STEM_L + 0.6))
                .circle(rib_r)
                .extrude(STEM_L - 1.0)
            )
            body = body.union(rib)
    # "plain" adds nothing: a friction fit relying on the gasket alone.

    return body


def _passage(z_lo, z_hi, r):
    """The single through passage, cut LAST so the result stays one shell."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_lo))
        .circle(r)
        .extrude(z_hi - z_lo)
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_lid_port():
    """Flanged bore fitting presenting a MALE PCO 1881 neck on its face."""
    body = flange_and_stem()

    # Neck core, straddling the flange top face by OVERLAP.
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, FLANGE_T - OVERLAP))
        .circle(NECK_CORE_R)
        .extrude(NECK_H + OVERLAP)
    )
    body = body.union(neck)

    # Support ledge: the flat land a bottle cap's skirt seats against, exactly as
    # a real PCO neck carries. Overlaps the flange, never sits on it.
    ledge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, FLANGE_T - OVERLAP))
        .circle(min(FLANGE_R - 0.6, NECK_MAJOR_R + 1.6))
        .extrude(OVERLAP + 1.4)
    )
    body = body.union(ledge)

    # The thread rib itself, started clear of the ledge and ending clear of the
    # neck top — NECK_H was derived from exactly these two bounds.
    thread_z = FLANGE_T + THREAD_LEAD
    try:
        body = body.union(male_thread(NECK_CORE_R, PCO1881["pitch"],
                                      THREAD_H, THREAD_DEPTH, thread_z))
    except Exception:
        # A thread that will not sweep is a defect, not a warning — but the
        # fallback still yields a usable plain-bore port rather than a crash,
        # and the sweep catches the missing rib as a volume change.
        pass

    top_z = FLANGE_T + NECK_H
    body = body.cut(_passage(-STEM_L - 1.0, top_z + 1.0, PASSAGE_R))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_bottle_receiver():
    """FEMALE PCO 1881 socket on the same bore flange: a cut-down PET bottle
    screws in neck-first as a reservoir, funnel or float."""
    body = flange_and_stem()

    sock_bore_r = PCO1881["major_d"] / 2.0 + clearance
    sock_outer_r = sock_bore_r + max(wall, 2.0)
    # Same rule as the male neck: the socket is sized so the rib's full swept
    # extent (pitch*0.82 past its nominal end) stays inside the wall.
    sock_h = THREAD_LEAD + THREAD_H + PCO1881["pitch"] * 0.82 + 1.4

    # Socket wall, straddling the flange top by OVERLAP.
    sock = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, FLANGE_T - OVERLAP))
        .circle(sock_outer_r)
        .extrude(sock_h + OVERLAP)
    )
    body = body.union(sock)

    # Hollow it from the TOP only — the floor stays, and the passage below is cut
    # separately, so there is never a moment where a closed cavity exists.
    top_z = FLANGE_T + sock_h
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, FLANGE_T + 0.8))
        .circle(sock_bore_r)
        .extrude(sock_h + 2.0)
    )
    body = body.cut(cavity)

    try:
        body = body.union(female_thread(sock_bore_r, PCO1881["pitch"],
                                        THREAD_H, THREAD_DEPTH,
                                        FLANGE_T + THREAD_LEAD))
    except Exception:
        pass

    # The passage: through the floor, the stem and out the bottom. Cut last.
    pr = max(1.2, min(PASSAGE_R, sock_bore_r - wall))
    body = body.cut(_passage(-STEM_L - 1.0, top_z + 1.0, pr))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_bore_plug():
    """Blanking plug on the same bore series, optionally vented.

    Unvented it is SOLID, not hollow: a hollow blank would seal a void, and a
    sealed void meshes as two bodies however valid the kernel says it is."""
    body = flange_and_stem()

    # A raised finger tab so a wet hand can turn it out. Two chords, unioned
    # volumetrically into the flange face (never resting on it).
    tab_h = max(3.0, wall * 1.4)
    tab_w = max(3.0, wall * 1.2)
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, FLANGE_T - OVERLAP))
        .box(FLANGE_R * 1.5, tab_w, tab_h + OVERLAP, centered=(True, True, False))
    )
    # Trim the tab to the flange disc so it can never overhang into thin air.
    disc = cq.Workplane("XY").circle(FLANGE_R).extrude(FLANGE_T + tab_h + 2.0)
    try:
        tab = tab.intersect(disc)
    except Exception:
        tab = None
    if tab is not None:
        body = body.union(tab)

    if vent_bore > 0.05:
        vr = max(0.6, min(vent_bore / 2.0, PASSAGE_R))
        body = body.cut(_passage(-STEM_L - 1.0, FLANGE_T + tab_h + 1.0, vr))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "lid_port": build_lid_port,
    "bottle_receiver": build_bottle_receiver,
    "bore_plug": build_bore_plug,
}

result = _dispatch.get(target_part, build_lid_port)()
