"""
Compliant Spring — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A printable geometric spring — no coil — that flexes because its shape bends, not
because the material is elastic. Three flexure families via `spring_type`:
  • wave       — a vertical column of stacked sine (serpentine) flexures that
                 compress along Z, like a printed wave/finger spring.
  • leaf       — a curved cantilever leaf spring (an arc-shaped beam).
  • cantilever — a simple straight cantilever beam (the reference snap flexure).
Beam/wall thickness tunes stiffness; the part is one continuous solid so it stays
watertight.

NOTE: This models GEOMETRY only. Real spring force depends on the material
(PLA/PETG/TPU/nylon), layer orientation, and infill — the same shape is stiff in
PLA and soft in TPU. Treat `thickness`, `waves`, and `free_length` as stiffness
levers, and validate force empirically.

Interface (Compliant Flexure, `spline`, internal):
  The flexure is defined by `thickness` (beam/wall) and `free_length` (the
  unloaded height/length). Mating pads at each end present flat mounting faces so
  the spring drops into a pocket sized to `width` × pad.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `free_length`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
spring_type = str(  PARAM(lambda: spring_type, "wave"))  # wave | leaf | cantilever_snap
free_length = float(PARAM(lambda: free_length, 40.0))    # unloaded height/length (mm)
width       = float(PARAM(lambda: width,       16.0))    # spring width across (Y, mm)
thickness   = float(PARAM(lambda: thickness,    2.0))    # beam/wall thickness (stiffness, mm)
waves       = int(  PARAM(lambda: waves,          4))    # sine cycles (wave type)
amplitude   = float(PARAM(lambda: amplitude,   10.0))    # peak-to-center sway of the meander (mm)
pad         = float(PARAM(lambda: pad,          4.0))    # end mounting-pad thickness (mm)

target_part = str(PARAM(lambda: target_part, "wave_spring"))  # wave_spring | leaf_spring | cantilever

# The mode dispatcher also picks the spring family; the mode wins if it names one.
if target_part in ("wave_spring", "leaf_spring", "cantilever"):
    spring_type = {"wave_spring": "wave", "leaf_spring": "leaf",
                   "cantilever": "cantilever"}[target_part]

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
free_length = max(10.0, min(free_length, 200.0))
width = max(4.0, min(width, 80.0))
thickness = max(0.6, min(thickness, 8.0))
waves = max(1, min(waves, 12))
amplitude = max(2.0, min(amplitude, 40.0))
pad = max(2.0, min(pad, 12.0))

_SEG = 24  # samples per half-wave for a smooth meander


# ── Helpers ──────────────────────────────────────────────────────────────────
def _closed_extrude_xz(pts, w):
    """Close a list of (x, z) points into a wire on the XZ plane and extrude it
    `w` in +Y (centered), giving a watertight prism."""
    return (
        cq.Workplane("XZ")
        .polyline(pts)
        .close()
        .extrude(w)
        .translate((0, -w / 2.0, 0))
    )


def build_wave():
    """Vertical serpentine: a sine centerline in X over the height Z, given beam
    `thickness`, capped by mounting pads top and bottom. Built as ONE closed
    outline (up the +thickness/2 offset edge, down the −thickness/2 edge) so it is
    a single watertight solid that compresses along Z."""
    body_h = max(1.0, free_length - 2.0 * pad)
    cycles = waves
    half = thickness / 2.0

    # Sample the centerline x(z) = amplitude * sin(2π·cycles·z/body_h) over the
    # flexing height (between the pads). Offset ±half along the path normal;
    # approximate the normal offset with a horizontal ± half (valid for gentle
    # slopes and keeps the wire simple and self-non-intersecting).
    n = max(8, _SEG * cycles)
    zs = [body_h * i / n for i in range(n + 1)]

    def cx(z):
        return amplitude * math.sin(2.0 * math.pi * cycles * z / body_h)

    # Right edge going up (x + half), then left edge coming down (x − half).
    up = [(cx(z) + half, pad + z) for z in zs]
    down = [(cx(z) - half, pad + z) for z in reversed(zs)]
    pts = up + down

    body = _closed_extrude_xz(pts, width)

    # Bottom + top mounting pads spanning the meander sway, so the spring seats
    # flat. Pads overlap into the meander ends for a watertight fuse.
    pad_w = amplitude * 2.0 + thickness + 4.0
    base = _closed_extrude_xz(
        [(-pad_w / 2.0, 0.0), (pad_w / 2.0, 0.0),
         (pad_w / 2.0, pad + 0.6), (-pad_w / 2.0, pad + 0.6)], width)
    top = _closed_extrude_xz(
        [(-pad_w / 2.0, free_length - pad - 0.6), (pad_w / 2.0, free_length - pad - 0.6),
         (pad_w / 2.0, free_length), (-pad_w / 2.0, free_length)], width)
    body = base.union(body).union(top)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_leaf():
    """Curved cantilever leaf spring: a circular-arc beam of `thickness`, fixed at
    one end by a mounting block. The arc bows up over `free_length`; loading the
    free tip flattens the arc. One closed outline (outer arc + inner arc) extruded
    across `width`."""
    span = free_length
    rise = amplitude
    # Fit a circular arc through (0,0) and (span, 0) with mid-rise `rise`.
    # Radius of the arc from chord `span` and sagitta `rise`.
    R = (rise / 2.0) + (span * span) / (8.0 * max(0.5, rise))
    half_ang = math.asin(min(1.0, (span / 2.0) / R))
    cz = -(R - rise)  # arc center below the chord so the mid bows up by `rise`

    n = max(16, _SEG * 2)

    def arc_pt(frac, radial):
        a = -half_ang + 2.0 * half_ang * frac
        x = R * math.sin(a) + span / 2.0
        z = cz + radial * math.cos(a)
        return (x, z)

    outer = [arc_pt(i / n, R + thickness / 2.0) for i in range(n + 1)]
    inner = [arc_pt(i / n, R - thickness / 2.0) for i in range(n, -1, -1)]
    beam = _closed_extrude_xz(outer + inner, width)

    # Root mounting block at the fixed (x≈0) end.
    blk_w = max(6.0, thickness * 3.0 + 2.0)
    blk_h = max(6.0, thickness * 3.0)
    block = _closed_extrude_xz(
        [(-2.0, -blk_h * 0.5), (blk_w - 2.0, -blk_h * 0.5),
         (blk_w - 2.0, blk_h * 0.5), (-2.0, blk_h * 0.5)], width)
    body = block.union(beam)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cantilever():
    """Simple straight cantilever beam of `thickness`, anchored by a root block —
    the reference snap flexure. Deflecting the free tip stores energy in bending."""
    span = free_length
    beam = _closed_extrude_xz(
        [(0.0, -thickness / 2.0), (span, -thickness / 2.0),
         (span, thickness / 2.0), (0.0, thickness / 2.0)], width)

    # Root block at x≈0.
    blk_w = max(6.0, thickness * 3.0 + 2.0)
    blk_h = max(6.0, thickness * 4.0)
    block = _closed_extrude_xz(
        [(-2.0, -blk_h * 0.5), (blk_w - 2.0, -blk_h * 0.5),
         (blk_w - 2.0, blk_h * 0.5), (-2.0, blk_h * 0.5)], width)

    # A small catch lip at the free tip (turns it into a snap hook).
    lip = _closed_extrude_xz(
        [(span - thickness, thickness / 2.0),
         (span, thickness / 2.0),
         (span, thickness / 2.0 + thickness * 1.5),
         (span - thickness, thickness / 2.0 + thickness * 1.5)], width * 0.9)

    body = block.union(beam).union(lip)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if spring_type == "leaf":
    result = build_leaf()
elif spring_type == "cantilever":
    result = build_cantilever()
else:
    result = build_wave()
