"""Pattern Weight — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The tailor's pattern weight — the wide, low, heavy disc that pins a paper pattern to cloth
without a single pin hole, so slippery silks and knits get cut on the true grain. Cutting
rooms buy these by the dozen; this one prints in any size, stacks, and takes a finger recess
so it lifts off the table cleanly.

Modes (dispatched via `target_part`):
  * "weight" — one weight.
  * "stack"  — two weights registered nose-to-tail on the stacking boss.
  * "set"    — a four-weight tray layout for one plate.

Geometry: a low cylinder with a chamfered rim (chamfered on a CLEAN blank before any cut,
never after), a debossed finger recess in the top face, and — when stacking is on — a raised
registration boss on top matched by a socket cut in the underside. The socket opens
downward and the recess opens upward, so nothing is a sealed void.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `weight_dia`).
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
weight_dia  = float(PARAM(lambda: weight_dia,  62.0))  # outside diameter (mm)
weight_h    = float(PARAM(lambda: weight_h,    16.0))  # body height (mm)
rim_chamfer = float(PARAM(lambda: rim_chamfer, 2.0))   # chamfer at top and bottom rim (mm)
recess_dia  = float(PARAM(lambda: recess_dia,  26.0))  # finger recess diameter (mm)
recess_d    = float(PARAM(lambda: recess_d,    5.0))   # finger recess depth (mm)
boss_h      = float(PARAM(lambda: boss_h,      2.4))   # stacking registration boss height (mm)
stack_clear = float(PARAM(lambda: stack_clear, 0.3))   # socket clearance over the boss (mm)

target_part = str(PARAM(lambda: target_part, "weight"))  # weight|stack|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
weight_dia  = max(30.0, min(weight_dia, 120.0))
weight_h    = max(8.0, min(weight_h, 40.0))
rim_chamfer = max(0.0, min(rim_chamfer, min(weight_h / 3.0, 6.0)))
recess_dia  = max(10.0, min(recess_dia, weight_dia - 12.0))
recess_d    = max(1.0, min(recess_d, weight_h / 2.5))
boss_h      = max(0.0, min(boss_h, weight_h / 4.0))
stack_clear = max(0.1, min(stack_clear, 1.0))

BOSS_DIA = recess_dia + 8.0 if recess_dia + 8.0 < weight_dia - 6.0 else weight_dia - 6.0


def build_weight():
    """Chamfer a clean blank first, then cut the recess, boss ring, and stack socket."""
    body = cq.Workplane("XY").circle(weight_dia / 2.0).extrude(weight_h)
    if rim_chamfer > 0.01:
        try:
            body = body.edges("%CIRCLE").chamfer(rim_chamfer)
        except Exception:
            pass

    # Stacking boss: an annular land raised on top, formed by cutting a moat around it
    # rather than unioning a separate disc (no coplanar seam).
    if boss_h > 0.05:
        body = body.faces(">Z").workplane().circle(BOSS_DIA / 2.0 + boss_h).circle(
            weight_dia / 2.0 + 1.0).cutBlind(-boss_h)

    # Finger recess: a blind pocket in the top face — opens upward, drains.
    body = body.faces(">Z").workplane(centerOption="CenterOfBoundBox").circle(
        recess_dia / 2.0).cutBlind(-recess_d)

    # Stack socket: a shallow relief in the underside that swallows the boss below it.
    if boss_h > 0.05:
        sock = (
            cq.Workplane("XY")
            .circle(BOSS_DIA / 2.0 + boss_h + stack_clear)
            .extrude(boss_h + stack_clear)
            .translate((0, 0, -0.5))
        )
        body = body.cut(sock)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "stack":
    lift = weight_h - (boss_h + stack_clear) * 0.5
    result = build_weight().union(build_weight().translate((0, 0, lift)))
elif target_part == "set":
    p = weight_dia + 6.0
    result = build_weight().translate((-p / 2.0, -p / 2.0, 0))
    result = result.union(build_weight().translate((p / 2.0, -p / 2.0, 0)))
    result = result.union(build_weight().translate((-p / 2.0, p / 2.0, 0)))
    result = result.union(build_weight().translate((p / 2.0, p / 2.0, 0)))
else:
    result = build_weight()
