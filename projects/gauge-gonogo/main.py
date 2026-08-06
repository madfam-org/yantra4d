"""
Go/No-Go Gauge — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An attribute inspection gauge that checks a dimension against its limits. By
convention the GO end is made to the lower limit and MUST enter/pass; the NO-GO
end is made to the upper limit and MUST NOT. A part is in tolerance when GO goes
and NO-GO does not.

Three types, dispatched by `target_part`:
  - plug_gauge : a double-ended plug for checking a HOLE. A GO pin at the lower
                 limit and a NO-GO pin at the upper limit share a central handle.
  - slot_gauge : a stepped blade for checking a SLOT/GROOVE width — a GO step at
                 the lower limit and a thicker NO-GO step at the upper limit.
  - snap_gauge : a C-frame snap/ring gauge for checking a SHAFT outside diameter,
                 with a GO throat at the upper limit and a NO-GO throat at the
                 lower limit (a good shaft passes GO, stops at NO-GO).

Limits: GO = nominal + tol_minus (lower limit); NO-GO = nominal + tol_plus
(upper limit). Feature print-shrinkage means a physical gauge should be verified
against gauge blocks; tolerance_by_material is declared.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `nominal`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr. Assign the final solid to a top-level name `result`.
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
nominal    = float(PARAM(lambda: nominal,    10.0))   # nominal dimension (mm)
tol_plus   = float(PARAM(lambda: tol_plus,    0.05))  # upper deviation (+) -> NO-GO limit
tol_minus  = float(PARAM(lambda: tol_minus,   0.0))   # lower deviation (may be negative) -> GO limit
pin_len    = float(PARAM(lambda: pin_len,    22.0))   # gauging length of each pin/step
handle_dia = float(PARAM(lambda: handle_dia, 16.0))   # handle diameter
handle_len = float(PARAM(lambda: handle_len,45.0))    # handle length
blade_h    = float(PARAM(lambda: blade_h,    20.0))   # slot-gauge blade height
frame      = float(PARAM(lambda: frame,       8.0))   # snap-gauge frame thickness
knurl_flat = bool( PARAM(lambda: knurl_flat, True))   # flatten handle sides for grip

target_part = str( PARAM(lambda: target_part, "plug_gauge"))

# Limits.
go_dim = nominal + tol_minus        # GO = lower limit
nogo_dim = nominal + tol_plus       # NO-GO = upper limit
if nogo_dim < go_dim:               # guard against inverted tolerances
    go_dim, nogo_dim = nogo_dim, go_dim
go_r = max(0.3, go_dim / 2.0)
nogo_r = max(0.3, nogo_dim / 2.0)


# ── Handle (shared) ──────────────────────────────────────────────────────────
def make_handle(length, dia):
    """Round handle along Z, centred at origin, with two opposing grip flats."""
    h = cq.Workplane("XY").cylinder(length, dia / 2.0)
    if knurl_flat:
        # Shave two opposing flats so the handle can't roll and shows orientation.
        for s in (1, -1):
            slab = (
                cq.Workplane("XY")
                .box(dia, dia, length + 2.0)
                .translate((s * (dia / 2.0 + dia * 0.35), 0, 0))
            )
            h = h.cut(slab)
    return h


# ── Plug gauge (hole check) ──────────────────────────────────────────────────
def build_plug_gauge():
    """GO pin (lower limit) and NO-GO pin (upper limit) on a shared handle.
    The NO-GO pin is intentionally short-marked by a relief groove at its root."""
    handle = make_handle(handle_len, handle_dia)

    go_pin = (
        cq.Workplane("XY")
        .cylinder(pin_len, go_r)
        .translate((0, 0, handle_len / 2.0 + pin_len / 2.0))
    )
    nogo_pin = (
        cq.Workplane("XY")
        .cylinder(pin_len * 0.6, nogo_r)   # NO-GO gauging face is short by design
        .translate((0, 0, -handle_len / 2.0 - pin_len * 0.6 / 2.0))
    )
    body = handle.union(go_pin).union(nogo_pin)

    # Lead chamfers on the free ends aid entry / show which end is which.
    try:
        body = body.faces(">Z").chamfer(min(0.8, go_r * 0.4))
    except Exception:
        pass
    return body


# ── Slot gauge (slot/groove width check) ─────────────────────────────────────
def build_slot_gauge():
    """A flat blade with a thin GO step (lower limit) and a thick NO-GO step
    (upper limit), separated by the handle."""
    handle = make_handle(handle_len, handle_dia)

    go_step = (
        cq.Workplane("XY")
        .box(go_dim, blade_h, pin_len, centered=(True, True, False))
        .translate((0, 0, handle_len / 2.0))
    )
    nogo_step = (
        cq.Workplane("XY")
        .box(nogo_dim, blade_h, pin_len * 0.6, centered=(True, True, True))
        .translate((0, 0, -handle_len / 2.0 - pin_len * 0.6 / 2.0))
    )
    body = handle.union(go_step).union(nogo_step)
    try:
        body = body.edges("|Y and >Z").chamfer(min(0.6, go_dim * 0.2))
    except Exception:
        pass
    return body


# ── Snap gauge (shaft OD check) ──────────────────────────────────────────────
def build_snap_gauge():
    """A C-frame snap gauge: a GO throat at the upper limit and a NO-GO throat at
    the lower limit, opening off a solid handle grip. A good shaft slips into GO
    and is stopped by NO-GO."""
    depth = frame
    grip_h = handle_len
    body_w = nogo_dim + 2.0 * frame + 6.0
    body_h = grip_h + 6.0

    # Solid C-frame plate on the XZ-ish plane (extruded in Y = depth).
    plate = (
        cq.Workplane("XY")
        .box(body_w, depth, body_h, centered=(True, True, True))
    )
    try:
        plate = plate.edges("|Y").fillet(min(4.0, depth * 0.9, body_w / 2.0 - 0.5))
    except Exception:
        pass

    throat_depth = go_dim + frame + 2.0  # how far each slot reaches in from the edge
    # GO throat (upper limit) opens from +X edge, centred high.
    go_slot = (
        cq.Workplane("XY")
        .box(throat_depth, depth + 2.0, nogo_dim, centered=(True, True, True))
        .translate((body_w / 2.0 - throat_depth / 2.0 + 0.1, 0, body_h * 0.22))
    )
    # NO-GO throat (lower limit) opens from -X edge, centred low.
    nogo_slot = (
        cq.Workplane("XY")
        .box(throat_depth, depth + 2.0, go_dim, centered=(True, True, True))
        .translate((-body_w / 2.0 + throat_depth / 2.0 - 0.1, 0, -body_h * 0.22))
    )
    body = plate.cut(go_slot).cut(nogo_slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "slot_gauge":
    result = build_slot_gauge()
elif target_part == "snap_gauge":
    result = build_snap_gauge()
else:
    result = build_plug_gauge()
