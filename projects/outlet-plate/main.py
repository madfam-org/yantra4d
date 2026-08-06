"""
Outlet / Switch Plate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Wall cover plates for device boxes. The mounting-screw pattern lands on the real
device-box standard: US single-gang boxes put the two 6-32 screws 3.28 in
(83.34 mm) apart on the vertical centerline; EU round boxes use a 60 mm screw
spacing. Pick the device opening (duplex outlet, toggle, rocker/Decora, or blank)
and the plate cuts the matching window over a screw pattern that fits the box.

Modes are dispatched via `target_part`:
  * "single_gang" — US single-gang plate: pick the device window; 6-32 screws at
                    3.28 in vertical spacing. 2.75 x 4.5 in outline.
  * "blank_plate" — a solid single-gang blank (same screw pattern, no window).
  * "eu_round"    — EU round cover, 60 mm screw spacing, central round window.

Standards encoded:
  US single-gang plate = 2.75 x 4.5 in (69.85 x 114.3 mm), screw spacing 3.28 in
    (83.34 mm), 6-32 screw clearance ~3.5 mm.  Duplex outlet cutout = 34.9 mm
    dia lobes on 34.9 mm centers (the classic figure-8); toggle slot 9.5x21 mm;
    Decora/rocker window 26.4 x 66.7 mm.
  EU round cover screw spacing = 60 mm (round wall-box centres).

Watertightness: everything is a boolean cut from a single filleted blank (fillet
the blank BEFORE cutting features). Countersinks are stacked cylinders opening to
the front face — no trapped voids.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `device`).
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


# ── Standard dimensions (mm) ─────────────────────────────────────────────────
US_W = 69.85          # 2.75 in plate width
US_H = 114.3          # 4.50 in plate height
US_SCREW_SPACING = 83.34   # 3.28 in center-to-center (vertical)
US_SCREW_CLEAR = 3.6       # 6-32 screw clearance Ø
EU_SCREW_SPACING = 60.0    # EU round box screw spacing


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "single_gang"))
device      = str(PARAM(lambda: device, "duplex"))   # duplex|toggle|rocker|round
thickness   = float(PARAM(lambda: thickness, 3.0))   # plate thickness (mm)
oversize    = float(PARAM(lambda: oversize, 0.0))    # add to W/H (jumbo plates)
corner_r    = float(PARAM(lambda: corner_r, 5.0))    # rounded corner radius (mm)
countersink = bool(PARAM(lambda: countersink, True)) # countersink the screw holes
eu_dia      = float(PARAM(lambda: eu_dia, 55.0))     # EU round plate window Ø (mm)

# Clamp to sane ranges.
thickness = max(1.6, min(thickness, 8.0))
oversize = max(0.0, min(oversize, 20.0))
corner_r = max(0.0, min(corner_r, 10.0))
eu_dia = max(20.0, min(eu_dia, 75.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _blank(w, h, t, r):
    """A rounded-corner plate blank. Fillet BEFORE any feature cuts."""
    b = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    if r > 0.1:
        try:
            b = b.edges("|Z").fillet(min(r, w / 2.0 - 0.5, h / 2.0 - 0.5))
        except Exception:
            pass
    return b


def _screw_holes(body, t, spacing, csink):
    """Two screw holes on the vertical centerline at +/- spacing/2, optionally
    countersunk from the FRONT face (front = +Z here)."""
    for sy in (-spacing / 2.0, spacing / 2.0):
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sy, -1.0))
            .circle(US_SCREW_CLEAR / 2.0).extrude(t + 2.0)
        )
        body = body.cut(hole)
        if csink:
            # 82-degree-ish countersink: a shallow cone opening at the front (+Z).
            cs_top_r = US_SCREW_CLEAR / 2.0 + 1.8
            cs_depth = min(1.8, t * 0.6)
            cone = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, sy, t - cs_depth))
                .circle(US_SCREW_CLEAR / 2.0)
                .workplane(offset=cs_depth + 0.5)
                .circle(cs_top_r)
                .loft(combine=True)
            )
            body = body.cut(cone)
    return body


def _device_window(body, t, kind):
    """Cut the device opening for the chosen device kind (US single gang)."""
    if kind == "toggle":
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .box(9.5, 21.0, t + 2.0, centered=(True, True, False))
        )
        body = body.cut(slot)
    elif kind == "rocker":
        win = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .box(26.4, 66.7, t + 2.0, centered=(True, True, False))
        )
        try:
            win = win.edges("|Z").fillet(3.0)
        except Exception:
            pass
        body = body.cut(win)
    elif kind == "round":
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .circle(17.5).extrude(t + 2.0)
        )
        body = body.cut(hole)
    else:  # duplex outlet — the classic figure-8 (two lobes on 34.9 mm centers)
        for sy in (-17.45, 17.45):
            lobe = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, sy, -1.0))
                .circle(34.9 / 2.0).extrude(t + 2.0)
            )
            body = body.cut(lobe)
        # bridge the two lobes into a waisted figure-8
        bridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .box(26.0, 34.9, t + 2.0, centered=(True, True, False))
        )
        body = body.cut(bridge)
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_single_gang():
    """US single-gang plate with the selected device window + 6-32 screw pattern."""
    w = US_W + oversize
    h = US_H + oversize
    body = _blank(w, h, thickness, corner_r)
    body = _device_window(body, thickness, device)
    body = _screw_holes(body, thickness, US_SCREW_SPACING, countersink)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_blank_plate():
    """Solid single-gang blank (same outline + screw pattern, no device window)."""
    w = US_W + oversize
    h = US_H + oversize
    body = _blank(w, h, thickness, corner_r)
    body = _screw_holes(body, thickness, US_SCREW_SPACING, countersink)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_eu_round():
    """EU round cover: a round plate, central round window, 60 mm screw spacing."""
    plate_d = EU_SCREW_SPACING + 2.0 * (US_SCREW_CLEAR + 8.0)   # box screws + rim
    body = cq.Workplane("XY").circle(plate_d / 2.0).extrude(thickness)

    # Central round window.
    win_r = min(eu_dia, plate_d - 2.0 * US_SCREW_CLEAR - 8.0) / 2.0
    win_r = max(6.0, win_r)
    win = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(win_r).extrude(thickness + 2.0)
    )
    body = body.cut(win)

    # Two screws on the vertical centerline at 60 mm spacing.
    body = _screw_holes(body, thickness, EU_SCREW_SPACING, countersink)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "single_gang": build_single_gang,
    "blank_plate": build_blank_plate,
    "eu_round": build_eu_round,
}

result = _dispatch.get(target_part, build_single_gang)()
