"""
Picatinny / M-LOK Accessory Rail — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The universal firearms/optics/photography accessory mounting interface. Models the
MIL-STD-1913 ("Picatinny") rail cross-section and the M-LOK negative-slot standard so
printed adapters mate real hardware.

Three parts (dispatched via `target_part`):
  * "rail_section" — a length of MIL-STD-1913 rail: the correct trapezoidal cross-
                     section (flat top, 45° clamping flanks, lower locating flange)
                     with transverse recoil grooves at the 10 mm standard pitch.
  * "mlok_strip"   — an M-LOK slot strip: a flat bar carrying the M-LOK negative
                     slots (7 mm × 32 mm rounded slots on 40 mm centres).
  * "rail_adapter" — a small base block with a Picatinny cross-section on TOP and a
                     flat bolt-down bottom, to fasten an accessory onto a rail.

MIL-STD-1913 nominal geometry (imperial standard, given here in mm):
  overall rail width 21.20 mm; flat top width ~15.70 mm; 45° angled sides forming the
  clamping recess; recoil-groove pitch 10.0 mm, groove width 5.35 mm (0.206").

Thread-free by design — this is a rail/slot interface, so every render is fast.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `standard`).
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


# ── MIL-STD-1913 nominal constants (mm) ──────────────────────────────────────
RAIL_W_BOTTOM = 21.20   # overall width at the lower locating flange
RAIL_TOP_W    = 15.70   # flat top width (0.617")
FLANGE_H      = 3.15    # height of the lower flange band the clamp grips
TOP_H         = 4.45    # total rail height above its base plane
GROOVE_PITCH  = 10.00   # recoil-groove on-centre spacing (0.394")
GROOVE_W      = 5.35    # recoil-groove width (0.206")
GROOVE_DEPTH  = 3.30    # recoil-groove depth (cut into the top toward the flange)

# M-LOK negative-slot nominal geometry (mm)
MLOK_SLOT_W   = 7.00    # slot width
MLOK_SLOT_L   = 32.00   # slot length (rounded ends)
MLOK_PITCH    = 40.00   # slot on-centre spacing


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "rail_section"))  # rail_section|mlok_strip|rail_adapter
standard    = str(PARAM(lambda: standard,     "picatinny"))     # picatinny | mlok
slots       = int(  PARAM(lambda: slots,           5))          # recoil grooves / M-LOK slots -> length
base_th     = float(PARAM(lambda: base_th,       4.0))          # substrate thickness under the rail
extra_w     = float(PARAM(lambda: extra_w,       0.0))          # widen the substrate beyond the rail
bolt_dia    = float(PARAM(lambda: bolt_dia,      5.2))          # adapter/strip bolt-hole clearance (M5)
bolt_count  = int(  PARAM(lambda: bolt_count,      2))          # bolt holes for adapter/strip base

# Clamp to sane ranges so extreme UI values still build watertight.
slots      = max(1, min(slots, 40))
base_th    = max(2.0, min(base_th, 20.0))
extra_w    = max(0.0, min(extra_w, 40.0))
bolt_dia   = max(0.0, min(bolt_dia, 10.0))
bolt_count = max(0, min(bolt_count, 12))


# ── Cross-section helpers ────────────────────────────────────────────────────
def picatinny_profile():
    """MIL-STD-1913 rail cross-section as a closed wire in the XY plane (X = width,
    Y = height, base at Y=0). Symmetric about X=0. The upper section narrows from the
    21.2 mm flange to the 15.7 mm flat top through the 45° clamping flanks."""
    xb = RAIL_W_BOTTOM / 2.0     # 10.6
    xt = RAIL_TOP_W / 2.0        # 7.85
    # Heights (from base plane): lower flange band, then 45° taper up to the flat top.
    y_flange = FLANGE_H          # top of the vertical lower flange
    y_taper_in = y_flange + 1.30  # a short vertical neck above the flange
    y_top = TOP_H                # flat top
    pts = [
        (-xb, 0.0),
        (-xb, y_flange),
        (-xb, y_taper_in),
        (-xt, y_top),            # 45°-ish clamping flank up to the flat top
        (xt, y_top),
        (xb, y_taper_in),
        (xb, y_flange),
        (xb, 0.0),
    ]
    return cq.Workplane("XY").polyline(pts).close()


def rail_length(n):
    """Length (Y once extruded) for n grooves/slots."""
    if standard == "mlok":
        return max(MLOK_PITCH, n * MLOK_PITCH)
    # Picatinny: material band each side of the outer grooves plus the groove field.
    return n * GROOVE_PITCH + 4.0


def build_rail_solid(length, sub_th):
    """A rail bar: substrate slab + Picatinny cross-section on top, extruded along Y.

    Returns (solid, total_width). The cross-section is drawn in XY then extruded
    along +Z internally, then rotated so the rail runs along Y and stands up in Z —
    keeping the sketch math simple and readable."""
    sub_w = RAIL_W_BOTTOM + 2.0 * extra_w
    # Substrate slab: base at z=0.
    body = cq.Workplane("XY").box(sub_w, length, sub_th, centered=(True, True, False))
    # Rail profile: extrude the XY cross-section through the length, then orient it so
    # width->X, height->Z, length->Y and sit it on top of the slab.
    rail = (
        picatinny_profile()
        .extrude(length)                         # +Z = along the (future) length
        .rotate((0, 0, 0), (1, 0, 0), 90)        # height(Y)->+Z, length(Z)->-Y
        .translate((0, length / 2.0, sub_th))    # centre in Y, sit on the slab
    )
    body = body.union(rail)
    return body, sub_w


def cut_recoil_grooves(body, length, sub_th):
    """Transverse recoil grooves across the rail top at the 10 mm standard pitch."""
    top_z = sub_th + TOP_H
    n = slots
    span = (n - 1) * GROOVE_PITCH
    y0 = -span / 2.0
    cutter_w = RAIL_W_BOTTOM + 4.0
    for i in range(n):
        y = y0 + i * GROOVE_PITCH
        groove = (
            cq.Workplane("XY")
            .box(cutter_w, GROOVE_W, GROOVE_DEPTH + 1.0, centered=(True, True, False))
            .translate((0, y, top_z - GROOVE_DEPTH))
        )
        body = body.cut(groove)
    return body


def mlok_slot_field(th):
    """The M-LOK negative slots as one fused cutter solid (stadium/rounded-end slots
    of MLOK_SLOT_L × MLOK_SLOT_W on MLOK_PITCH centres, long axis along Y)."""
    n = slots
    span = (n - 1) * MLOK_PITCH
    y0 = -span / 2.0
    cutter = None
    for i in range(n):
        y = y0 + i * MLOK_PITCH
        slot = (
            cq.Workplane("XY")
            .slot2D(MLOK_SLOT_L, MLOK_SLOT_W, 90)  # rounded slot, long axis along Y
            .extrude(th + 2.0)
            .translate((0, y, -1.0))
        )
        cutter = slot if cutter is None else cutter.union(slot)
    return cutter


def drill_base(body, th, length):
    """Bolt-down clearance holes along the base centreline (for strip/adapter)."""
    if bolt_dia <= 0.05 or bolt_count <= 0:
        return body
    r = bolt_dia / 2.0
    if bolt_count == 1:
        ys = [0.0]
    else:
        span = length - 2.0 * max(6.0, bolt_dia * 1.6)
        span = max(0.0, span)
        step = span / (bolt_count - 1)
        ys = [-span / 2.0 + i * step for i in range(bolt_count)]
    pts = [(0.0, y) for y in ys]
    cutter = (
        cq.Workplane("XY")
        .pushPoints(pts)
        .circle(r)
        .extrude(th + 2.0)
        .translate((0, 0, -1.0))
    )
    return body.cut(cutter)


# ── Part builders ────────────────────────────────────────────────────────────
def build_rail_section():
    """A standalone length of MIL-STD-1913 rail (picatinny) or an M-LOK slot bar
    (mlok) — chosen by the `standard` parameter."""
    length = rail_length(slots)
    if standard == "mlok":
        return build_mlok_strip()
    body, sub_w = build_rail_solid(length, base_th)
    body = cut_recoil_grooves(body, length, base_th)
    return body


def build_mlok_strip():
    """An M-LOK slot strip: a flat bar carrying the M-LOK negative slots."""
    length = max(MLOK_PITCH, slots * MLOK_PITCH)
    width = RAIL_W_BOTTOM + 2.0 * extra_w
    th = max(base_th, 6.0)
    body = cq.Workplane("XY").box(width, length, th, centered=(True, True, False))
    cutter = mlok_slot_field(th)
    if cutter is not None:
        body = body.cut(cutter)
    body = drill_base(body, th, length)
    try:
        body = body.edges("|Z").fillet(min(2.0, width / 2.0 - 0.5))
    except Exception:
        pass
    return body


def build_rail_adapter():
    """A short base with a Picatinny cross-section on TOP and a flat, bolt-down
    bottom — clamp an accessory to a rail, or bolt an accessory to this."""
    length = rail_length(max(2, min(slots, 6)))
    body, sub_w = build_rail_solid(length, base_th)
    body = cut_recoil_grooves(body, length, base_th)
    body = drill_base(body, base_th, length)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "mlok_strip":
    result = build_mlok_strip()
elif target_part == "rail_adapter":
    result = build_rail_adapter()
else:
    result = build_rail_section()
