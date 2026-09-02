"""
Busbar Insulating Shroud — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The cover over the live metal, on the rail everything else already clips to.

A control cabinet or a consumer unit is a row of terminals, a comb busbar and a
great deal of exposed conductor between them. The commons has seven cartridges
that clip to DIN EN 60715 TS35 rail and not one that covers anything: `din-rail-
end-stop` terminates the rail, `din-terminal-comb` and `busbar-support` carry the
bar, `terminal-cover` covers ONE terminal — and the long runs between them stay
open. Every one of those runs is a place a hand goes when a board is being
worked on live, which is most of the times a board is worked on at all.

Modes are dispatched via `target_part`:
  * "busbar_shroud"   — a tunnel over a comb or bar run, open at both ends so
                        the conductor continues, closed everywhere a hand is.
  * "terminal_shroud" — the same tunnel with lead-out slots in its front face,
                        so conductors leave without the cover coming off.
  * "end_barrier"     — a flat insulating partition standing between two
                        terminals of different phases or circuits.

All three share the same rail clip back, whose geometry mirrors `din-module`'s
published constants exactly.

The aperture rule, and what it is not:
  IEC 60529's IP2X access probe is a Ø12 mm jointed test finger. Every aperture
  this cartridge cuts has its minor dimension capped BELOW that figure, in the
  geometry rather than in a warning, because an aperture that a finger enters is
  not a shroud. That is a geometric property of the model. It is NOT a tested
  rating, and this cartridge does not claim one — see the README.

Watertightness strategy:
  * The tunnel is open at BOTH ends by construction. A shroud closed at its ends
    would be a sealed void, and a sealed void meshes as two bodies however valid
    the kernel reports the solid.
  * The body width always contains the rail hooks. A narrower body would sit
    between them, the hooks would touch nothing, and the render would be three
    separate watertight solids that no watertightness check can see.
  * Every union straddles what it grows from; every cut is bounded inside the
    blank that must contain it, with a margin that scales.
  * Slot counts are derived from the space that survives the margins, never
    picked first and trimmed.
  * No fillet on any edge a slot has touched.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
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


# ── DIN EN 60715 TS35 top-hat rail (mirrors din-module) ──────────────────────
RAIL_SPAN = 35.0
LIP_GRIP = 5.0
CLEAR = 0.35
HOOK_WALL = 2.6

# IEC 60529 IP2X access probe: a Ø12 mm jointed test finger. Apertures are
# capped BELOW it in the geometry, not in a warning.
IP2X_PROBE_DIA = 12.0
APERTURE_CAP = 11.0

OVERLAP = 1.0


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "busbar_shroud"))
rail_depth_class = str(PARAM(lambda: rail_depth_class, "ts35_7v5"))

run_len = float(PARAM(lambda: run_len, 45.0))
bar_w = float(PARAM(lambda: bar_w, 12.0))
bar_h = float(PARAM(lambda: bar_h, 25.0))
barrier_h = float(PARAM(lambda: barrier_h, 45.0))
aperture = float(PARAM(lambda: aperture, 6.0))
lead_outs = float(PARAM(lambda: lead_outs, 4.0))
wall = float(PARAM(lambda: wall, 2.4))
plate_th = float(PARAM(lambda: plate_th, 3.0))
spring_thick = float(PARAM(lambda: spring_thick, 2.0))

run_len = max(10.0, min(run_len, 120.0))
bar_w = max(4.0, min(bar_w, 40.0))
bar_h = max(5.0, min(bar_h, 50.0))
barrier_h = max(15.0, min(barrier_h, 80.0))
# The cap is applied HERE, to the value the geometry uses, not to the slider —
# an aperture limit enforced only in the UI is an aperture limit that a preset,
# a saved configuration or an API call walks straight through.
aperture = max(0.0, min(aperture, APERTURE_CAP))
lead_outs = int(max(0, min(round(lead_outs), 10)))
wall = max(1.6, min(wall, 5.0))
plate_th = max(2.5, min(plate_th, 8.0))
spring_thick = max(1.2, min(spring_thick, 4.0))

RAIL_DEPTH = 15.0 if rail_depth_class == "ts35_15" else 7.5
JAW_H = RAIL_DEPTH + 2.5
CATCH = max(1.5, min(LIP_GRIP - 1.0, 3.0))

# The body must ALWAYS contain the hooks (see the module docstring).
MIN_BODY_W = RAIL_SPAN + 2.0 * HOOK_WALL + 4.0
BODY_W = max(MIN_BODY_W, bar_w + 2.0 * wall + 2.0)
HOOK_LEN = min(run_len, 40.0)


# ── Rail hooks (mirroring din-module) ────────────────────────────────────────
def _extrude_profile_xz(pts, length):
    return cq.Workplane("XZ").polyline(pts).close().extrude(length / 2.0, both=True)


def _fixed_hook():
    """Rigid hook on the +X side (the fixed reference jaw)."""
    x_in = RAIL_SPAN / 2.0 - CLEAR
    x_wall = RAIL_SPAN / 2.0 + HOOK_WALL
    x_catch = x_in - CATCH
    pts = [
        (x_catch, plate_th), (x_wall, plate_th),
        (x_wall, -JAW_H), (x_catch, -JAW_H),
        (x_catch, -JAW_H + HOOK_WALL), (x_in, -JAW_H + HOOK_WALL),
        (x_in, 0.0), (x_catch, 0.0),
    ]
    return _extrude_profile_xz(pts, HOOK_LEN)


def _spring_hook():
    """COMPLIANT sprung hook on the -X side: a folded cantilever whose bend
    energy lives in the beam, so the wall is never held in permanent strain."""
    t = spring_thick
    x_lip = -RAIL_SPAN / 2.0
    x_out = x_lip - CLEAR
    x_root_in = x_lip + 7.0
    x_catch = x_out + CATCH
    outer = [
        (x_root_in, plate_th), (x_out, plate_th),
        (x_out, -JAW_H), (x_catch, -JAW_H),
    ]
    inner = [
        (x_catch, -JAW_H + t), (x_out + t, -JAW_H + t),
        (x_out + t, plate_th - t - 2.0), (x_root_in, plate_th - t - 2.0),
    ]
    return _extrude_profile_xz(outer + inner, HOOK_LEN)


def clip_back():
    """The plate the hooks root into, and everything else grows from."""
    plate = (
        cq.Workplane("XY")
        .box(BODY_W, run_len, plate_th, centered=(True, True, False))
    )
    return plate.union(_fixed_hook()).union(_spring_hook())


# ── Shared shroud geometry ───────────────────────────────────────────────────
def tunnel(body):
    """An inverted-U hood over the conductor zone, OPEN AT BOTH ENDS.

    Open ends are not a convenience: a shroud closed at its ends encloses a
    void, and a sealed void meshes as a second body however valid the kernel
    calls the solid. They are also correct — a busbar run continues past the
    cover, which is the whole reason a cover is needed in the middle of it."""
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_th - OVERLAP))
        .box(bar_w + 2.0 * wall, run_len, bar_h + wall + OVERLAP,
             centered=(True, True, False))
    )
    body = body.union(outer)
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_th))
        .box(bar_w, run_len + 2.0, bar_h, centered=(True, True, False))
    )
    return body.cut(cavity)


def lead_out_slots(body):
    """Slots in the front face so conductors leave without the cover coming off.

    Count derived from the space that survives the end margins. Width is capped
    below the IP2X probe by the geometry itself — an aperture a finger enters is
    not a shroud, and a limit enforced only in the UI is not a limit."""
    n = lead_outs
    if n < 1 or aperture < 0.8:
        return body
    margin = max(3.0, wall)
    avail = run_len - 2.0 * margin
    slot_w = min(aperture, APERTURE_CAP)
    pitch = avail / n if n else 0.0
    if avail <= 0 or pitch < slot_w + 1.5:
        return body
    slot_h = min(aperture, bar_h - 2.0)
    if slot_h < 0.8:
        return body
    x0 = bar_w / 2.0
    for i in range(n):
        y = -avail / 2.0 + pitch * (i + 0.5)
        tool = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x0, y, plate_th + 1.0))
            .box(2.0 * wall + 2.0, slot_w, slot_h, centered=(False, True, False))
        )
        try:
            body = body.cut(tool)
        except Exception:
            pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_busbar_shroud():
    """A tunnel over a comb or bar run, open at both ends."""
    body = tunnel(clip_back())
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_terminal_shroud():
    """The same tunnel with lead-out slots in its front face."""
    body = lead_out_slots(tunnel(clip_back()))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_end_barrier():
    """A flat insulating partition standing between two terminals.

    Solid, not shelled: a shelled barrier would trap a void, and the barrier's
    whole job is to be continuous material between two conductors."""
    body = clip_back()
    fin = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_th - OVERLAP))
        .box(BODY_W, wall, barrier_h + OVERLAP, centered=(True, True, False))
    )
    body = body.union(fin)

    # Lightening cut-outs in the fin, bounded well inside it so a continuous
    # frame always survives. Their minor dimension is capped below the IP2X
    # probe like every other aperture here — a hole in a barrier is an aperture
    # whatever it is called.
    inner_w = BODY_W - 2.0 * 6.0
    inner_h = barrier_h - 2.0 * 6.0
    slot_w = min(APERTURE_CAP - 1.0, max(2.0, inner_w * 0.25))
    if inner_w > 12.0 and inner_h > 8.0 and slot_w >= 2.0:
        pitch = slot_w + 4.0
        n = int(math.floor(inner_w / pitch))
        if n >= 1:
            span = (n - 1) * pitch
            for i in range(n):
                x = -span / 2.0 + i * pitch
                tool = (
                    cq.Workplane("XY")
                    .transformed(offset=cq.Vector(x, 0.0, plate_th + 6.0))
                    .box(slot_w, wall + 2.0, inner_h, centered=(True, True, False))
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
    "busbar_shroud": build_busbar_shroud,
    "terminal_shroud": build_terminal_shroud,
    "end_barrier": build_end_barrier,
}

result = _dispatch.get(target_part, build_busbar_shroud)()
