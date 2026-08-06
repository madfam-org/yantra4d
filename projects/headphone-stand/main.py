"""
Desk Headphone Stand — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A free-standing desk stand that holds a headset by its headband on a broad,
rounded cradle so the band does not develop a dent. This is the desktop, post-on-
a-base companion to the wall/under-desk Headphone Hook — here the headset hangs
from a saddle atop a weighted pillar rather than a wall bracket.

Three parts (dispatched by `target_part`):
  * "desk_stand"  — a single saddle on a post rising from a weighted disc base.
  * "dual_stand"  — a taller post with TWO saddles (front and back) for two
                    headsets on one footprint.
  * "clamp_stand" — a post whose base is a C-clamp that grips a desk edge instead
                    of a free base (saves desk space).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cradle_w`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "desk_stand"))  # desk|dual|clamp

cradle_w   = float(PARAM(lambda: cradle_w,   30.0))  # headband rest width (mm)
post_h     = float(PARAM(lambda: post_h,    260.0))  # post height (mm)
post_dia   = float(PARAM(lambda: post_dia,   26.0))  # post diameter (mm)
base_dia   = float(PARAM(lambda: base_dia,  120.0))  # base disc diameter (mm)
base_h     = float(PARAM(lambda: base_h,     14.0))  # base disc thickness (mm)
wall       = float(PARAM(lambda: wall,        4.0))  # shell wall thickness (mm)
desk_t     = float(PARAM(lambda: desk_t,     28.0))  # desk thickness for clamp (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
cradle_w = max(16.0, min(cradle_w, 60.0))
post_h   = max(120.0, min(post_h, 380.0))
post_dia = max(16.0, min(post_dia, 50.0))
base_dia = max(70.0, min(base_dia, 220.0))
base_h   = max(8.0, min(base_h, 30.0))
wall     = max(2.5, min(wall, 8.0))
desk_t   = max(10.0, min(desk_t, 60.0))

# Saddle radius: the half-round the headband rests in.
cradle_r = cradle_w * 0.6


# ── Helpers ──────────────────────────────────────────────────────────────────
def saddle(top_z, face_deg=0.0):
    """A broad rounded headband saddle whose base sits at z=top_z, mounted atop a
    post. A solid block with a horizontal half-round trough cut across the top so
    the headband rests on a gentle curve. `face_deg` rotates which way it faces.

    Overlaps the post below by `embed` so the boolean union is volumetric (a
    coincident face would leave a non-manifold seam)."""
    embed = 6.0
    block_w = cradle_w + 2.0 * wall + 6.0       # along the band (X before rotate)
    block_len = cradle_r * 2.0 + 2.0 * wall     # front-back reach (Y)
    block_h = cradle_r + wall
    base_z = top_z - embed

    block = (
        cq.Workplane("XY")
        .box(block_w, block_len, block_h + embed, centered=(True, True, False))
        .translate((0, 0, base_z))
    )
    # Trough: a cylinder lying along X (across the band), cut from the top.
    trough_top = base_z + block_h + embed
    trough = (
        cq.Workplane("YZ")
        .circle(cradle_r)
        .extrude(block_w + 2.0)
        .translate((-block_w / 2.0 - 1.0, 0, trough_top))
    )
    block = block.cut(trough)
    # Ease the two front/back lips so the band slides in.
    try:
        block = block.edges("|X and >Z").fillet(min(wall * 0.8, 2.5))
    except Exception:
        pass
    block = block.rotate((0, 0, 0), (0, 0, 1), face_deg)
    return block


def hollow_post(height, dia):
    """A SOLID vertical post from z=0 up. (Kept solid deliberately: an internal bore
    on a post that sits on a solid base top creates a trapped sealed void — unprintable
    and exported as a disconnected negative-volume mesh body. The base underside stays
    hollowed for material saving; the post is small enough to be solid.)"""
    return cq.Workplane("XY").circle(dia / 2.0).extrude(height)


# ── Part builders ────────────────────────────────────────────────────────────
def build_desk_stand():
    """A single saddle on a hollow post rising from a weighted disc base."""
    base = cq.Workplane("XY").circle(base_dia / 2.0).extrude(base_h)
    # Hollow the base underside to save plastic (leave a rim + floor).
    inner_r = base_dia / 2.0 - max(6.0, wall * 2.0)
    if inner_r > 6.0:
        cav = (
            cq.Workplane("XY")
            .circle(inner_r)
            .extrude(base_h - wall)
            .translate((0, 0, -0.01))
        )
        base = base.cut(cav)
    try:
        base = base.edges(">Z").fillet(min(3.0, base_h * 0.25))
    except Exception:
        pass

    post = hollow_post(post_h, post_dia).translate((0, 0, base_h))
    body = base.union(post)
    body = body.union(saddle(base_h + post_h))
    return body


def build_dual_stand():
    """A taller post carrying two saddles facing front and back."""
    base = cq.Workplane("XY").circle(base_dia / 2.0).extrude(base_h)
    inner_r = base_dia / 2.0 - max(6.0, wall * 2.0)
    if inner_r > 6.0:
        cav = (
            cq.Workplane("XY")
            .circle(inner_r)
            .extrude(base_h - wall)
            .translate((0, 0, -0.01))
        )
        base = base.cut(cav)
    try:
        base = base.edges(">Z").fillet(min(3.0, base_h * 0.25))
    except Exception:
        pass

    tall = post_h + cradle_r * 2.0 + 20.0
    post = hollow_post(tall, post_dia).translate((0, 0, base_h))
    body = base.union(post)
    # Lower saddle faces front (0°); upper saddle faces back (180°).
    lower_z = base_h + tall - (cradle_r * 2.0 + 40.0)
    body = body.union(saddle(lower_z, 0.0))
    body = body.union(saddle(base_h + tall, 180.0))
    return body


def build_clamp_stand():
    """A post whose base is a C-clamp gripping a desk edge (no free base)."""
    jaw = wall + 3.0
    depth = max(45.0, post_dia * 2.0)
    width = max(post_dia + 2.0 * wall, 40.0)
    total_h = desk_t + 2.0 * jaw

    # Solid C block, then cut the desk slot from +X leaving the back spine.
    outer = (
        cq.Workplane("XY")
        .box(depth, width, total_h, centered=(False, True, False))
    )
    slot = (
        cq.Workplane("XY")
        .box(depth, width + 2.0, desk_t, centered=(False, True, False))
        .translate((jaw, 0, jaw))
    )
    body = outer.cut(slot)
    # Lead-in chamfers at the slot mouth (boolean cuts stay watertight).
    lead = min(3.0, jaw * 0.6)
    if lead > 0.2:
        wide = width + 4.0
        low = (
            cq.Workplane("XZ")
            .polyline([(0, 0), (lead, 0), (0, lead)]).close()
            .extrude(wide).translate((0, wide / 2.0, jaw))
        )
        high = (
            cq.Workplane("XZ")
            .polyline([(0, 0), (lead, 0), (0, -lead)]).close()
            .extrude(wide).translate((0, wide / 2.0, jaw + desk_t))
        )
        body = body.cut(low).cut(high)

    # Post rising from the back-top of the clamp, with the saddle on top.
    post = hollow_post(post_h, post_dia).translate((depth - post_dia / 2.0 - wall, 0, total_h))
    body = body.union(post)
    body = body.union(
        saddle(total_h + post_h).translate((depth - post_dia / 2.0 - wall, 0, 0))
    )
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "dual_stand":
    result = build_dual_stand()
elif target_part == "clamp_stand":
    result = build_clamp_stand()
else:
    result = build_desk_stand()
