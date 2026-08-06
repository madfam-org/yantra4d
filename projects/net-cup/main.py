"""
Net Cup / Hydroponic Collar — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A net cup is a tapered mesh basket that drops into a hole in a lid, bucket or
PVC pipe for Kratky, DWC and NFT hydroponics. Its wide rim lip rests on the
hole edge; slots in the tapered wall let roots and water pass while retaining
the growing medium (clay pebbles, rockwool).

  * "net_cup"     — the full tapered mesh basket with a rim lip and a base ring
                    (target_part == "net_cup").
  * "collar"      — a short mesh collar / hole adapter ring that seats a plug or
                    rockwool cube in a lid hole (target_part == "collar").
  * "lid_grommet" — a plain tapered eyelet that lines a drilled lid hole so a
                    smooth net cup or tube seats without chafing the lid
                    (target_part == "lid_grommet").

Real dimensions (net cup nominal, dimensionally accurate):
  - 2 in net cup: rim lip OD ~50 mm, body top OD ~44 mm, base OD ~30 mm,
    height ~48 mm, drops into a ~44-45 mm hole (lip overhangs the hole edge).
  - 3 in net cup: rim lip OD ~76 mm, body top OD ~68 mm, base OD ~44 mm,
    height ~66 mm, drops into a ~68-70 mm hole.
  The taper (wide top, narrow base) is the truncated-cone form that keeps the
  medium from falling through while shedding into the reservoir.

Watertight strategy: the basket wall is an OUTER cone frustum minus an INNER
cone frustum — an open tube (open top + open base), which is a closed 2-manifold
(watertight in trimesh terms). Mesh openings are obround slots swept fully
through the wall (open to BOTH faces → no trapped void). The rim lip is a solid
annular disc unioned at the top (overlapping into the wall, never tangent). The
base is left OPEN (a real net cup drains from the bottom). Every union overlaps
into shared material; the whole is one manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "net_cup"))  # net_cup | collar | lid_grommet

top_od = float(PARAM(lambda: top_od, 44.0))       # body top outer diameter (mm)
base_od = float(PARAM(lambda: base_od, 30.0))     # body base outer diameter (mm)
cup_h = float(PARAM(lambda: cup_h, 48.0))         # basket height (mm)
wall = float(PARAM(lambda: wall, 2.0))            # basket wall thickness (mm)
lip_w = float(PARAM(lambda: lip_w, 3.0))          # rim lip radial overhang (mm)
lip_h = float(PARAM(lambda: lip_h, 3.0))          # rim lip thickness (mm)
slot_w = float(PARAM(lambda: slot_w, 3.0))        # mesh slot width (mm)
slot_rows = int(float(PARAM(lambda: slot_rows, 3)))    # vertical rows of slots
slot_cols = int(float(PARAM(lambda: slot_cols, 8)))    # slots around the cup

# ── Clamps (keep the kernel safe at UI extremes) ─────────────────────────────
top_od = max(20.0, min(top_od, 120.0))
base_od = max(12.0, min(base_od, top_od - 6.0))
cup_h = max(15.0, min(cup_h, 120.0))
wall = max(1.2, min(wall, 6.0))
lip_w = max(1.5, min(lip_w, 10.0))
lip_h = max(1.5, min(lip_h, 8.0))
slot_w = max(1.5, min(slot_w, 8.0))
slot_rows = max(1, min(slot_rows, 8))
slot_cols = max(3, min(slot_cols, 16))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _frustum(bottom_r, top_r, height, z0=0.0):
    """A solid truncated cone, base at z0. Uses the OCCT primitive makeCone
    (radius1=bottom, radius2=top) — far faster and more robust than lofting two
    circles, and it produces a clean single-solid frustum every time."""
    return cq.Workplane(obj=cq.Solid.makeCone(bottom_r, top_r, height)).translate((0, 0, z0))


def _cone_shell(top_r, base_r, height, thk, z0=0.0):
    """An open-ended conical tube: outer frustum minus a slightly taller inner
    frustum, so both the top and bottom are open annular rings (a closed,
    watertight 2-manifold). Wall thickness `thk` measured horizontally."""
    outer = _frustum(base_r, top_r, height, z0)
    inner = _frustum(base_r - thk, top_r - thk, height + 2.0, z0 - 1.0)
    return outer.cut(inner)


def _wall_slot_solid(z_center, ang_deg, width, height, outer_r):
    """An obround slot solid swept fully through the wall at a given height and
    angle. A rounded-rectangle prism aimed radially outward from the axis, long
    enough to pierce the wall on both faces (open → no trapped void). Returns the
    raw Solid so many can be grouped into one Compound and cut in a single pass."""
    prism = (
        cq.Workplane("XZ")
        .slot2D(height, width, angle=90)
        .extrude(outer_r + 6.0)
    )
    # slot2D on XZ lies in the X(horizontal)-Z(vertical) plane centred at origin,
    # extruded along +Y toward the axis; rotate it to face outward and lift it.
    prism = prism.rotate((0, 0, 0), (0, 0, 1), ang_deg)
    prism = prism.translate((0, 0, z_center))
    return prism.val()


def _mesh(body, top_r, base_r, height, z0=0.0):
    """Cut a grid of obround slots through a conical wall. Each row sits at a
    height band; slots are staggered so adjacent rows don't line up. Radius at a
    given z is interpolated so the slot always reaches through the local wall.

    All slot cutters are grouped into ONE Compound and subtracted in a single
    boolean pass — sequential per-slot cuts are O(rows*cols * mesh_size) and
    become minutes-long at the dense UI extreme; the batched cut stays fast and
    yields the same single-manifold result."""
    margin = max(4.0, height * 0.12)
    usable = height - 2.0 * margin
    if usable <= 0 or slot_rows < 1:
        return body
    row_gap = usable / max(1, slot_rows - 1) if slot_rows > 1 else 0.0
    slot_h = max(3.0, min(row_gap * 0.62 if slot_rows > 1 else usable * 0.7, usable))
    cutters = []
    for r in range(slot_rows):
        zc = z0 + margin + r * row_gap
        frac = (zc - z0) / height
        local_r = base_r + (top_r - base_r) * frac
        stagger = (360.0 / slot_cols) * 0.5 if (r % 2) else 0.0
        for c in range(slot_cols):
            ang = (360.0 / slot_cols) * c + stagger
            cutters.append(_wall_slot_solid(zc, ang, slot_w, slot_h, local_r))
    if cutters:
        body = body.cut(cq.Workplane(obj=cq.Compound.makeCompound(cutters)))
    return body


def _rim_lip(top_r, lip_width, lip_thk, z_top):
    """A solid annular lip disc at the rim that overhangs the hole edge. Its
    inner radius overlaps the wall (union into shared material)."""
    inner = top_r - wall - 0.5
    outer = top_r + lip_width
    return (
        cq.Workplane("XY")
        .workplane(offset=z_top - lip_thk)
        .circle(outer)
        .circle(inner)
        .extrude(lip_thk)
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_net_cup():
    """Full tapered mesh basket: conical wall + rim lip, open base, mesh slots."""
    top_r = top_od / 2.0
    base_r = base_od / 2.0
    shell = _cone_shell(top_r, base_r, cup_h, wall)
    lip = _rim_lip(top_r, lip_w, lip_h, cup_h)
    body = shell.union(lip)
    # Base retaining ring: a short solid ring at the very bottom so the medium
    # doesn't spill while roots still exit the lowest slots. Union, don't kiss.
    base_ring = (
        cq.Workplane("XY")
        .circle(base_r)
        .circle(max(0.5, base_r - wall - 1.5))
        .extrude(max(2.0, wall + 0.5))
    )
    body = body.union(base_ring)
    body = _mesh(body, top_r, base_r, cup_h)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_collar():
    """A short mesh collar / hole adapter: a squat tapered ring that seats a
    rockwool cube or a bare plug in a lid hole. Shorter than the full cup with a
    single band of slots and a lip."""
    top_r = top_od / 2.0
    base_r = max(base_od / 2.0, top_r - 4.0)
    h = max(12.0, cup_h * 0.4)
    shell = _cone_shell(top_r, base_r, h, wall)
    lip = _rim_lip(top_r, lip_w, lip_h, h)
    body = shell.union(lip)
    # one staggered band of slots, batched into a single cut
    margin = max(3.0, h * 0.2)
    zc = margin + (h - 2.0 * margin) * 0.5
    frac = zc / h
    local_r = base_r + (top_r - base_r) * frac
    slot_h = max(3.0, h - 2.0 * margin)
    cutters = [
        _wall_slot_solid(zc, (360.0 / slot_cols) * c, slot_w, slot_h, local_r)
        for c in range(slot_cols)
    ]
    if cutters:
        body = body.cut(cq.Workplane(obj=cq.Compound.makeCompound(cutters)))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_lid_grommet():
    """A plain tapered eyelet (no mesh) that lines a drilled lid hole so a smooth
    net cup or tube seats without chafing. A conical tube + a rim lip and a
    small bottom retaining flange that snaps under the lid."""
    top_r = top_od / 2.0
    base_r = max(base_od / 2.0, top_r - 5.0)
    h = max(10.0, cup_h * 0.35)
    shell = _cone_shell(top_r, base_r, h, wall)
    lip = _rim_lip(top_r, lip_w, lip_h, h)
    body = shell.union(lip)
    # bottom snap flange: a thin annular lip flaring OUT at the base underside so
    # the grommet clips under the lid material. Solid ring, overlapped into wall.
    snap = (
        cq.Workplane("XY")
        .circle(base_r + max(1.0, lip_w * 0.6))
        .circle(max(0.5, base_r - wall - 0.5))
        .extrude(max(1.5, lip_h * 0.6))
    )
    body = body.union(snap)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "collar":
    result = build_collar()
elif target_part == "lid_grommet":
    result = build_lid_grommet()
else:  # "net_cup"
    result = build_net_cup()
