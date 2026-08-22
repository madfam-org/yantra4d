"""Point Turner — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The collar point turner and seam presser — one flat blade with a blunt point at one end for
pushing out collar, cuff, and lapel corners without bursting the stitching, and a broad
rounded paddle at the other for holding a seam open under the iron. The bamboo original is
a sewing-room staple; printed, it is one object a maker can size to their own hand and to
the corner angle their pattern actually has.

Modes (dispatched via `target_part`):
  * "turner" — the full tool: point end + presser end.
  * "point"  — the point end alone, a short pocket tool.
  * "set"    — turner and point tool laid out together.

Geometry: ONE planar outline (a symmetric polyline: rounded presser paddle → waisted grip →
tapered blade → blunt point) extruded to thickness, then chamfered along the outline so the
edges are slim enough to slip inside a seam without cutting the thread. The chamfer runs on
the clean extruded blank BEFORE the thumb-grip pocket is cut — chamfering after a cut is the
uncatchable OCCT crash. Prints flat, no supports.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `tool_len`).
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
tool_len    = float(PARAM(lambda: tool_len,    150.0))  # overall length (mm)
presser_w   = float(PARAM(lambda: presser_w,   34.0))   # presser paddle width (mm)
point_w     = float(PARAM(lambda: point_w,     3.0))    # blunt width at the point (mm)
tool_t      = float(PARAM(lambda: tool_t,      5.0))    # blade thickness (mm)
edge_bevel  = float(PARAM(lambda: edge_bevel,  1.4))    # bevel along the working edges (mm)
grip_pocket = float(PARAM(lambda: grip_pocket, 1.2))    # thumb-grip pocket depth (mm, 0 = none)

target_part = str(PARAM(lambda: target_part, "turner"))  # turner|point|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
tool_len    = max(70.0, min(tool_len, 260.0))
presser_w   = max(16.0, min(presser_w, 60.0))
point_w     = max(1.5, min(point_w, 8.0))
tool_t      = max(3.0, min(tool_t, 12.0))
edge_bevel  = max(0.0, min(edge_bevel, min(tool_t / 2.5, presser_w / 8.0)))
grip_pocket = max(0.0, min(grip_pocket, tool_t / 3.0))


def outline(length, wide):
    """Half-outline mirrored into a closed planar profile, from the presser end (y=0) to
    the blunt point (y=length). Straight segments only — arcs on a mirrored polyline are
    where these profiles usually go non-manifold."""
    wide = max(wide, point_w + 4.0)
    half = wide / 2.0
    waist = max(half * 0.52, point_w)          # the grip waist
    nose = point_w / 2.0
    # Key stations along the tool.
    y_paddle = length * 0.16                   # full-width paddle ends here
    y_waist = length * 0.42                    # narrowest grip
    y_blade = length * 0.74                    # blade starts its final taper
    pts = [
        (-nose * 0.9, 0.0),                    # the presser end is flat, slightly relieved
        (-half, length * 0.055),
        (-half, y_paddle),
        (-waist, y_waist),
        (-waist * 0.80, y_blade),
        (-nose, length),
        (nose, length),
        (waist * 0.80, y_blade),
        (waist, y_waist),
        (half, y_paddle),
        (half, length * 0.055),
        (nose * 0.9, 0.0),
    ]
    return pts


def build_turner(length, wide, with_pocket):
    """Extrude the outline, bevel the clean blank, then cut the grip pockets."""
    blade = cq.Workplane("XY").polyline(outline(length, wide)).close().extrude(tool_t)

    # Bevel the working edges on the CLEAN blank — never after the pocket cut.
    if edge_bevel > 0.02:
        try:
            blade = blade.edges("|Z").chamfer(edge_bevel)
        except Exception:
            pass

    if with_pocket and grip_pocket > 0.02:
        # Two shallow thumb dishes at the waist, one per face, so the tool is reversible.
        waist_y = length * 0.42
        dish_r = max(min(wide * 0.22, length * 0.06), 3.0)
        # Each cutter is `grip_pocket` deep in the blade and overshoots 1 mm out of the
        # face, so the pocket is unambiguously open — no sealed void, no coplanar kiss.
        for z_bottom in (tool_t - grip_pocket, -1.0):
            dish = (
                cq.Workplane("XY")
                .circle(dish_r)
                .extrude(grip_pocket + 1.0)
                .translate((0, waist_y, z_bottom))
            )
            blade = blade.cut(dish)
    return blade


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "point":
    result = build_turner(tool_len * 0.55, presser_w * 0.62, False)
elif target_part == "set":
    # Two genuinely separate tools — a COMPOUND, not .union() of non-touching solids.
    big = build_turner(tool_len, presser_w, True).translate((-presser_w * 0.75, 0, 0))
    small = build_turner(tool_len * 0.55, presser_w * 0.62, False).translate(
        (presser_w * 0.75, 0, 0))
    result = cq.Workplane(obj=cq.Compound.makeCompound(
        big.solids().vals() + small.solids().vals()))
else:
    result = build_turner(tool_len, presser_w, True)
