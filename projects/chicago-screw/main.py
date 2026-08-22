"""Chicago Screw (binding post) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The two-part binding post leatherworkers call a Chicago screw or sex bolt: a barrel post
with a flat head and an internal bore, and a cap screw that threads into it from the other
side. Together they clamp a leather strap sandwich without a rivet setter, and unlike a
rivet they come apart again — which is why every adjustable strap, watch band and knife
sheath uses them. This is the rigid hard good the Fashion Cabinet `chicago-screw` notion
places and bridges to here for its geometry.

Modes (dispatched via `target_part`):
  * "post" — the barrel with the flat head and the threaded bore.
  * "cap"  — the cap screw with the flat head and the threaded shank.
  * "set"  — both, laid out on one plate as separate bodies.

Threads are COSMETIC: a revolved sawtooth profile cut into (or raised on) the bore/shank
wall — never a long helical sweep. A printed thread this small does not hold anyway; the
engagement is a light interference press that the sawtooth ratchets into. Print, then chase
the joint with a drop of thread-locker if the strap sees real load.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `post_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
head_dia   = float(PARAM(lambda: head_dia,   10.0))  # flat head diameter, both parts (mm)
head_t     = float(PARAM(lambda: head_t,      2.0))  # head thickness (mm)
post_dia   = float(PARAM(lambda: post_dia,    5.0))  # barrel outside diameter (mm)
stack_t    = float(PARAM(lambda: stack_t,     6.0))  # leather stack the screw clamps (mm)
thread_dia = float(PARAM(lambda: thread_dia,  3.0))  # nominal thread diameter (mm)
thread_len = float(PARAM(lambda: thread_len,  5.0))  # engaged thread length (mm)
slot_w     = float(PARAM(lambda: slot_w,      1.2))  # flat-blade driver slot width (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # post|cap|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
# Real Chicago screws: 8-12 mm heads, 4-6 mm barrels, post lengths from 3 to 20 mm.
head_dia   = max(6.0, min(head_dia, 20.0))
head_t     = max(1.2, min(head_t, 5.0))
post_dia   = max(3.0, min(post_dia, head_dia - 2.0))
stack_t    = max(1.5, min(stack_t, 25.0))
# The thread must leave real barrel wall: at least 0.9 mm all round.
thread_dia = max(1.6, min(thread_dia, post_dia - 1.8))
slot_w     = max(0.6, min(slot_w, head_dia * 0.18))

# ── Derived geometry ─────────────────────────────────────────────────────────
# The post barrel spans most of the stack; the cap shank makes up the rest plus overlap.
post_barrel = max(1.0, stack_t * 0.55)
cap_shank = max(1.0, stack_t - post_barrel)
# Engaged thread length can never exceed the barrel's own depth minus a floor.
thread_len = max(1.5, min(thread_len, post_barrel + cap_shank - 0.8))
bore_depth = min(thread_len + 1.0, post_barrel + head_t - 0.8)
slot_d = max(0.5, head_t * 0.55)
thread_pitch = max(0.6, min(thread_dia * 0.25, 1.0))  # cosmetic sawtooth pitch
thread_depth = thread_pitch * 0.5                     # radial tooth depth
clear = 0.25                                          # bore-to-shank diametral clearance


def _head(dia, thick):
    """A flat disc head sitting on Z=0, top rim softened on the clean blank."""
    wp = cq.Workplane("XY").circle(dia / 2.0).extrude(thick)
    try:
        wp = wp.edges(">Z").fillet(min(thick * 0.35, 0.7))
    except Exception:
        pass
    return wp


def _driver_slot(dia, depth, z_top):
    """A flat-blade driver slot cutter across the head, overshooting both ends."""
    return (
        cq.Workplane("XY")
        .box(dia + 4.0, slot_w, depth + 2.0)
        .translate((0, 0, z_top - depth + (depth + 2.0) / 2.0 - 1.0))
    )


def _thread_teeth(r_ref, z0, length):
    """A cosmetic sawtooth thread: a stack of revolved triangular rings, no helix.

    Each turn is one triangle profile revolved 360 degrees, its inner edge at `r_ref`
    and its crest at `r_ref + thread_depth`. A ring stack reads as a thread at print
    resolution and avoids the segfault-prone long helical sweep. The caller positions
    `r_ref` on the shank wall (male) or inside the bore wall (female).
    """
    turns = max(1, int(length / thread_pitch))
    solids = None
    for i in range(turns):
        zc = z0 + (i + 0.5) * thread_pitch
        ring = (
            cq.Workplane("XZ")
            .moveTo(r_ref, zc - thread_pitch * 0.5)
            .lineTo(r_ref + thread_depth, zc)
            .lineTo(r_ref, zc + thread_pitch * 0.5)
            .close()
            .revolve(360, (0, 0, 0), (0, 1, 0))
        )
        solids = ring if solids is None else solids.union(ring)
    return solids


def build_post():
    """Barrel post: flat head + barrel + threaded blind bore, plus a driver slot."""
    head = _head(head_dia, head_t)
    barrel = (
        cq.Workplane("XY")
        .circle(post_dia / 2.0)
        .extrude(post_barrel + 0.4)
        .translate((0, 0, head_t - 0.4))
    )
    body = head.union(barrel)

    # Blind bore from the barrel's open top down toward (never through) the head.
    # The cosmetic internal thread is built INTO the cutter — bore cylinder unioned
    # with the sawtooth ring stack, then a single cut. Cutting once (rather than
    # cutting a bore and then unioning crests back in) is what keeps this watertight:
    # the crest-back-in approach produced negative-volume slivers in verification.
    top_z = head_t + post_barrel
    bore_r = thread_dia / 2.0 + clear / 2.0
    cutter = (
        cq.Workplane("XY")
        .circle(bore_r)
        .extrude(bore_depth + 2.0)
        .translate((0, 0, top_z - bore_depth))
    )
    teeth = _thread_teeth(bore_r - 0.05, top_z - bore_depth + 0.6,
                          max(1.0, bore_depth - 1.4))
    if teeth is not None:
        cutter = cutter.union(teeth)

    # Lead-in flare at the bore mouth, fused into the same cutter so the mouth opens
    # in one operation. Never a fillet after a cut.
    lead = (
        cq.Workplane("XY")
        .circle(bore_r)
        .workplane(offset=0.9)
        .circle(bore_r + 0.7)
        .loft(ruled=True)
        .translate((0, 0, top_z - 0.4))
    )
    cutter = cutter.union(lead)
    body = body.cut(cutter)

    body = body.cut(_driver_slot(head_dia, slot_d, head_t))
    return body


def build_cap():
    """Cap screw: flat head + threaded shank sized to the post bore, plus a driver slot."""
    head = _head(head_dia, head_t)
    shank_r = thread_dia / 2.0 - clear / 2.0
    shank_len = cap_shank + min(thread_len, bore_depth - 0.6) + 0.4
    shank = (
        cq.Workplane("XY")
        .circle(shank_r)
        .extrude(shank_len + 0.4)
        .translate((0, 0, head_t - 0.4))
    )
    body = head.union(shank)

    # Cosmetic external thread: sawtooth rings standing proud of the shank, over the
    # engaged length only. Clipped to the shank's own span so nothing floats.
    # Stop the thread 1.2 mm short of the tip taper: a ring straddling the taper cut
    # gets sliced into a floating sliver (the same failure the bag-feet boss hit).
    taper_clear = 1.2
    t_run = max(1.0, min(thread_len, shank_len - 0.6) - taper_clear)
    t_z0 = head_t + shank_len - taper_clear - t_run
    teeth = _thread_teeth(shank_r - 0.05, t_z0, t_run)
    if teeth is not None:
        body = body.union(teeth)

    # Tip lead-in: build a cone frustum that tapers the shank end, and cut away
    # everything outside it over the last 0.8 mm. A cut ring-minus-cone, never a
    # .chamfer() after the thread union (that is the segfault-prone ordering).
    tip_z = head_t + shank_len
    tip = (
        cq.Workplane("XY")
        .circle(shank_r + thread_depth + 1.0)
        .workplane(offset=0.8)
        .circle(shank_r * 0.55)
        .loft(ruled=True)
        .translate((0, 0, tip_z - 0.8))
    )
    ring = (
        cq.Workplane("XY")
        .circle(shank_r + thread_depth + 2.0)
        .extrude(1.2)
        .translate((0, 0, tip_z - 0.8))
    )
    body = body.cut(ring.cut(tip))

    body = body.cut(_driver_slot(head_dia, slot_d, head_t))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "post":
    result = build_post()
elif target_part == "cap":
    result = build_cap()
else:
    gap = max(head_dia * 0.4, 4.0)
    off = head_dia / 2.0 + gap / 2.0
    asm = cq.Assembly()
    asm.add(build_post().translate((-off, 0, 0)), name="post", color=cq.Color("#9a9a9e"))
    asm.add(build_cap().translate((off, 0, 0)), name="cap", color=cq.Color("#b4b4b8"))
    result = asm
