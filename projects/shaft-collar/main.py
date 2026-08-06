"""
Keyed Shaft Collar — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A shaft collar is a ring that clamps onto a round drive shaft to set an axial
stop, space a bearing, or key a hub in place. This cartridge builds three shaft
stops sized to the common small-shaft bore range (6-12 mm) that the shaft-spline
commons family shares, so a printed collar drops onto the same shafts a
spline-hub or D-shaft knob keys to.

Three distinct collars (each keyed to the shaft-spline 6-12 mm bore + M-series
setscrew standard):
  - setscrew_collar : the classic solid-ring set collar. A radial setscrew bore
                      threads down onto the shaft to pin the collar in place.
  - clamp_collar    : a split clamping ring — a saw slit across one side and a
                      cross clamp-bolt bore squeeze the ring shut around the
                      shaft (kinder to the shaft, no marring).
  - shaft_stop      : a flanged stop / thrust washer — a set collar with a wide
                      base flange that presents a large face for a bearing or a
                      panel to seat against.

Dimensionally real (small-shaft accessories):
  - bore Ø            : 6-12 mm (matches the shaft-spline commons range)
  - setscrew          : M4 clearance ~4.3 mm radial (M3-M5 typical for this size)
  - clamp bolt        : M4 ~4.3 mm cross bore on the split ring
  - ring OD           : ~bore + 2x wall, wall ~5 mm (a stiff printable ring)

Watertight strategy:
  Every collar is a solid ring (a cylinder with the shaft bore cut fully through
  → the bore vents to both faces). The setscrew / clamp bores are through-holes
  that vent to outside. The clamp slit is cut fully through one wall so it opens
  to the bore and the OD (a real gap, not a trapped void). The flange is a second
  cylinder UNIONED coaxially into shared material. Fillets are applied to the
  clean ring blank BEFORE any feature is cut, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>) — do NOT use globals()/eval.
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


# ── Parameters (6-12 mm shaft collars) ───────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "setscrew_collar"))
# "setscrew_collar" | "clamp_collar" | "shaft_stop"

bore_d = float(PARAM(lambda: bore_d, 8.0))         # shaft bore Ø (mm)
wall = float(PARAM(lambda: wall, 5.0))             # ring wall thickness (radial, mm)
collar_h = float(PARAM(lambda: collar_h, 10.0))    # collar height / length (mm)
set_d = float(PARAM(lambda: set_d, 4.3))           # setscrew / clamp bolt Ø (mm)
flange_ext = float(PARAM(lambda: flange_ext, 6.0)) # flange radial extension (shaft_stop)
flange_t = float(PARAM(lambda: flange_t, 3.0))     # flange thickness (shaft_stop)

# Clamp to sane ranges so extreme UI values never crash the kernel.
bore_d = max(6.0, min(bore_d, 12.0))
wall = max(3.0, min(wall, 10.0))
collar_h = max(5.0, min(collar_h, 25.0))
set_d = max(2.5, min(set_d, min(wall - 0.8, collar_h - 2.0, 6.0)))
flange_ext = max(3.0, min(flange_ext, 20.0))
flange_t = max(2.0, min(flange_t, collar_h - 1.0))

collar_od = bore_d + 2.0 * wall


# ── Primitives ───────────────────────────────────────────────────────────────
def _ring(od, height, bore):
    """A solid ring: an OD cylinder with the shaft bore cut fully through so the
    bore vents top and bottom (never a sealed cavity). Base at z=0."""
    blank = (
        cq.Workplane("XY")
        .cylinder(height, od / 2.0, centered=(True, True, False))
    )
    # Soften the top OD rim on the clean blank BEFORE boring.
    try:
        blank = blank.faces(">Z").edges("%circle").fillet(min(0.8, wall * 0.15))
    except Exception:
        pass
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(bore / 2.0)
        .extrude(height + 1.0)
    )
    return blank.cut(bore)


def _radial_bore(diam, center_z, reach):
    """A radial (X-axis) through-bore at height center_z, from the ring OD in to
    the bore, vented to outside. `reach` is the half-length each way."""
    return (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, center_z, 0))
        .circle(diam / 2.0)
        .extrude(reach, both=True)
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_setscrew_collar():
    """Solid set collar: a ring with a single radial setscrew bore that pins the
    collar to the shaft."""
    body = _ring(collar_od, collar_h, bore_d)
    body = body.cut(_radial_bore(set_d, collar_h / 2.0, collar_od / 2.0 + 1.0))
    return body


def build_clamp_collar():
    """Split clamping collar: a ring with a saw slit cut fully through one wall
    (opening bore→OD, a real gap) and a cross clamp-bolt bore that squeezes the
    ring shut. Kinder to the shaft than a setscrew."""
    body = _ring(collar_od, collar_h, bore_d)

    # Saw slit through the +X wall: a thin box from the bore out past the OD,
    # spanning the full height (opens to bore and to outside → a genuine gap).
    slit_w = 1.6
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(collar_od / 4.0, 0, -0.5))
        .box(collar_od / 2.0 + 1.0, slit_w, collar_h + 1.0,
             centered=(True, True, False))
    )
    body = body.cut(slit)

    # Cross clamp bolt: a Y-axis through-bore ahead of the slit (straddles the gap
    # so tightening pulls the two ears together). Placed above mid-height.
    bolt_z = collar_h / 2.0
    bolt = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(collar_od / 2.0 - wall * 0.5, bolt_z, 0))
        .circle(set_d / 2.0)
        .extrude(collar_od / 2.0 + 1.0, both=True)
    )
    body = body.cut(bolt)
    return body


def build_shaft_stop():
    """Flanged shaft stop / thrust collar: a set collar with a wide base flange
    presenting a large seating face for a bearing or panel. The flange is a
    coaxial disk UNIONED into the ring's shared material → one manifold body."""
    body = _ring(collar_od, collar_h, bore_d)

    flange_od = collar_od + 2.0 * flange_ext
    flange = (
        cq.Workplane("XY")
        .cylinder(flange_t, flange_od / 2.0, centered=(True, True, False))
    )
    # Fillet the clean flange top rim before boring / unioning.
    try:
        flange = flange.faces(">Z").edges("%circle").fillet(min(1.0, flange_t * 0.3))
    except Exception:
        pass
    # Bore the flange so the shaft passes through the whole stack.
    fbore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(bore_d / 2.0)
        .extrude(flange_t + 1.0)
    )
    flange = flange.cut(fbore)
    body = body.union(flange)

    # Radial setscrew through the upper ring (above the flange).
    set_z = flange_t + (collar_h - flange_t) / 2.0
    body = body.cut(_radial_bore(set_d, set_z, collar_od / 2.0 + 1.0))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "clamp_collar":
    result = build_clamp_collar()
elif target_part == "shaft_stop":
    result = build_shaft_stop()
else:
    result = build_setscrew_collar()
