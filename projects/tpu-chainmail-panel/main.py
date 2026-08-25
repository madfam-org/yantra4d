"""TPU Chainmail Panel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A print-in-place flexible chainmail panel — the additive-manufacturing fabric that
the Fashion Cabinet `tpu-panel-impreso` fabric card describes as cloth and bridges to
here for its geometry. A grid of interlocked rings (the 4-in-1 European weave) prints
in one job as separate, already-linked solids and drapes like a textile: rigid link,
flexible sheet. Sized by ring count so a Fashion Cabinet garment panel's finished
dimensions drive the weave.

This is the soft-goods↔hard-goods seam made physical: Fashion Cabinet owns the panel
as a *fabric* (drape, stretch, cut planning); Yantra4D owns it as a *solid* (the
printable ring lattice). One material identity spans both — `bambu-tpu-95a`.

Modes (dispatched via `target_part`):
  * "panel"   — the full interlocked ring grid (rows x cols), print-in-place.
  * "swatch"  — a small 3x3 sample for a print/fit test.
  * "ring"    — a single ring (the unit cell), for tuning cross-section + clearance.

Every ring is a watertight torus; rings are NOT fused (they interlink by placement,
as real chainmail does) — the assembly is a set of separate solids the slicer prints
in place.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `rows`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr.
  - Assign the final result to a top-level name `result`.
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
rows        = int(  PARAM(lambda: rows,        10))     # rings down the panel
cols        = int(  PARAM(lambda: cols,        8))      # rings across the panel
ring_id     = float(PARAM(lambda: ring_id,     9.0))    # ring inner diameter (mm)
wire_d      = float(PARAM(lambda: wire_d,      2.4))    # ring wire (cross-section) diameter (mm)
clearance   = float(PARAM(lambda: clearance,   0.45))   # print gap between linked rings (mm)

target_part = str(  PARAM(lambda: target_part, "panel"))  # panel|swatch|ring

# ── Safe clamps ──────────────────────────────────────────────────────────────
rows      = max(1, min(rows, 40))
cols      = max(1, min(cols, 40))
ring_id   = max(4.0, min(ring_id, 30.0))
wire_d    = max(1.2, min(wire_d, 6.0))
clearance = max(0.2, min(clearance, 1.5))

ring_od   = ring_id + 2.0 * wire_d        # ring outer diameter
r_center  = (ring_id + wire_d) / 2.0      # torus centreline radius
tube_r    = wire_d / 2.0                  # torus tube radius

# 4-in-1 geometry: rings lie in tilted planes so each links four neighbours. The
# in-plane pitch packs rings so a linked pair overlaps by ~one wire; the row pitch
# is half that (offset rows interleave). Tilt alternates ± so adjacent columns link.
col_pitch = (ring_od - wire_d - clearance)          # centre-to-centre across a row
row_pitch = col_pitch * 0.62                        # interleaved rows sit closer
tilt_deg  = 32.0                                     # ring plane tilt off vertical


def _ring(cx, cy, tilt_sign):
    """One chainmail ring centred at (cx, cy) on the panel plane (XY), its plane
    tilted about the Y axis by ±tilt so it interlinks its row neighbours. A closed
    torus — watertight. Z is the panel's thickness direction."""
    torus = cq.Solid.makeTorus(
        r_center, tube_r,
        pnt=cq.Vector(0, 0, 0),
        dir=cq.Vector(0, 0, 1),          # ring lies flat, axis up
    )
    w = cq.Workplane(obj=torus)
    # Tilt the ring about Y so consecutive rings in a row interlock through each other.
    w = w.rotate((0, 0, 0), (0, 1, 0), tilt_sign * tilt_deg)
    return w.translate((cx, cy, 0))


def build_panel(n_rows, n_cols):
    """The interlocked ring grid. Even/odd rows are offset by half a column and the
    tilt alternates so every interior ring links its four diagonal neighbours — the
    4-in-1 weave. Returns an Assembly of separate (interlinked) ring solids."""
    asm = cq.Assembly()
    idx = 0
    for r in range(n_rows):
        y = r * row_pitch
        x_off = (col_pitch / 2.0) if (r % 2) else 0.0
        for c in range(n_cols):
            x = c * col_pitch + x_off
            # Alternate tilt across columns AND rows so neighbours interlink.
            tilt_sign = 1 if ((r + c) % 2 == 0) else -1
            asm.add(_ring(x, y, tilt_sign), name=f"ring_{idx}",
                    color=cq.Color("#8a8f94"))
            idx += 1
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "ring":
    result = _ring(0, 0, 1)
elif target_part == "swatch":
    result = build_panel(3, 3)
else:
    result = build_panel(rows, cols)
