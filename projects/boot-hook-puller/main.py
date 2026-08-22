"""Boot Hook Puller — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The boot-pull: a T-handle on a flat blade that ends in a hook, which grabs the sewn fabric
loop inside a boot shaft so the boot can be hauled on. Tall boots — riding boots, western
boots, work boots, waders — have that loop precisely because you cannot get them on by hand,
and the puller is the tool that makes the loop usable. A pair of them lets you pull both
boots at once, standing.

Modes (dispatched via `target_part`):
  * "puller"     — one T-handle puller.
  * "puller_pair" — the pair, laid out on a plate; two boots need two hands.
  * "wide_hook"  — one puller with a wider, flatter hook throat for a heavy strap loop
                   (work boots and waders use webbing, not a thin cord).

Geometry: the blade is a rounded-rect slab; the handle is a cylinder crossing the blade top
with GENEROUS overlap into the blade (the handle root is where a puller actually breaks, so
the union is deliberately deep, not tangent). The hook is a `cq.Solid.makeTorus` quarter —
never a swept radiusArc, which degenerates — wrapped in cq.Workplane(obj=...), trimmed with
oversized box cuts, and unioned into the blade tip with real overlap. One piece throughout.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `blade_len`).
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
blade_len   = float(PARAM(lambda: blade_len,   160.0))  # blade length, handle to hook (mm)
blade_w     = float(PARAM(lambda: blade_w,     20.0))   # blade width (mm)
blade_t     = float(PARAM(lambda: blade_t,     5.0))    # blade thickness (mm)
handle_len  = float(PARAM(lambda: handle_len,  95.0))   # T-handle length (mm)
handle_dia  = float(PARAM(lambda: handle_dia,  22.0))   # T-handle diameter (mm)
hook_r      = float(PARAM(lambda: hook_r,      11.0))   # hook throat radius (mm)
hook_d      = float(PARAM(lambda: hook_d,      6.0))    # hook rod diameter (mm)
overlap_f   = float(PARAM(lambda: overlap_f,   0.55))   # handle-into-blade overlap fraction

target_part = str(PARAM(lambda: target_part, "puller"))  # puller|puller_pair|wide_hook

# ── Safe clamps ──────────────────────────────────────────────────────────────
blade_len  = max(70.0, min(blade_len, 400.0))
blade_w    = max(10.0, min(blade_w, 45.0))
blade_t    = max(3.0, min(blade_t, 12.0))
handle_len = max(50.0, min(handle_len, 180.0))
handle_dia = max(12.0, min(handle_dia, 40.0))
hook_d     = max(2.4, min(hook_d, min(blade_t * 1.6, 14.0)))
# The hook rod must never be exactly as thick as the blade: a rod whose diameter equals
# blade_t sits TANGENT to the blade's flat side faces, and a tangent union is not
# watertight (observed as broken faces at y = ±blade_t/2). Bias it strictly off tangency.
if abs(hook_d - blade_t) < 0.35:
    hook_d = blade_t - 0.4 if blade_t > 3.0 else blade_t + 0.5
hook_d     = max(2.0, hook_d)
# The throat must clear the rod that forms it, or the hook closes on itself.
hook_r     = max(hook_d * 0.8, min(hook_r, 30.0))
overlap_f  = max(0.25, min(overlap_f, 0.9))

# Handle root overlap: how deep the handle cylinder sinks into the blade. This is the
# stress path — a shallow union is exactly how a printed puller snaps in use.
root_over = handle_dia * overlap_f

# The blade runs along +Z from the handle (at Z=0) up to the hook.
blade_top = blade_len


def _blade():
    """Rounded-rect blade standing along Z, centred on X, flat in Y."""
    return (
        cq.Workplane("XY")
        .rect(blade_w, blade_t)
        .extrude(blade_top)
        .edges("|Z")
        .fillet(min(blade_t / 2.5, blade_w / 4.0, 2.0))
    )


def _handle():
    """T-handle: a cylinder crossing the blade along X, sunk deep into the blade root."""
    return (
        cq.Workplane("YZ")
        .circle(handle_dia / 2.0)
        .extrude(handle_len)
        .translate((-handle_len / 2.0, 0.0, root_over * 0.5))
        .edges("%CIRCLE")
        .fillet(min(handle_dia * 0.2, 3.0))
    )


def _hook(throat_r, rod_d):
    """A quarter torus hooking the boot loop — makeTorus, never a swept radiusArc.

    cq.Solid.makeTorus returns a cq.Solid, so it is wrapped in cq.Workplane(obj=...).
    Trimmed to a quarter with oversized box cuts that overshoot every face.
    """
    centre_r = throat_r + rod_d / 2.0
    torus = cq.Workplane(obj=cq.Solid.makeTorus(centre_r, rod_d / 2.0))
    # The torus lies in XY about Z. Rotate its axis onto Y so the hook curls in the
    # blade's own plane (XZ) — the direction a boot loop is pulled.
    torus = torus.rotate((0, 0, 0), (1, 0, 0), 90)
    big = centre_r + rod_d + 8.0
    # Keep the +X / +Z quarter: cut away everything at X < 0 and everything at Z < 0.
    cut_x = (
        cq.Workplane("XY")
        .box(big * 2.0, big * 2.0, big * 2.0)
        .translate((-big, 0.0, 0.0))
    )
    cut_z = (
        cq.Workplane("XY")
        .box(big * 2.0, big * 2.0, big * 2.0)
        .translate((0.0, 0.0, -big))
    )
    quarter = torus.cut(cut_x).cut(cut_z)
    # A stub down the +Z arm so the quarter meets the blade with real overlap rather
    # than a tangent touch at a single circle.
    stub = (
        cq.Workplane("XY")
        .circle(rod_d / 2.0)
        .extrude(rod_d * 1.6)
        .translate((centre_r, 0.0, -rod_d * 1.4))
    )
    return quarter.union(stub)


def build_puller(throat_r):
    """Blade + deeply-rooted T-handle + hook at the blade tip. One piece."""
    body = _blade().union(_handle())
    # Hook, placed so its downward arm sinks into the blade top with real overlap.
    hook = _hook(throat_r, hook_d).translate(
        (-(throat_r + hook_d / 2.0), 0.0, blade_top - hook_d * 0.9)
    )
    return body.union(hook)


def _compound(solids):
    """Separate bodies on one plate — a Compound, never a union of non-touching solids."""
    shapes = []
    for s in solids:
        shapes.extend(s.vals())
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wide_hook":
    # A wider, flatter throat for a webbing strap loop rather than a thin cord, on a
    # beefier rod — a strap loop carries more load across more stitching than a cord does.
    hook_d = min(hook_d * 1.45, blade_t * 1.6, 14.0)
    if abs(hook_d - blade_t) < 0.35:
        hook_d = blade_t - 0.4 if blade_t > 3.0 else blade_t + 0.5
    result = build_puller(max(hook_r * 1.7, hook_d * 2.2))
elif target_part == "puller_pair":
    _gap = handle_dia + max(6.0, handle_dia * 0.4)
    result = _compound([
        build_puller(hook_r).translate((0.0, -_gap / 2.0, 0.0)),
        build_puller(hook_r).translate((0.0, _gap / 2.0, 0.0)),
    ])
else:
    result = build_puller(hook_r)
