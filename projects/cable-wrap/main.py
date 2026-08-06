"""
Cable Wrap & XLR Label — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Tames stage and studio cabling. A figure-8 winder to coil a cable, a snap ring
that labels an XLR/instrument connector with embossed text, and a hook keeper
that holds a looped cable on a wall or rack. Sized by the cable diameter so the
channel grips the specific cable.

Three parts (dispatched by `target_part`):
  * "wrap"        — a dumbbell / figure-8 winder: two end spools joined by a
                    waist; wind the cable in a figure-8 to prevent memory kinks.
  * "xlr_label"   — a split snap ring that clips around an XLR barrel and carries
                    an embossed channel label (`label_text`).
  * "hook_keeper" — a wall hook with a rounded cable saddle and a return lip.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cable_dia`).
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
target_part = str(PARAM(lambda: target_part, "wrap"))  # wrap|xlr_label|hook_keeper

cable_dia  = float(PARAM(lambda: cable_dia,   7.0))   # cable outer diameter (mm)
wrap_len   = float(PARAM(lambda: wrap_len,   90.0))   # figure-8 winder overall length (mm)
spool_dia  = float(PARAM(lambda: spool_dia,  34.0))   # winder end-spool diameter (mm)
wall       = float(PARAM(lambda: wall,        3.0))   # body wall thickness (mm)
label_text = str(  PARAM(lambda: label_text, "MIC 1"))  # XLR label text
label_dia  = float(PARAM(lambda: label_dia,  19.0))   # XLR barrel diameter (mm)
screw_dia  = float(PARAM(lambda: screw_dia,   4.5))   # hook keeper screw clearance (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
cable_dia = max(2.0, min(cable_dia, 25.0))
wrap_len  = max(50.0, min(wrap_len, 200.0))
spool_dia = max(18.0, min(spool_dia, 80.0))
wall      = max(2.0, min(wall, 6.0))
label_dia = max(10.0, min(label_dia, 40.0))
screw_dia = max(2.5, min(screw_dia, 8.0))
# Keep the label short so the embossed text fits the ring circumference.
label_text = (label_text or "LABEL")[:10]


# ── Part builders ────────────────────────────────────────────────────────────
def build_wrap():
    """A dumbbell figure-8 winder: two flanged end spools joined by a slim waist.
    The cable wraps in a figure-8 around the waist and over the flanges."""
    core_r = max(cable_dia * 1.2, spool_dia * 0.32)
    flange_r = spool_dia / 2.0
    thick = max(cable_dia + 2.0 * wall, 12.0)   # winder depth (z)
    waist_len = wrap_len - 2.0 * flange_r
    waist_len = max(waist_len, spool_dia * 0.4)

    # Waist bar joining the two spool centres (along X).
    waist = (
        cq.Workplane("XY")
        .box(waist_len, core_r * 2.0, thick, centered=(True, True, False))
    )
    body = waist
    # Two end spools: a core cylinder with a flange lip top and bottom so cable
    # can't slide off. Built as core + two disks.
    for sx in [-waist_len / 2.0, waist_len / 2.0]:
        core = (
            cq.Workplane("XY")
            .circle(core_r)
            .extrude(thick)
            .translate((sx, 0, 0))
        )
        flange_bot = (
            cq.Workplane("XY")
            .circle(flange_r)
            .extrude(wall)
            .translate((sx, 0, 0))
        )
        flange_top = (
            cq.Workplane("XY")
            .circle(flange_r)
            .extrude(wall)
            .translate((sx, 0, thick - wall))
        )
        body = body.union(core).union(flange_bot).union(flange_top)
    return body


def build_xlr_label():
    """A split snap ring that clips over an XLR barrel and carries embossed text.
    A C-ring (open mouth so it snaps on) with the label raised on the outside."""
    r_in = label_dia / 2.0 + 0.3
    r_out = r_in + wall
    ring_h = max(10.0, label_dia * 0.55)

    ring = cq.Workplane("XY").circle(r_out).circle(r_in).extrude(ring_h)
    # Snap mouth: a slot narrower than the diameter so it springs over the barrel.
    mouth_w = max(2.0, r_in * 0.7)
    mouth = (
        cq.Workplane("XY")
        .box(mouth_w, r_out * 2.5, ring_h + 2.0, centered=(True, False, False))
        .translate((0, 0, -1.0))
    )
    ring = ring.cut(mouth)

    # Embossed label: raise the text on a flat pad on the +Y outer face.
    pad_w = min(r_out * 1.6, 30.0)
    pad_h = ring_h * 0.7
    pad = (
        cq.Workplane("XZ")
        .box(pad_w, pad_h, wall * 0.8, centered=(True, True, False))
        .translate((0, r_out - 0.1, ring_h / 2.0))
    )
    ring = ring.union(pad)
    # Engrave the label INTO the pad's outer (+Y) face. The XZ workplane normal
    # points −Y, so a text solid built just proud of the pad's outer surface
    # extrudes back into the pad; cutting it leaves a clean debossed (recessed)
    # label that is snag-free and always watertight.
    try:
        pad_front = r_out - 0.1  # pad's outer (+Y) surface
        fs = min(pad_h * 0.6, pad_w / max(2, len(label_text)) * 1.5)
        depth = min(wall * 0.5, 1.0)
        txt = (
            cq.Workplane("XZ", origin=(0, pad_front + 0.05, ring_h / 2.0))
            .text(label_text, fs, depth, combine=False,
                  font="Arial", halign="center", valign="center")
        )
        ring = ring.cut(txt)
    except Exception:
        pass  # text is a label — the raised pad still works if a glyph fails
    return ring


def build_hook_keeper():
    """A wall hook: a screw plate with a rounded cable saddle and a return lip so
    a coiled cable hangs without slipping off."""
    saddle_r = max(cable_dia * 1.6, 12.0)
    plate_w = saddle_r * 2.0 + 2.0 * wall
    plate_h = saddle_r * 3.0
    plate_t = wall + 2.0

    # Back plate (vertical, in XZ), thickness in Y.
    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_t, plate_h, centered=(True, True, False))
        .translate((0, -plate_t / 2.0, 0))
    )
    # Hook arm sweeping out and up: a bar reaching +Y then an up-turned lip.
    arm = (
        cq.Workplane("XY")
        .box(saddle_r * 1.4, saddle_r * 2.0, plate_t, centered=(True, False, False))
        .translate((0, 0, plate_h * 0.3))
    )
    lip = (
        cq.Workplane("XY")
        .box(saddle_r * 1.4, plate_t, saddle_r + plate_t, centered=(True, True, False))
        .translate((0, saddle_r * 2.0 - plate_t / 2.0, plate_h * 0.3))
    )
    body = plate.union(arm).union(lip)
    # Round the cable saddle: cut a half cylinder along X over the arm top.
    trough = (
        cq.Workplane("YZ")
        .circle(saddle_r * 0.7)
        .extrude(plate_w + 2.0)
        .translate((-plate_w / 2.0 - 1.0, saddle_r, plate_h * 0.3 + plate_t + saddle_r * 0.55))
    )
    try:
        body = body.cut(trough)
    except Exception:
        pass
    # Two screw holes through the back plate (bored +Y).
    r = screw_dia / 2.0
    for zc in [plate_h * 0.12, plate_h * 0.85]:
        cutter = (
            cq.Workplane("XZ")
            .circle(r)
            .extrude(plate_t + 4.0)
            .translate((0, 2.0, zc))
        )
        body = body.cut(cutter)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "xlr_label":
    result = build_xlr_label()
elif target_part == "hook_keeper":
    result = build_hook_keeper()
else:
    result = build_wrap()
