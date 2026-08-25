"""
Sharps Container Lid Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Turns an ordinary threaded jar into a one-way sharps container. A used needle is the
single most dangerous object in a small clinic, and the standard answer — a purpose
made, puncture-resistant, one-way container — is a purchased consumable. Where the
supply budget does not stretch, the observed substitute is an open bottle or a tin,
and an open container is the specific thing that causes needlestick injury: it can be
reached into, it spills when knocked, and it invites the recapping that causes most
injuries in the first place.

This adapter supplies the part that is actually missing. Jars are everywhere; the
one-way lid is not.

What "one-way" means here, mechanically:
  * A slot sized so a syringe hub passes but a hand does not.
  * A sprung BAFFLE behind the slot, so the opening admits from above and closes
    behind the drop — you cannot fish anything back out, and the contents do not
    pour out if the jar is knocked over.
  * A lock that, once closed, is destroyed rather than reopened.

Interchange: the thread lands on the published jar-thread family — the same CT
(continuous-thread) finishes the commons' jar-adapter cartridge already encodes — and
the slot is keyed to the published needle-gauge series. Nothing new is invented; the
cartridge is a recombination of two interfaces the commons already carries.

DISTINCT FROM the published `sharps-lid` cartridge. That one is a friction-fit lid
for a bucket or carboy, sized on a plain bore. This one is a THREADED jar adapter and
does not interchange with it: different attachment, different vessel class. The two
sit alongside each other deliberately rather than one superseding the other.

Standards encoded (mm), GPI/SPI continuous-thread jar finishes:
  63-400: thread major Ø 63.0, pitch 4.23, ~1 turn
  70-400: thread major Ø 70.0, pitch 4.23, ~1 turn
  89-400: thread major Ø 89.0, pitch 4.23, ~1 turn
  ("-400" is the GPI finish code for a shallow continuous thread; the number before
  it is the nominal outside diameter of the jar's thread in millimetres.)
  Needle/hub: Luer hub nominal Ø 7.5 mm; gauge series 14G-30G governs the slot's
  minimum width, since the slot must pass a hub, not a bare cannula.

Modes are dispatched via `target_part`:
  * "lid"     — the threaded lid with the entry slot and the baffle seat.
  * "baffle"  — the one-way flap that drops in behind the slot.
  * "closure" — the final lock that seals a full container permanently.

Watertightness strategy:
  Every part is one blank with THROUGH cuts, and every cut is bounded INSIDE the
  blank that must contain it — with a full margin — rather than run past its edges.
  A cut that reaches an edge is not a slot, it is a cut-off, and it severs the part
  into pieces that still tessellate. No fillet is taken on any edge a slot or bore
  has touched: OCC blends such arcs without raising and returns a non-watertight
  solid (found the hard way in graft-clip, this same batch).

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


# ── Jar thread standards (shared with the published jar-adapter family) ───────
# GPI/SPI continuous-thread finishes. The leading number is the nominal thread OD in
# millimetres; "-400" is the finish code for a shallow single-lead continuous thread.
JAR_THREADS = {
    "63-400": {"major_d": 63.0, "pitch": 4.23, "turns": 1.0},
    "70-400": {"major_d": 70.0, "pitch": 4.23, "turns": 1.0},
    "89-400": {"major_d": 89.0, "pitch": 4.23, "turns": 1.0},
}

# Needle gauge -> nominal cannula OD (mm). The SLOT is not sized from these: a needle
# arrives attached to a syringe, so the slot must pass the HUB. The series is carried
# because it sets the floor on slot width and because it is the published vocabulary
# the commons' needle-gauge cartridge already uses.
NEEDLE_GAUGE_OD = {
    "14G": 2.11, "16G": 1.65, "18G": 1.27, "20G": 0.91,
    "21G": 0.82, "23G": 0.64, "25G": 0.51, "27G": 0.41, "30G": 0.31,
}
LUER_HUB_D = 7.5   # nominal Luer hub Ø (mm) — the real gate on slot width


def jar_geo(name):
    """Look up nominal jar-thread geometry, defaulting to 70-400."""
    return JAR_THREADS.get(name, JAR_THREADS["70-400"])


def half_turns(n):
    """Nearest lower half-integer, never a whole integer.

    A whole number of turns produces a null sweep in OCC — the helix closes on itself
    and the swept profile degenerates. This is the same guard the published
    jar-adapter uses, and it is not optional."""
    return math.floor(max(0.5, n)) + 0.5


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "lid"))
jar_thread_std = str(PARAM(lambda: jar_thread_std, "70-400"))
needle_gauge_max = str(PARAM(lambda: needle_gauge_max, "18G"))
lock_style = str(PARAM(lambda: lock_style, "snap"))     # snap | screw | tab

slot_width_mm = float(PARAM(lambda: slot_width_mm, 11.0))
one_way_baffle = bool(PARAM(lambda: one_way_baffle, True))
wall = float(PARAM(lambda: wall, 3.0))
clearance = float(PARAM(lambda: clearance, 0.5))

# Clamp so extreme UI values still build watertight.
slot_width_mm = max(6.0, min(slot_width_mm, 22.0))
wall = max(2.0, min(wall, 6.0))
clearance = max(0.0, min(clearance, 1.2))


# ── Derived safety geometry ──────────────────────────────────────────────────
def effective_slot_w():
    """Slot width that passes a syringe hub but not a finger.

    Floor: the Luer hub plus a little slop, since a needle arrives attached to a
    syringe and a slot that only passes a bare cannula is unusable in practice.
    Ceiling: 22 mm, above which an adult finger enters easily and the container stops
    being one-way in the only sense that matters.

    The gauge series is consulted for the floor as well — a large-bore 14G needle on a
    heavy hub needs more room than a 30G insulin needle — but the hub, not the
    cannula, is what governs."""
    hub_floor = LUER_HUB_D + 1.5
    gauge_od = NEEDLE_GAUGE_OD.get(needle_gauge_max, 1.27)
    return max(hub_floor + gauge_od * 0.5, min(slot_width_mm, 22.0))


# ── Thread primitive (inlined — repo lib imports are blocked in the sandbox) ──
def _helix_path(pitch, height):
    """A helical wire centered on Z. Radius ~0 so the swept profile (already at the
    target radius in its own plane) traces the true helix."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib, ridges pointing INWARD to grab the jar's male
    thread. Root radius = bore_r + overlap so the rib bites into the wall material —
    a clean volumetric union instead of a fragile tangent kiss. Same convention as
    the published jar-adapter and bottle-thread cartridges."""
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
def build_lid():
    """The threaded lid: a jar-thread skirt, a solid top, and the entry slot.

    The slot is bounded INSIDE the top disk with a full wall of margin all round, so
    it can never reach the skirt and cut the lid open. That margin is what makes the
    difference between a lid and two arcs."""
    g = jar_geo(jar_thread_std)
    pitch = g["pitch"]
    tt = half_turns(g["turns"] + 0.5)

    bore_r = g["major_d"] / 2.0 + clearance
    out_r = bore_r + wall
    thread_h = pitch * tt
    top_t = max(2.5, wall)
    skirt_h = thread_h + top_t + 2.0

    body = cq.Workplane("XY").circle(out_r).extrude(skirt_h)
    # Jar bore, open at the bottom, stopping short of the top so the lid has a roof.
    bore = cq.Workplane("XY").circle(bore_r).extrude(skirt_h - top_t)
    body = body.cut(bore)

    # Female jar thread inside the skirt.
    thr_depth = min(pitch * 0.32, wall * 0.6)
    overlap = min(0.8, wall * 0.35 + 0.2)
    rib = female_thread(bore_r, pitch, thread_h, thr_depth, overlap)
    try:
        body = body.union(rib)
    except Exception:
        pass

    # Entry slot through the roof. Bounded inside the top disk with a full wall of
    # margin, so it can never reach the skirt.
    sw = effective_slot_w()
    max_half = max(1.0, bore_r - wall * 1.5)
    half_len = min(sw * 1.6, max_half)
    half_w = min(sw / 2.0, max_half * 0.6)
    z_roof = skirt_h - top_t
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, z_roof - 1.0))
        .box(2.0 * half_len, 2.0 * half_w, top_t + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # Baffle seat: a shallow ledge under the roof that the flap drops onto. Cut as a
    # bounded pocket inside the bore, never reaching the skirt wall.
    if one_way_baffle:
        seat_r = min(bore_r - wall * 0.6, out_r)
        seat_d = max(1.2, top_t * 0.45)
        if seat_r > half_len + 1.0:
            seat = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0.0, 0.0, z_roof - seat_d))
                .circle(seat_r).extrude(seat_d + 0.5)
            )
            try:
                body = body.cut(seat)
            except Exception:
                pass

    # Lock features on the outside of the skirt, so a closure can be fitted.
    if lock_style in ("snap", "tab"):
        # A shallow retaining bead. Added as a volumetric union that overlaps the
        # skirt, so it is never a tangent kiss.
        bead_h = max(1.2, wall * 0.4)
        bead_r = out_r + max(0.8, wall * 0.3)
        bead = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, skirt_h - top_t - bead_h * 1.5))
            .circle(bead_r).extrude(bead_h)
        )
        try:
            body = body.union(bead)
        except Exception:
            pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_baffle():
    """The one-way flap: a disk with a hinged tongue that swings down under a dropped
    sharp and falls closed behind it.

    Printed as ONE piece with a thin living hinge rather than as two parts and a pin —
    a pin joint in a container full of used needles is a part that can be pulled
    apart, which is exactly the failure the container exists to prevent."""
    g = jar_geo(jar_thread_std)
    bore_r = g["major_d"] / 2.0 + clearance
    disk_r = max(6.0, bore_r - wall * 0.7 - clearance)
    t = max(1.4, wall * 0.55)

    body = cq.Workplane("XY").circle(disk_r).extrude(t)

    sw = effective_slot_w()
    # The tongue is defined by the two cuts that free it: a slot on three sides,
    # leaving one edge as the living hinge. Every cut is bounded inside the disk.
    max_half = max(1.0, disk_r - wall)
    tongue_len = min(sw * 1.7, max_half * 1.5)
    tongue_w = min(sw * 1.25, max_half * 1.2)
    kerf = max(0.6, t * 0.5)

    if tongue_len > 2.0 and tongue_w > 2.0:
        # Two side kerfs and one end kerf, each a bounded box.
        for sign in (-1.0, 1.0):
            k = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(tongue_len * 0.1, sign * (tongue_w / 2.0 + kerf / 2.0), -1.0))
                .box(tongue_len, kerf, t + 2.0, centered=(True, True, False))
            )
            try:
                body = body.cut(k)
            except Exception:
                pass
        end = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(tongue_len * 0.1 + tongue_len / 2.0 + kerf / 2.0, 0.0, -1.0))
            .box(kerf, tongue_w + 2.0 * kerf, t + 2.0, centered=(True, True, False))
        )
        try:
            body = body.cut(end)
        except Exception:
            pass

        # Thin the hinge line so the tongue folds THERE rather than cracking randomly.
        # Depth is a fraction of thickness with a stated ligament remaining — the
        # lesson from graft-clip, where a groove sized independently of the wall cut
        # clean through it.
        hinge_lig = max(0.4, t * 0.45)
        hinge_d = min(t - hinge_lig, 0.8)
        if hinge_d >= 0.2:
            hx = tongue_len * 0.1 - tongue_len / 2.0
            groove = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(hx, 0.0, t - hinge_d))
                .box(max(0.8, kerf), tongue_w, hinge_d + 1.0, centered=(True, True, False))
            )
            try:
                body = body.cut(groove)
            except Exception:
                pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_closure():
    """The final lock: a cap that closes a full container permanently.

    Deliberately one-way. Once seated it is destroyed rather than reopened, because a
    sharps container that can be reopened for one more needle will be, and the whole
    chain of custody from clinic to incinerator depends on it staying shut."""
    g = jar_geo(jar_thread_std)
    bore_r = g["major_d"] / 2.0 + clearance
    out_r = bore_r + wall
    # Fits OVER the lid's retaining bead.
    cap_bore_r = out_r + max(0.8, wall * 0.3) + clearance
    cap_out_r = cap_bore_r + wall
    top_t = max(2.5, wall)
    height = max(6.0, wall * 3.0) + top_t

    body = cq.Workplane("XY").circle(cap_out_r).extrude(height)
    bore = cq.Workplane("XY").circle(cap_bore_r).extrude(height - top_t)
    body = body.cut(bore)

    # Internal catch ring that snaps past the lid's bead and cannot climb back.
    catch_r = max(1.0, cap_bore_r - max(0.7, wall * 0.3))
    catch_h = max(1.0, wall * 0.35)
    if catch_r < cap_bore_r:
        ring = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, max(0.0, height - top_t - catch_h * 2.0)))
            .circle(cap_bore_r).circle(catch_r)
            .extrude(catch_h)
        )
        try:
            body = body.union(ring)
        except Exception:
            pass

    # Grip flutes, each BOUNDED inside the cap wall so none can reach through it.
    flute_d = min(wall * 0.35, 1.0)
    if flute_d >= 0.3:
        n = 8
        pts = []
        for i in range(n):
            a = 2.0 * math.pi * i / n
            pts.append((math.cos(a) * (cap_out_r + flute_d * 0.4),
                        math.sin(a) * (cap_out_r + flute_d * 0.4)))
        tool = (
            cq.Workplane("XY")
            .pushPoints(pts)
            .circle(flute_d)
            .extrude(height)
        )
        try:
            body = body.cut(tool)
        except Exception:
            pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "lid": build_lid,
    "baffle": build_baffle,
    "closure": build_closure,
}

result = _dispatch.get(target_part, build_lid)()
