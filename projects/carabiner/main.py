"""
Carabiner / Quick-Link — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A UTILITY clip for keys, gear, bags, and organisation. NOT load-rated and NOT for
climbing, fall protection, or any life-safety use — printed plastic is not a safety
device. See the README safety note.

Three parts (dispatched via `target_part`):
  * "spring_carabiner" — a stadium-shaped (racetrack) body with a gate opening and a
                         printed cantilever sprung gate arm that flexes to open and
                         springs closed.
  * "screw_link"       — a quick-link: the body's gap is flanked by a short post that
                         carries a real EXTERNAL thread (volumetric-rib helix,
                         ~2-3 turns) so a printed sleeve/nut screws over to close it.
  * "s_hook"           — an open S / double hook for hanging.

The body is a flat racetrack RING (outer stadium minus inner stadium, extruded to a
thickness) — robust, watertight, and printable flat. The gate is the shared CDG
interface.

Thread strategy (screw_link) uses the verified watertight + fast idiom: a
trapezoidal profile swept along a real makeHelix path for ~2-3 turns, unioned as a
rib whose root is pushed INTO the post wall (the `overlap`) so the boolean is a
clean volumetric fuse, not a fragile tangent kiss.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `length`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "spring_carabiner"))  # spring_carabiner|screw_link|s_hook
gate_type   = str(PARAM(lambda: gate_type,    "spring_gate"))       # spring_gate|screw_gate|simple_hook

length      = float(PARAM(lambda: length,     60.0))   # overall length of the clip (mm)
spine       = float(PARAM(lambda: spine,       6.0))   # spine (stock) cross-section size (mm)
opening     = float(PARAM(lambda: opening,    12.0))   # gate opening size (mm)
inner_w     = float(PARAM(lambda: inner_w,    20.0))   # interior width of the loop (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
length   = max(30.0, min(length, 140.0))
spine    = max(3.0, min(spine, 14.0))
opening  = max(6.0, min(opening, 40.0))
inner_w  = max(10.0, min(inner_w, 60.0))


# ── Stadium (racetrack) helpers ──────────────────────────────────────────────
def stadium_2d(total_len, width):
    """A closed stadium (racetrack) wire in XY, centred at the origin, long axis
    along Y: two straight sides plus semicircular ends of radius width/2."""
    half_w = width / 2.0
    straight = max(1.0, total_len - width)
    return (
        cq.Workplane("XY")
        .moveTo(-half_w, -straight / 2.0)
        .lineTo(-half_w, straight / 2.0)
        .threePointArc((0, straight / 2.0 + half_w), (half_w, straight / 2.0))
        .lineTo(half_w, -straight / 2.0)
        .threePointArc((0, -straight / 2.0 - half_w), (-half_w, -straight / 2.0))
        .close()
    )


def ring_body(total_len, outer_w, stock, thick):
    """A flat racetrack RING: outer stadium minus inner stadium, extruded `thick` in
    Z. `stock` is the radial rail width. Watertight and printable flat."""
    outer = stadium_2d(total_len, outer_w).extrude(thick)
    inner = (
        stadium_2d(total_len - 2.0 * stock, outer_w - 2.0 * stock)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    return outer.cut(inner)


# ── Thread idiom (inlined; imports of repo libs are blocked in sandbox) ───────
def _helix_path(pitch, height):
    """A helical wire centred on Z (radius ~0 so a swept profile already at the
    target radius traces the true helix)."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    """External helical rib (bottle-thread idiom). Root bites into the shaft by
    `overlap`; crest sticks out to shaft_r + thr_depth. ~2-3 turns."""
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


# ── Part builders ────────────────────────────────────────────────────────────
def _gate_gap_cutter(outer_w, thick):
    """A box that removes a section of the +X straight rail to form the gate
    opening, spanning `opening` along Y."""
    half_w = outer_w / 2.0
    return (
        cq.Workplane("XY")
        .box(spine * 3.0, opening, thick + 2.0, centered=(True, True, True))
        .translate((half_w, 0.0, thick / 2.0))
    )


def build_spring_carabiner():
    """Racetrack body with a gate opening + a printed cantilever sprung gate arm
    that flexes into the opening and springs shut against the lower lip."""
    thick = spine
    stock = spine
    outer_w = inner_w + 2.0 * stock
    body = ring_body(length, outer_w, stock, thick)
    body = body.cut(_gate_gap_cutter(outer_w, thick))

    half_w = outer_w / 2.0
    arm_th = max(1.4, stock * 0.55)
    arm_len = opening + stock
    # The sprung arm: a slim bar anchored at the top of the opening, spanning down
    # across it, offset slightly inward (−X) so it sits behind the rail line.
    gate = (
        cq.Workplane("XY")
        .box(arm_th, arm_len, thick * 0.8, centered=(True, True, True))
        .translate((half_w - stock * 0.5, 0.0, thick / 2.0))
    )
    # Anchor tying the arm to the upper rail at the top of the opening.
    anchor = (
        cq.Workplane("XY")
        .box(stock * 1.4, arm_th * 1.6, thick, centered=(True, True, True))
        .translate((half_w - stock * 0.3, arm_len / 2.0 - arm_th * 0.4, thick / 2.0))
    )
    body = body.union(gate).union(anchor)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_screw_link():
    """A quick-link: racetrack body with a gap, and the gap flanked by a short post
    carrying a real (volumetric-rib) EXTERNAL thread, ~2-3 turns, so a printed
    sleeve/nut screws down to bridge and close the link."""
    thick = spine
    stock = spine
    outer_w = inner_w + 2.0 * stock
    body = ring_body(length, outer_w, stock, thick)
    body = body.cut(_gate_gap_cutter(outer_w, thick))

    half_w = outer_w / 2.0
    post_r = max(1.6, stock * 0.6)
    pitch = max(1.6, post_r * 0.9)
    turns = 2.5
    thread_h = pitch * turns
    # Post is taller than the thread on BOTH ends so the helix start/end fully embed
    # in solid material — that is what keeps the male-thread union watertight.
    post_h = thread_h + 2.0 * pitch + 2.0
    cx = half_w - stock / 2.0
    cy = -opening / 2.0 + stock * 0.2
    post = (
        cq.Workplane("XY")
        .circle(post_r)
        .extrude(post_h)
        .translate((cx, cy, thick))
    )
    thr_depth = 0.5 * pitch
    overlap = min(0.6, post_r * 0.35 + 0.2)
    # Lift the rib a full pitch so its lower turn starts inside the post body.
    thread = male_thread(post_r, pitch, thread_h, thr_depth, overlap).translate(
        (cx, cy, thick + pitch)
    )
    body = body.union(post).union(thread)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_s_hook():
    """An open S / double hook: a flat racetrack ring split so both ends open, giving
    the classic double-hook silhouette. Robust flat-stock variant for hanging."""
    thick = spine
    stock = spine
    outer_w = inner_w + 2.0 * stock
    body = ring_body(length, outer_w, stock, thick)
    # Open BOTH ends: cut a gap on +X near the top and on −X near the bottom so the
    # ring becomes an S of two opposed hooks.
    half_w = outer_w / 2.0
    gap = max(opening, stock * 1.5)
    top_cut = (
        cq.Workplane("XY")
        .box(spine * 3.0, gap, thick + 2.0, centered=(True, True, True))
        .translate((half_w, length / 2.0 - gap / 2.0 - stock, thick / 2.0))
    )
    bot_cut = (
        cq.Workplane("XY")
        .box(spine * 3.0, gap, thick + 2.0, centered=(True, True, True))
        .translate((-half_w, -length / 2.0 + gap / 2.0 + stock, thick / 2.0))
    )
    body = body.cut(top_cut).cut(bot_cut)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "screw_link":
    result = build_screw_link()
elif target_part == "s_hook":
    result = build_s_hook()
else:
    result = build_spring_carabiner()
