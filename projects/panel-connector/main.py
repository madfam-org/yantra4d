"""
Panel Connector Frame — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A panel-mount frame that carries the correct cutout for a chosen connector, so a
bare enclosure wall gets a clean, sized opening plus the connector's own fixing
holes. Pick the connector and the plate gets the right window and screw pattern;
bolt the frame into a rectangular panel aperture (or use it as a drilling
template).

Modes are dispatched via `target_part`:
  * "single_cutout" — a frame plate with one connector cutout.
  * "dual_cutout"   — a wider plate with two side-by-side cutouts.
  * "blank_plate"   — a blank cover plate (no cutout) to close an unused bay.

Connector cutouts (panel opening + fixing pattern) for XT60, USB-A, RJ45 and
GX16 aviation connectors.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `connector`).
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


# ── Connector table ──────────────────────────────────────────────────────────
# kind      : "rect" (rectangular window) or "round" (bored hole).
# For rect: w, h are the panel opening; for round: bore is the panel hole dia.
# screws    : list of (x, y) fixing-hole centres relative to the cutout centre.
# screw_d   : fixing-hole diameter.
# footprint : (w, h) suggested minimum plate window around the connector.
_CONN = {
    # XT60: panel-mount version drops in a ~16 x 8 slot; 2 fixing holes at ±12.5.
    "XT60": {
        "kind": "rect", "w": 16.4, "h": 8.4, "screw_d": 3.2,
        "screws": [(-12.5, 0.0), (12.5, 0.0)], "footprint": (34.0, 20.0),
    },
    # USB-A panel coupler: ~14 x 6.5 window, 2 fixing holes at ±15.
    "USB-A": {
        "kind": "rect", "w": 14.0, "h": 6.8, "screw_d": 3.2,
        "screws": [(-15.0, 0.0), (15.0, 0.0)], "footprint": (36.0, 20.0),
    },
    # RJ45 keystone-style coupler: ~15 x 13 window, 2 fixing holes at ±13.
    "RJ45": {
        "kind": "rect", "w": 15.0, "h": 13.5, "screw_d": 3.2,
        "screws": [(-13.0, 0.0), (13.0, 0.0)], "footprint": (34.0, 26.0),
    },
    # GX16 aviation: a round 16 mm panel bore with a small anti-rotation key.
    "GX16-aviation": {
        "kind": "round", "bore": 16.2, "screw_d": 0.0,
        "screws": [], "footprint": (26.0, 26.0),
    },
}


def conn_spec(key):
    k = str(key).strip()
    if k in _CONN:
        return _CONN[k]
    ku = k.upper().replace(" ", "")
    for name, spec in _CONN.items():
        if name.upper().replace(" ", "") == ku:
            return spec
    return _CONN["XT60"]


# ── Parameters ───────────────────────────────────────────────────────────────
connector  = str(  PARAM(lambda: connector, "XT60"))    # XT60|USB-A|RJ45|GX16-aviation
plate_t    = float(PARAM(lambda: plate_t,     3.0))     # frame plate thickness
margin     = float(PARAM(lambda: margin,      6.0))     # plate border past the cutout
corner_r   = float(PARAM(lambda: corner_r,    3.0))     # plate corner radius
mount_bore = float(PARAM(lambda: mount_bore,  3.4))     # plate corner mount holes (M3)
pair_gap   = float(PARAM(lambda: pair_gap,   10.0))     # gap between the two dual cutouts

target_part = str(PARAM(lambda: target_part, "single_cutout"))

# ── Derived ──────────────────────────────────────────────────────────────────
spec = conn_spec(connector)
fp_w, fp_h = spec["footprint"]

plate_t = max(2.0, min(plate_t, 8.0))
margin = max(4.0, min(margin, 20.0))
corner_r = max(0.0, min(corner_r, 8.0))
mount_bore = max(2.7, min(mount_bore, 6.0))
pair_gap = max(4.0, min(pair_gap, 40.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _plate(w, d):
    body = cq.Workplane("XY").box(w, d, plate_t, centered=(True, True, False))
    if corner_r > 0.05:
        try:
            body = body.edges("|Z").fillet(min(corner_r, w / 2.0 - 0.1, d / 2.0 - 0.1))
        except Exception:
            pass
    return body


def _cut_connector(body, cx):
    """Cut the connector opening + its fixing holes, centred at (cx, 0)."""
    if spec["kind"] == "round":
        hole = (
            cq.Workplane("XY").transformed(offset=cq.Vector(cx, 0, -0.5))
            .circle(spec["bore"] / 2.0).extrude(plate_t + 1.0)
        )
        body = body.cut(hole)
        # anti-rotation key notch (small rectangular tab off the bore)
        key = (
            cq.Workplane("XY").transformed(offset=cq.Vector(cx, spec["bore"] / 2.0, -0.5))
            .box(3.0, 2.4, plate_t + 1.0, centered=(True, True, False))
        )
        body = body.cut(key)
    else:
        win = (
            cq.Workplane("XY").transformed(offset=cq.Vector(cx, 0, -0.5))
            .box(spec["w"], spec["h"], plate_t + 1.0, centered=(True, True, False))
        )
        body = body.cut(win)
    # fixing holes
    if spec["screws"]:
        pts = [(cx + sx, sy) for (sx, sy) in spec["screws"]]
        fix = (
            cq.Workplane("XY").pushPoints(pts).circle(spec["screw_d"] / 2.0)
            .extrude(plate_t + 1.0).translate((0, 0, -0.5))
        )
        body = body.cut(fix)
    return body


def _corner_mounts(body, w, d):
    hx = w / 2.0 - margin / 2.0
    hy = d / 2.0 - margin / 2.0
    pts = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    mounts = (
        cq.Workplane("XY").pushPoints(pts).circle(mount_bore / 2.0)
        .extrude(plate_t + 1.0).translate((0, 0, -0.5))
    )
    return body.cut(mounts)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_single_cutout():
    w = fp_w + 2.0 * margin
    d = fp_h + 2.0 * margin
    body = _plate(w, d)
    body = _cut_connector(body, 0.0)
    body = _corner_mounts(body, w, d)
    return body


def build_dual_cutout():
    step = fp_w + pair_gap
    w = 2.0 * fp_w + pair_gap + 2.0 * margin
    d = fp_h + 2.0 * margin
    body = _plate(w, d)
    for cx in (-step / 2.0, step / 2.0):
        body = _cut_connector(body, cx)
    body = _corner_mounts(body, w, d)
    return body


def build_blank_plate():
    """A blank cover plate the size of the single-cutout frame, with only the
    corner mount holes — closes an unused connector bay."""
    w = fp_w + 2.0 * margin
    d = fp_h + 2.0 * margin
    body = _plate(w, d)
    body = _corner_mounts(body, w, d)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "single_cutout": build_single_cutout,
    "dual_cutout": build_dual_cutout,
    "blank_plate": build_blank_plate,
}

result = _dispatch.get(target_part, build_single_cutout)()
