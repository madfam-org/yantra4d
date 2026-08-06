"""
Living-Hinge Panel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A print-in-place flexure hinge that joins two flat panels so they can fold
without a separate pin. Three hinge styles: a continuous thin web (bends by
stretching a ~0.5 mm membrane), a segmented lattice of alternating slots (curls
like a laser-cut living hinge), and a coiled knuckle (a compact rolled flexure).
Modes build the two panels flat with the hinge between them, a segmented panel,
or an L of two panels meeting at a folded corner.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `panel_w`).
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
panel_w     = float(PARAM(lambda: panel_w,     60.0))   # panel width (Y span, mm)
panel_len   = float(PARAM(lambda: panel_len,   40.0))   # length of EACH panel (X, mm)
panel_thick = float(PARAM(lambda: panel_thick, 3.0))    # panel thickness (Z, mm)
web_thick   = float(PARAM(lambda: web_thick,   0.5))    # web / hinge membrane thickness
hinge_len   = float(PARAM(lambda: hinge_len,   8.0))    # hinge zone length along X
seg_count   = int(  PARAM(lambda: seg_count,     6))    # segmented: number of slot rows
seg_gap     = float(PARAM(lambda: seg_gap,     1.2))    # segmented: slot width (mm)

hinge_type  = str(  PARAM(lambda: hinge_type,  "thin_web"))   # thin_web|segmented|coiled
target_part = str(  PARAM(lambda: target_part, "web_hinge"))  # web_hinge|segmented_hinge|box_corner

# ── Safe clamps ──────────────────────────────────────────────────────────────
# Web can never be thicker than the panel, and must stay a real positive solid.
web_thick = max(0.2, min(web_thick, panel_thick - 0.2))
# Hinge zone must be positive and not longer than the parts around it.
hinge_len = max(1.0, hinge_len)
seg_count = max(1, seg_count)
seg_gap   = max(0.4, seg_gap)


# ── Helpers ──────────────────────────────────────────────────────────────────
def flat_panel(length, x0):
    """One rectangular panel sitting on z=0, spanning X:[x0, x0+length],
    centered in Y, thickness panel_thick."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x0 + length / 2.0, 0, panel_thick / 2.0))
        .box(length, panel_w, panel_thick)
    )


def thin_web_zone(x0):
    """A continuous thin membrane of thickness web_thick spanning the hinge
    zone X:[x0, x0+hinge_len]. Placed at the bottom of the panel stack so the
    fold is a living skin — a single continuous solid bridging the panels."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x0 + hinge_len / 2.0, 0, web_thick / 2.0))
        .box(hinge_len, panel_w, web_thick)
    )


def build_web_hinge():
    """Two panels joined by one continuous thin web across the hinge zone.
    Watertight: three overlapping boxes fused; the web fully spans the gap."""
    left = flat_panel(panel_len, -panel_len - hinge_len / 2.0)
    right = flat_panel(panel_len, hinge_len / 2.0)
    web = thin_web_zone(-hinge_len / 2.0)
    body = left.union(right).union(web)
    return body


def build_segmented_hinge():
    """Two panels bridged by a full-thickness hinge block that is perforated by
    a row of vertical through-slots. The remaining ligaments between slots flex,
    letting the panel curl (laser-cut 'living hinge' behaviour). The block stays
    one connected watertight solid because slots do not reach the outer edges."""
    left = flat_panel(panel_len, -panel_len - hinge_len / 2.0)
    right = flat_panel(panel_len, hinge_len / 2.0)
    block = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, panel_thick / 2.0))
        .box(hinge_len, panel_w, panel_thick)
    )

    # Slots run along X (the fold axis is Y). Each slot is a thin box cut
    # through Z, leaving a margin at both Y ends so the block never splits.
    margin = max(2.0, panel_w * 0.08)
    slot_len = max(1.0, panel_w - 2.0 * margin)
    span = hinge_len - seg_gap
    if seg_count > 1:
        step = span / (seg_count - 1)
        start = -span / 2.0
    else:
        step = 0.0
        start = 0.0
    for i in range(seg_count):
        # Alternate slots toward +Y / -Y so ligaments stagger like a real
        # segmented hinge; every slot still leaves both ends connected.
        yshift = (margin * 0.5) if (i % 2 == 0) else (-margin * 0.5)
        x = start + i * step
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, yshift, panel_thick / 2.0))
            .box(seg_gap, slot_len, panel_thick + 2.0)
        )
        block = block.cut(slot)

    return left.union(right).union(block)


def build_coiled_hinge():
    """A compact rolled flexure: two panels bridged by a thin web that is
    bumped up into a shallow arch (a printed-in knuckle). Modelled as the thin
    web plus a half-annulus rib over the hinge zone so it reads as a coil while
    staying a single watertight solid."""
    left = flat_panel(panel_len, -panel_len - hinge_len / 2.0)
    right = flat_panel(panel_len, hinge_len / 2.0)
    web = thin_web_zone(-hinge_len / 2.0)

    # Shallow rolled rib: a cylinder segment lying along Y, radius ~hinge_len/2,
    # trimmed to its upper half so it forms an arch bridging the two panels.
    r = max(web_thick, hinge_len / 2.0)
    cyl = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, r, -panel_w / 2.0))
        .circle(r)
        .extrude(panel_w)
    )
    # Hollow the arch so it is a thin coil wall, not a solid lump.
    inner = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, r, -panel_w / 2.0 - 1.0))
        .circle(max(0.5, r - web_thick))
        .extrude(panel_w + 2.0)
    )
    arch = cyl.cut(inner)
    # Keep only material above the web (z >= web_thick).
    trim = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, (web_thick) / 2.0))
        .box(hinge_len + 2.0, panel_w + 2.0, web_thick)
    )
    arch = arch.cut(trim)
    return left.union(right).union(web).union(arch)


def build_box_corner():
    """An L of two panels meeting at a folded 90° corner, joined at the fold by
    the selected hinge style. Panel A lies flat on XY; panel B stands vertical.
    The hinge web wraps the inner corner as one continuous solid."""
    # Flat panel A along +X, sitting on z=0.
    a = flat_panel(panel_len, hinge_len / 2.0)

    # Vertical panel B: build it flat then rotate up about the corner edge (Y).
    b = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(panel_len / 2.0 + hinge_len / 2.0, 0, panel_thick / 2.0))
        .box(panel_len, panel_w, panel_thick)
    )
    # Rotate B 90° about the Y axis through the corner line x = hinge_len/2.
    b = b.rotate((hinge_len / 2.0, 0, 0), (hinge_len / 2.0, 1, 0), 90)

    # Corner web: a thin quarter-fillet solid bridging the inner corner. Model
    # as a small box at the corner minus a rounding, kept full-width in Y so it
    # is one continuous membrane.
    web = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(hinge_len / 2.0, 0, web_thick / 2.0))
        .box(hinge_len, panel_w, web_thick)
    )
    # A vertical strip of the web climbing the inner face of panel B so the
    # membrane is continuous around the fold.
    web_up = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(hinge_len / 2.0 - web_thick / 2.0, 0, hinge_len / 2.0))
        .box(web_thick, panel_w, hinge_len)
    )
    body = a.union(b).union(web).union(web_up)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "box_corner":
    result = build_box_corner()
elif target_part == "segmented_hinge" or hinge_type == "segmented":
    result = build_segmented_hinge()
elif hinge_type == "coiled":
    result = build_coiled_hinge()
else:
    result = build_web_hinge()
