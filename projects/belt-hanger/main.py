"""Belt Hanger — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A multi-loop belt and accessory rack: a vertical spine carrying a column of open hooks,
topped by a rod hook that hangs the whole thing on a closet rail. Each open hook takes one
belt folded at its buckle, or a scarf, a tie, or a bag strap — pulled off the front without
disturbing its neighbours, which is the whole point of an open hook over a closed loop.

Modes (dispatched via `target_part`):
  * "belt"      — hooks sized and pitched for folded leather belts (20-50 mm webbing).
  * "scarf"     — wider, shallower hooks with a longer reach, for scarves and shawls.
  * "tie"       — many small closely-pitched hooks for ties and thin straps.

Geometry: the spine is a rounded slab. Each hook is a J built from an arm (a rounded slab
extruded forward) plus an upturn (a torus arc from `cq.Solid.makeTorus` wrapped in a
Workplane and trimmed with oversized boxes — never a swept path). The top rod hook is the
same three-quarter-torus technique the `garment-hanger` cartridge uses.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `hook_count`).
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
hook_count = int(  PARAM(lambda: hook_count, 6))     # open hooks on the spine
strap_w    = float(PARAM(lambda: strap_w,    38.0))  # widest strap the hook must take (mm)
hook_reach = float(PARAM(lambda: hook_reach, 34.0))  # how far each hook stands off the spine (mm)
spine_w    = float(PARAM(lambda: spine_w,    26.0))  # spine width (mm)
spine_t    = float(PARAM(lambda: spine_t,    9.0))   # spine thickness, front to back (mm)
rod_dia    = float(PARAM(lambda: rod_dia,    32.0))  # closet rod the top hook clears (mm)

target_part = str(PARAM(lambda: target_part, "belt"))


# ── Safe clamps ──────────────────────────────────────────────────────────────
hook_count = max(2,    min(hook_count, 14))
# 20 / 25 / 38 / 50 mm are the standard webbing and belt widths; allow a little either way.
strap_w    = max(12.0, min(strap_w, 60.0))
hook_reach = max(14.0, min(hook_reach, 70.0))
spine_w    = max(14.0, min(spine_w, 50.0))
spine_t    = max(5.0,  min(spine_t, 18.0))
rod_dia    = max(18.0, min(rod_dia, 45.0))

# ── Mode profiles ────────────────────────────────────────────────────────────
# Each mode re-proportions the same hook family rather than changing its topology.
if target_part == "scarf":
    # Scarves are bulky but light: wider throat, shallower upturn, longer reach.
    throat_k, lip_k, pitch_k, arm_k = 1.35, 0.55, 1.30, 0.85
elif target_part == "tie":
    # Ties are thin and numerous: narrow throat, tall lip so they cannot slide off.
    throat_k, lip_k, pitch_k, arm_k = 0.55, 1.15, 0.62, 0.75
else:
    # Belts: the throat must swallow a belt folded double at its buckle.
    throat_k, lip_k, pitch_k, arm_k = 1.00, 1.00, 1.00, 1.00

# Hook section: a rounded bar, always thick enough to carry a loaded belt.
arm_t   = max(4.0, min(spine_t * 0.72, 11.0)) * arm_k
arm_t   = max(3.6, arm_t)
arm_w   = max(6.0, min(spine_w * 0.62, 16.0))
# Throat: the vertical gap the strap drops into. A folded belt is roughly two thicknesses
# of leather plus the buckle bar, so the throat is sized from the strap width, not guessed.
throat  = max(8.0, min(strap_w * 0.55, 34.0)) * throat_k
throat  = max(7.0, throat)
# Lip: how far the hook's free end turns back up, expressed as the upturn's torus
# centreline radius. The clear opening between the arm's underside and the lip's tip
# is `2 * lip_rc - arm_t`, so solving for the throat we want gives the radius directly.
lip_rc  = ((throat + arm_t) / 2.0) * lip_k
lip_rc  = max(arm_t * 0.75, lip_rc)
pitch   = (throat + arm_t + max(10.0, strap_w * 0.30)) * pitch_k
pitch   = max(arm_t * 2.4 + 4.0, pitch)

# Spine length: room for every hook plus a head for the rod hook and a tail below.
head_h  = max(28.0, rod_dia * 0.9)
tail_h  = max(10.0, arm_t * 1.6)
spine_h = head_h + pitch * hook_count + tail_h

# Top rod hook, same technique as `garment-hanger`.
hook_wire = max(4.0, min(spine_t * 0.85, 9.0))
hook_ri   = rod_dia / 2.0 + 1.2
hook_rc   = hook_ri + hook_wire / 2.0


def _slab(length, width, thick, rad):
    """A rounded-rect slab lying in XY, centred at the origin, `thick` along Z."""
    r = max(0.4, min(rad, min(length, width) / 2.0 - 0.3))
    return (
        cq.Workplane("XY")
        .rect(length, width)
        .extrude(thick)
        .translate((0, 0, -thick / 2.0))
        .edges("|Z")
        .fillet(r)
    )


def _curl(rc, wire_d):
    """A three-quarter arc of `cq.Solid.makeTorus`, wrapped in a Workplane.

    A swept arc path degenerates, and assembling several quadrants leaves the pieces
    meeting along a single tangent circle (a coincident surface, not an overlap). One
    oversized box cut on a whole torus avoids both: one cut, one solid.

    Result: a ring lying in the XZ plane, open at its +X/-Z quadrant.
    """
    tor = cq.Workplane(obj=cq.Solid.makeTorus(rc, wire_d / 2.0))
    tor = tor.rotate((0, 0, 0), (1, 0, 0), 90)
    big = rc * 2.0 + wire_d * 4.0 + 20.0
    opener = (
        cq.Workplane("XY")
        .box(big, big, big)
        .translate((big / 2.0, 0, -big / 2.0))
    )
    return tor.cut(opener)


def _half_torus_up(rc, wire_d):
    """The lower half of a torus ring — the upturned lip at a hook's free end.

    Keeping a HALF (not a quadrant) means the piece meets the straight arm across a
    full tube section rather than at a tangent line, so the union has real material.
    Lies in the XZ plane; the open ends point along +X and -X at z = 0.
    """
    tor = cq.Workplane(obj=cq.Solid.makeTorus(rc, wire_d / 2.0))
    tor = tor.rotate((0, 0, 0), (1, 0, 0), 90)
    big = rc * 2.0 + wire_d * 4.0 + 20.0
    return tor.cut(
        cq.Workplane("XY").box(big, big, big).translate((0, 0, big / 2.0))
    )


def _spine():
    """The vertical spine: a rounded slab standing in the XZ plane.

    Length runs along Z, width along Y, thickness along X (the spine's front face is
    the +X face, which is where the hooks grow from).
    """
    slab = _slab(spine_h, spine_w, spine_t, min(spine_w, spine_t) * 0.35)
    # _slab builds in XY with length along X; stand it up so length runs along Z.
    return slab.rotate((0, 0, 0), (0, 1, 0), 90)


def _hook(z):
    """One open J-hook at height `z`, growing forward from the spine's +X face.

    Three overlapping pieces: a root block buried in the spine, a forward arm, and a
    half-torus lip that turns the free end back up. Each overlaps its neighbour across
    a full section — no tangent contacts anywhere.
    """
    # Root: a block straddling the spine's front face so the arm is never merely
    # butted against a flat wall.
    root = (
        cq.Workplane("XY")
        .box(spine_t * 1.1, arm_w, arm_t)
        .translate((spine_t * 0.25, 0, z))
    )
    # Arm: reaches forward along +X, starting inside the root block so the two overlap.
    # It stops short of the full reach — the lip's own radius makes up the rest.
    arm_x0 = 0.0
    arm_len = max(arm_t * 1.2, hook_reach - lip_rc)
    arm = (
        cq.Workplane("XY")
        .box(arm_len, arm_w, arm_t)
        .translate((arm_x0 + arm_len / 2.0, 0, z))
    )
    arm_end_x = arm_x0 + arm_len

    # Lip: a lower-half torus ring already lying in the XZ plane. Its ring centre goes
    # `lip_rc` past the arm end MINUS a bite, so the ring's -X open section is seated
    # INSIDE the arm rather than butted flat against it.
    lip = _half_torus_up(lip_rc, arm_t)
    lip = lip.translate((arm_end_x - arm_t * 0.35 + lip_rc, 0, z))

    return root.union(arm).union(lip)


def _rod_hook():
    """The top rod hook: stem plus a three-quarter curl, returned as pieces.

    Returned unfused because OCCT's fuse is order-sensitive on this composition —
    `spine.union(stem).union(curl)` comes out watertight while
    `spine.union(stem.union(curl))` does not (the same trap the `garment-hanger`
    cartridge documents).
    """
    r = hook_wire / 2.0
    z_top = spine_h / 2.0
    z0 = z_top - hook_wire * 1.5          # bury the stem root inside the spine
    stem_len = max(hook_rc * 1.2, 16.0)
    z_curl = z0 + stem_len
    # `bite` shifts the curl inboard so the stem lands inside real torus material.
    # A shallow bite leaves a thin lens of overlap whose fusion is fragile — at
    # bite = 0.8 * r the curl detached outright — so the stem carries a short FATTER
    # collar at the junction instead. The collar guarantees a fat overlap for any
    # combination of wire diameter and rod diameter, which the bite alone did not.
    bite = r * 0.35
    cx = hook_rc - bite
    stem = (
        cq.Workplane("XY")
        .circle(r)
        .extrude(stem_len + r * 1.2)
        .translate((0, 0, z0))
    )
    collar = (
        cq.Workplane("XY")
        .circle(r + bite * 1.4)
        .extrude(hook_wire * 1.6)
        .translate((0, 0, z_curl - hook_wire * 0.8))
    )
    curl = _curl(hook_rc, hook_wire).translate((cx, 0, z_curl))
    return stem.union(collar), curl


def build():
    """The whole rack: spine, rod hook, and the column of open hooks."""
    body = _spine()
    stem, curl = _rod_hook()
    body = body.union(stem).union(curl)
    z_first = spine_h / 2.0 - head_h
    for i in range(hook_count):
        z = z_first - (i + 0.5) * pitch
        body = body.union(_hook(z))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
# Mode ids and part ids match the manifest exactly — one part per mode, and the mode
# id IS the part id, so `target_part` also selects the proportion profile above:
#   belt  -> parts ["belt"]
#   scarf -> parts ["scarf"]
#   tie   -> parts ["tie"]
result = build()
