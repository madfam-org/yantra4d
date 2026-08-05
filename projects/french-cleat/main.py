"""
Modular Wall Hook Rail / French Cleat — Yantra4D Hyperobject Cartridge (CadQuery).

The catalog capstone: a 45° French-cleat shop-wall system. A wall-mounted cleat
strip screws to the wall; accessory backs carry the COMPLEMENTARY 45° cleat and hang
on it, so the whole wall becomes reconfigurable storage.

Three parts (dispatched via `target_part`):
  * "wall_cleat" — the 45° strip that screws to the wall, with mounting screw holes.
  * "hook_back"  — an accessory with the mating 45° cleat on its back + a hook out front.
  * "bin_back"   — a small open bin with the mating 45° cleat on its back.

Geometry model (vertical section; X = distance out from the wall, Z = up):
  * The WALL cleat's front-top edge is cut at `angle` (default 45°), leaving a ramp
    that faces up-and-away from the wall. The wall face (X=0) is flat.
  * The ACCESSORY cleat is the COMPLEMENT: its back-bottom is cut at the same angle so
    its lip drops over the wall ramp. Wall-ramp and accessory-lip are parallel 45°
    planes — they mate. A small `fit` gap keeps it printable and easy to hang.

No threads — a rail/wedge interface, so every render is fast.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `angle`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "wall_cleat"))  # wall_cleat|hook_back|bin_back
accessory   = str(PARAM(lambda: accessory,    "hook"))        # hook|bin|tool_holder|shelf

angle       = float(PARAM(lambda: angle,      45.0))   # cleat bevel angle (deg)
cleat_h     = float(PARAM(lambda: cleat_h,    30.0))   # cleat height (Z) of the wedge band
cleat_depth = float(PARAM(lambda: cleat_depth, 14.0))  # cleat depth (X) out from the wall
strip_len   = float(PARAM(lambda: strip_len, 120.0))   # wall-cleat length (Y)
screw_dia   = float(PARAM(lambda: screw_dia,   4.5))   # wall screw clearance dia (mm)
screw_count = int(  PARAM(lambda: screw_count,   2))   # wall-cleat mounting screws
back_w      = float(PARAM(lambda: back_w,     70.0))   # accessory back width (Y)
wall        = float(PARAM(lambda: wall,        4.0))   # accessory / cleat wall thickness
fit         = float(PARAM(lambda: fit,         0.4))   # hang clearance between cleats
tool_dia    = float(PARAM(lambda: tool_dia,   25.0))   # tool_holder hole diameter (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
angle       = max(30.0, min(angle, 60.0))
cleat_h     = max(15.0, min(cleat_h, 60.0))
cleat_depth = max(8.0, min(cleat_depth, 30.0))
strip_len   = max(40.0, min(strip_len, 400.0))
screw_dia   = max(0.0, min(screw_dia, 10.0))
screw_count = max(0, min(screw_count, 12))
back_w      = max(30.0, min(back_w, 200.0))
wall        = max(2.5, min(wall, 10.0))
fit         = max(0.0, min(fit, 1.5))
tool_dia    = max(4.0, min(tool_dia, 80.0))


# ── Cleat cross-sections (inlined; exact `angle` math — no repo imports) ──────
def cleat_ramp_geometry(depth, height, ang):
    """Return (run, rise, ramp_z) for a cleat ramp at EXACTLY `ang` degrees.

    The ramp rises by `rise` over a horizontal `run = rise / tan(ang)`. The rise is
    driven by the ramp starting at `ramp_z` (mid-height) and reaching the top, then
    clamped so `run` fits within `depth` — clamping the RISE (not the run) keeps the
    angle exact. Both the wall cleat and the accessory use this same geometry, so
    their mating faces are guaranteed parallel at `ang`."""
    rad = math.radians(ang)
    tan = math.tan(rad)
    rise = height * 0.5
    run = rise / tan
    max_run = depth - 2.0                        # keep ≥2 mm flat ledge at the top-back
    if run > max_run:
        run = max_run
        rise = run * tan                         # shrink rise to preserve the exact angle
    ramp_z = height - rise                        # ramp starts here, tops out at `height`
    return run, rise, ramp_z


def wall_cleat_profile(depth, height, ang):
    """WALL cleat vertical section in the XZ plane (X out from wall, Z up), base at
    z=0, wall face at x=0. The front-top edge is a ramp at exactly `ang`, facing
    up-and-away from the wall; the accessory lip drops onto it."""
    run, rise, ramp_z = cleat_ramp_geometry(depth, height, ang)
    top_x = depth - run
    return (
        cq.Workplane("XZ")
        .polyline([
            (0.0, 0.0),
            (depth, 0.0),
            (depth, ramp_z),                     # vertical front up to the ramp start
            (top_x, height),                     # ramp up-and-back at `ang`
            (0.0, height),                       # flat top-back to the wall
        ])
        .close()
    )


def accessory_cleat_profile(depth, height, ang, gap):
    """ACCESSORY cleat vertical section (XZ) — the COMPLEMENT of the wall cleat: its
    lip underside is the same `ang` plane, shifted up by `gap` for a printable hang
    fit, so it drops over the wall ramp. X is measured out from the accessory's back
    plane (which sits against the wall cleat)."""
    run, rise, ramp_z = cleat_ramp_geometry(depth, height, ang)
    ramp_x = depth - run
    return (
        cq.Workplane("XZ")
        .polyline([
            (0.0, 0.0),
            (ramp_x, 0.0),
            (depth, ramp_z + gap),               # lip underside at `ang` (parallel to wall ramp)
            (depth, height),                     # front face up to the top
            (0.0, height),                       # back-top to the accessory back
        ])
        .close()
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_wall_cleat():
    """The wall strip: the cleat cross-section extruded along Y (`strip_len`) plus
    mounting screw holes drilled through the flat back band."""
    cleat = (
        wall_cleat_profile(cleat_depth, cleat_h, angle)
        .extrude(strip_len)
        .translate((0, -strip_len / 2.0, 0))
    )
    # A thicker lower band would over-build; the trapezoid already gives a solid strip.
    body = cleat
    # Screw holes: horizontal bores through the wall band (along +X into the wall),
    # placed low where the section is full depth.
    if screw_dia > 0.05 and screw_count > 0:
        r = screw_dia / 2.0
        if screw_count == 1:
            ys = [0.0]
        else:
            span = strip_len - 2.0 * max(8.0, screw_dia * 2.0)
            span = max(0.0, span)
            step = span / (screw_count - 1)
            ys = [-span / 2.0 + i * step for i in range(screw_count)]
        for y in ys:
            bore = (
                cq.Workplane("XZ")
                .circle(r)
                .extrude(cleat_depth + 2.0)
                .translate((-1.0, y, cleat_h * 0.22))
            )
            body = body.cut(bore)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _accessory_back(depth, height, width):
    """The accessory's mating cleat back: the complement cross-section extruded along
    Y (`width`), returned centred in Y with its back plane at x=0."""
    back = (
        accessory_cleat_profile(depth, height, angle, fit)
        .extrude(width)
        .translate((0, -width / 2.0, 0))
    )
    return back


def build_hook_back():
    """An accessory back with the mating 45° cleat + a hook projecting out front."""
    depth = cleat_depth
    height = cleat_h + wall * 2.0
    back = _accessory_back(depth, height, back_w)

    # Front bodies start a couple mm INSIDE the back so the union is a volumetric fuse
    # (a face-to-face tangent kiss tessellates non-watertight).
    front_x = depth - 2.0
    hook_out = 45.0
    hook_up = 22.0
    arm = (
        cq.Workplane("XY")
        .box(hook_out, min(back_w * 0.5, 30.0), wall, centered=(True, True, False))
        .translate((front_x + hook_out / 2.0, 0.0, wall))
    )
    tip = (
        cq.Workplane("XY")
        .box(wall, min(back_w * 0.5, 30.0), hook_up, centered=(True, True, False))
        .translate((front_x + hook_out - wall / 2.0, 0.0, wall))
    )
    body = back.union(arm).union(tip)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_bin_back():
    """A small open bin with the mating 45° cleat on its back."""
    depth = cleat_depth
    height = cleat_h + wall * 2.0
    back = _accessory_back(depth, height, back_w)

    # Bin: an open box projecting from the front face. Start it a couple mm INSIDE the
    # back so the union is a volumetric fuse (not a non-watertight tangent kiss).
    bin_out = 55.0
    bin_h = 45.0
    join = 2.0
    front_x = depth - join
    outer = (
        cq.Workplane("XY")
        .box(bin_out, back_w, bin_h, centered=(True, True, False))
        .translate((front_x + bin_out / 2.0, 0.0, 0.0))
    )
    # Inner cavity: opens at the top (extends above the rim) and stops short of the
    # back+join wall so the bin's back panel stays solid.
    inner = (
        cq.Workplane("XY")
        .box(bin_out - 2.0 * wall, back_w - 2.0 * wall, bin_h + 2.0, centered=(True, True, False))
        .translate((front_x + join + bin_out / 2.0, 0.0, wall))
    )
    binbody = outer.cut(inner)
    if accessory == "tool_holder":
        # Replace the bin with a plate carrying a tool hole of `tool_dia`.
        plate = (
            cq.Workplane("XY")
            .box(max(bin_out, tool_dia + 2.0 * wall), back_w, wall, centered=(True, True, False))
            .translate((front_x + max(bin_out, tool_dia + 2.0 * wall) / 2.0, 0.0, 0.0))
        )
        hole = (
            cq.Workplane("XY")
            .circle(tool_dia / 2.0)
            .extrude(wall + 2.0)
            .translate((front_x + max(bin_out, tool_dia + 2.0 * wall) / 2.0, 0.0, -1.0))
        )
        binbody = plate.cut(hole)
    elif accessory == "shelf":
        binbody = (
            cq.Workplane("XY")
            .box(bin_out, back_w, wall, centered=(True, True, False))
            .translate((front_x + bin_out / 2.0, 0.0, 0.0))
        )
    body = back.union(binbody)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "hook_back":
    result = build_hook_back()
elif target_part == "bin_back":
    result = build_bin_back()
else:
    result = build_wall_cleat()
