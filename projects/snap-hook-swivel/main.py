"""Snap Hook with Swivel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The bolt-snap that clips a bag strap to its D-ring, a lanyard to a key ring, or a lead to
a collar — with a swivel eye behind it so the strap never winds itself into a twist. The
gate is a compliant flexure: a slim arm moulded into the hook body that sweeps open under
a thumb and springs back closed, so nothing loose is needed. This is the rigid hard good
the Fashion Cabinet `snap-hook-swivel` notion places and bridges to here for its geometry.

Modes (dispatched via `target_part`):
  * "set"   — hook and swivel eye laid out side by side on one plate.
  * "hook"  — the hook body, compliant gate flexure, and the swivel post it pivots on.
  * "eye"   — the swivel eye: a webbing loop plate with a bore that drops over the post
              and is retained by the post's head.

Geometry: the hook throat is a trimmed `cq.Solid.makeTorus` (wrapped in
`cq.Workplane(obj=...)`) — never a swept radiusArc, which degenerates. The gate is a
straight flexure bar with a generous root land and a flat-topped lofted nose, so no knife
edge exists anywhere on the spring. The swivel post is a plain cylinder with a lofted
retaining head (a frustum, never a sphere cap). Every union overlaps; every cutter
overshoots both faces; the eye's webbing slot is the flange edge the tape threads over.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `webbing_w`).
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
webbing_w  = float(PARAM(lambda: webbing_w,  25.0))  # nominal webbing width (mm)
webbing_t  = float(PARAM(lambda: webbing_t,  1.6))   # webbing thickness (mm)
hook_r     = float(PARAM(lambda: hook_r,     9.0))   # hook throat inner radius (mm)
stock_d    = float(PARAM(lambda: stock_d,    5.0))   # hook stock (rod) diameter (mm)
gate_t     = float(PARAM(lambda: gate_t,     1.6))   # compliant gate flexure thickness
swivel_d   = float(PARAM(lambda: swivel_d,   5.0))   # swivel post diameter (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|hook|eye

# ── Safe clamps ──────────────────────────────────────────────────────────────
webbing_w  = max(10.0, min(webbing_w, 50.0))
webbing_t  = max(0.8, min(webbing_t, 4.0))
hook_r     = max(5.0, min(hook_r, 20.0))
stock_d    = max(3.0, min(stock_d, 9.0))
gate_t     = max(1.0, min(gate_t, 3.0))
swivel_d   = max(3.0, min(swivel_d, 9.0))

# ── Derived geometry ─────────────────────────────────────────────────────────
throat_rc  = hook_r + stock_d / 2.0                 # torus centreline radius
gate_len   = throat_rc * 1.55                       # flexure free length (mm)
gate_w     = max(stock_d * 0.8, 3.0)                # flexure width across (Y)
post_clear = 0.4                                    # swivel running clearance (mm)
post_len   = max(stock_d * 0.9, 3.5)                # post shank length (mm)
head_h     = max(1.2, swivel_d * 0.30)              # retaining head height (mm)
head_d     = swivel_d + max(1.6, swivel_d * 0.40)   # retaining head diameter (mm)
neck_len   = max(stock_d * 1.1, 5.0)                # hook-to-post neck length (mm)

# Swivel eye plate: a webbing loop with a bore at one end.
eye_slot_x = max(webbing_t * 2.0 + 1.2, 3.0)        # tape slot opening along the pull
eye_slot_y = webbing_w + 1.0                        # tape slot span across the tape
eye_t      = max(stock_d * 0.65, 3.0)               # plate thickness (Z)
eye_wall   = max(2.0, stock_d * 0.45)               # plate rail thickness
eye_bore_d = swivel_d + post_clear
eye_boss_d = eye_bore_d + 2.0 * eye_wall
eye_len    = eye_boss_d / 2.0 + eye_slot_x + 2.0 * eye_wall + 4.0


def _hook_arc():
    """The open C of the hook: a trimmed torus, cut back to ~three quarters."""
    torus = cq.Workplane(obj=cq.Solid.makeTorus(throat_rc, stock_d / 2.0))
    # makeTorus lies in XY with its axis on Z; roll it so the C opens in the XZ plane.
    torus = torus.rotate((0, 0, 0), (1, 0, 0), 90)
    big = throat_rc + stock_d + 6.0
    # Remove the +X/+Z quadrant to open the throat.
    cutter = (
        cq.Workplane("XY")
        .box(big, big * 2.0, big)
        .translate((big / 2.0, 0.0, big / 2.0))
    )
    return torus.cut(cutter)


def build_hook():
    """C-arc + neck + swivel post with retaining head + the compliant gate flexure."""
    body = _hook_arc()

    # Neck: a rod running up from the top of the C toward the swivel post, overlapping
    # the arc by a full stock diameter so the union has real material, not a tangent.
    neck = (
        cq.Workplane("XY")
        .circle(stock_d / 2.0)
        .extrude(neck_len + stock_d)
        .translate((-throat_rc, 0.0, -stock_d / 2.0))
    )
    body = body.union(neck)

    z_post = neck_len + stock_d / 2.0
    # Swivel post: plain shank, then a lofted frustum head (never a sphere cap).
    post = (
        cq.Workplane("XY")
        .circle(swivel_d / 2.0)
        .extrude(post_len + 1.0)
        .translate((-throat_rc, 0.0, z_post - 1.0))
    )
    head = (
        cq.Workplane("XY")
        .workplane(offset=z_post + post_len)
        .circle(swivel_d / 2.0)
        .workplane(offset=head_h)
        .circle(head_d / 2.0)
        .loft(ruled=True)
        .translate((-throat_rc, 0.0, 0.0))
    )
    # Flat cap over the head so the top face is a real face, not a lofted point.
    cap = (
        cq.Workplane("XY")
        .circle(head_d / 2.0)
        .extrude(max(0.8, head_h * 0.45))
        .translate((-throat_rc, 0.0, z_post + post_len + head_h - 0.2))
    )
    body = body.union(post).union(head).union(cap)

    # Compliant gate: a slim bar rooted at the top of the C and sweeping down across the
    # throat mouth. Its root is fattened into a land so the spring never starts at a
    # knife edge; the free nose is a flat-topped loft, never a point.
    root_x = -throat_rc + stock_d * 0.3
    root_z = 0.0
    land = (
        cq.Workplane("XY")
        .box(stock_d * 1.4, gate_w + 1.2, gate_t * 2.2)
        .translate((root_x, 0.0, root_z))
    )
    arm = (
        cq.Workplane("XY")
        .box(gate_len, gate_w, gate_t)
        .translate((root_x + gate_len / 2.0 - stock_d * 0.3, 0.0, root_z))
    )
    nose_x = root_x + gate_len - stock_d * 0.3
    nose = (
        cq.Workplane("YZ")
        .workplane(offset=nose_x - 0.4)
        .rect(gate_w, gate_t)
        .workplane(offset=max(1.6, stock_d * 0.5))
        .rect(gate_w * 0.55, max(0.8, gate_t * 0.6))
        .loft(ruled=True)
        .translate((0.0, 0.0, root_z))
    )
    return body.union(land).union(arm).union(nose)


def build_eye():
    """Swivel eye: a bored boss at one end, a webbing loop slot at the other."""
    # Plate outline: a rounded slab running +X from the boss toward the tape slot.
    plate_w = max(eye_boss_d, eye_slot_y + 2.0 * eye_wall)
    body = (
        cq.Workplane("XY")
        .rect(eye_len, plate_w)
        .extrude(eye_t)
        .edges("|Z")
        .fillet(min(eye_wall, plate_w / 2.0 - 0.3, eye_len / 2.0 - 0.3))
        .translate((eye_len / 2.0 - eye_boss_d / 2.0, 0.0, 0.0))
    )
    # Break the rim on the clean blank, before any hole exists.
    try:
        body = body.edges("#Z").chamfer(min(0.5, eye_t * 0.18, eye_wall * 0.25))
    except Exception:
        pass

    # Swivel bore, straight through both faces with overshoot.
    bore = (
        cq.Workplane("XY")
        .circle(eye_bore_d / 2.0)
        .extrude(eye_t + 8.0)
        .translate((0.0, 0.0, -4.0))
    )
    body = body.cut(bore)

    # Webbing slot: the flange edge the tape loops through, cut clean across.
    slot_cx = eye_len - eye_boss_d / 2.0 - eye_wall - eye_slot_x / 2.0
    slot = (
        cq.Workplane("XY")
        .box(eye_slot_x, eye_slot_y, eye_t + 8.0)
        .translate((slot_cx, 0.0, eye_t / 2.0))
    )
    return body.cut(slot)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "hook":
    result = build_hook()
elif target_part == "eye":
    result = build_eye()
else:
    gap = max(6.0, stock_d * 1.6)
    # The hook is modelled standing up in XZ; roll it flat onto the bed for printing.
    hook = build_hook().rotate((0, 0, 0), (1, 0, 0), 90)
    span = max(eye_len, throat_rc * 2.0 + stock_d) / 2.0
    hook = hook.translate((0.0, span + gap / 2.0, stock_d / 2.0))
    eye = build_eye().translate((-eye_len * 0.35, -(span + gap / 2.0), 0.0))
    result = cq.Workplane("XY").add(hook).add(eye)
