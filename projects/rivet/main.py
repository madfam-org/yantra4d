"""Rivet + Burr — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The tubular rivet + burr that reinforces denim stress points (pocket corners, fly base) —
the rigid hard good the Fashion Cabinet `rivet-burr` notion places and bridges to here for
its geometry. A domed cap on a hollow post, and the burr (washer) the post flares into.
Printed rigid (or a print-in-place setting jig), it stands in for the copper rivet.

Modes (dispatched via `target_part`):
  * "set"   — cap+post and burr side by side.
  * "rivet" — just the cap + post.
  * "burr"  — just the washer.

Geometry: the cap is a shallow cylinder (dome approximated by a chamfered cylinder), the
post a smaller cylinder, the burr a flat annulus (cylinder minus bore). Small boolean
count → fast, watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cap_dia`).
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
cap_dia   = float(PARAM(lambda: cap_dia,   9.0))     # rivet cap (head) diameter (mm)
cap_h     = float(PARAM(lambda: cap_h,     2.2))     # cap height (mm)
post_dia  = float(PARAM(lambda: post_dia,  4.0))     # post (shank) diameter (mm)
post_h    = float(PARAM(lambda: post_h,    6.0))     # post height (mm)
bore_dia  = float(PARAM(lambda: bore_dia,  2.0))     # hollow bore through the post (mm)
burr_dia  = float(PARAM(lambda: burr_dia,  8.0))     # burr (washer) outer diameter (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|rivet|burr

# ── Safe clamps ──────────────────────────────────────────────────────────────
cap_dia  = max(5.0, min(cap_dia, 20.0))
cap_h    = max(1.0, min(cap_h, 6.0))
post_dia = max(2.0, min(post_dia, cap_dia - 1.0))
post_h   = max(2.0, min(post_h, 20.0))
bore_dia = max(0.6, min(bore_dia, post_dia - 1.0))
burr_dia = max(post_dia + 1.5, min(burr_dia, 20.0))


def build_rivet():
    """Domed cap on a hollow post."""
    cap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cap_h / 2.0))
        .circle(cap_dia / 2.0)
        .extrude(cap_h)
    )
    # Round the top edge for a dome-ish read.
    try:
        cap = cap.edges(">Z").fillet(min(cap_h, cap_dia * 0.2) * 0.9)
    except Exception:
        pass
    post = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cap_h + post_h / 2.0))
        .circle(post_dia / 2.0)
        .extrude(post_h)
    )
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cap_h + post_h / 2.0))
        .circle(bore_dia / 2.0)
        .extrude(post_h + cap_h + 2.0)
        .translate((0, 0, -cap_h - 1.0))
    )
    return cap.union(post).cut(bore)


def build_burr():
    """Flat washer (annulus) the post flares into."""
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cap_h / 2.0))
        .circle(burr_dia / 2.0)
        .extrude(cap_h)
    )
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cap_h / 2.0))
        .circle((post_dia + 0.3) / 2.0)
        .extrude(cap_h + 2.0)
        .translate((0, 0, -1.0))
    )
    return outer.cut(bore)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rivet":
    result = build_rivet()
elif target_part == "burr":
    result = build_burr()
else:
    gap = cap_dia * 0.4 + burr_dia / 2.0 + cap_dia / 2.0
    result = build_rivet().union(build_burr().translate((gap, 0, 0)))
