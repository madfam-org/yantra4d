"""
Bollard Cap — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Caps that close the open top of a steel pipe bollard. An uncapped bollard fills with
rainwater, freezes, rusts from the inside and stains the pavement below; the factory
cap is usually the first part to go missing after a vehicle strike. The bore lands on
real steel pipe outside diameters (NPS schedule 40, the sizes bollards are actually
made from), which is the same pipe-OD-series interface the published pipe-clip and
pipe-fitting families use — one diameter convention across the commons.

Modes are dispatched via `target_part`:
  * "dome_cap"    — a domed slip-over cap: the classic rounded bollard top that sheds
                    water and has no flat face to pool on.
  * "flat_cap"    — a flat slip-over cap with a chamfered rim, for bollards under a
                    sign or a light fitting that needs a flat seat.
  * "reflect_cap" — a flat cap with a recessed band around the skirt to take a
                    retroreflective tape wrap, plus drain slots.

Standards encoded (mm):
  NPS schedule 40 steel pipe OD (the bollard sizes):
    NPS 3   = 3.500 in = 88.90
    NPS 4   = 4.500 in = 114.30
    NPS 5   = 5.563 in = 141.30
    NPS 6   = 6.625 in = 168.28
    NPS 8   = 8.625 in = 219.08
  A slip-over cap's skirt bore = pipe OD + clearance; the skirt hangs past the cut
  edge of the pipe so the joint is shadowed and water cannot track in.

Watertightness strategy (a hollow cap as a closed manifold):
  Each cap is a SOLID revolve/blank from which the skirt bore is cut as a single
  cylinder open to the bottom face — an open-bottomed cup, never a sealed internal
  void. Drain slots are cut through the skirt wall from outside to the bore, so they
  connect two already-open regions rather than puncturing into a cavity. The dome is
  built as one revolved profile (not a sphere union, which would leave a tangent
  seam), and the reflect band is a shallow groove cut into the outside of the skirt.
  Fillets/chamfers are wrapped in try/except so a crashed blend degrades to a sharp
  edge instead of aborting the build.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Steel pipe outside diameters (mm), NPS schedule 40 ───────────────────────
PIPE_OD = {
    "nps_3": 88.90,     # 3.500 in
    "nps_4": 114.30,    # 4.500 in
    "nps_5": 141.30,    # 5.563 in
    "nps_6": 168.28,    # 6.625 in
    "nps_8": 219.08,    # 8.625 in
}


def pipe_od(name):
    """Bollard pipe outside diameter (mm), defaulting to NPS 4."""
    return PIPE_OD.get(name, PIPE_OD["nps_4"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "dome_cap"))
pipe = str(PARAM(lambda: pipe, "nps_4"))                 # bollard pipe spec key
clearance = float(PARAM(lambda: clearance, 0.8))         # slip fit over the pipe OD (mm)
wall = float(PARAM(lambda: wall, 4.0))                   # cap wall (mm)
skirt = float(PARAM(lambda: skirt, 30.0))                # how far the skirt hangs down (mm)
dome_rise = float(PARAM(lambda: dome_rise, 0.45))        # dome height as a fraction of radius
band_depth = float(PARAM(lambda: band_depth, 1.2))       # reflective band recess depth (mm)
band_width = float(PARAM(lambda: band_width, 50.0))      # reflective band height (mm)
drain_count = int(PARAM(lambda: drain_count, 4))         # drain slots around the skirt
drain_w = float(PARAM(lambda: drain_w, 6.0))             # drain slot width (mm)

# Clamp so extreme UI values still build watertight.
clearance = max(0.0, min(clearance, 3.0))
wall = max(2.0, min(wall, 10.0))
skirt = max(8.0, min(skirt, 90.0))
dome_rise = max(0.15, min(dome_rise, 0.90))
band_depth = max(0.4, min(band_depth, 3.0))
drain_count = max(0, min(drain_count, 8))
drain_w = max(2.0, min(drain_w, 20.0))


# ── Derived radii ────────────────────────────────────────────────────────────
def _radii():
    """Return (bore_r, out_r): skirt bore radius (pipe OD + clearance) and cap
    outer radius. Clearance is applied on diameter, as a slip fit is quoted."""
    bore_r = pipe_od(pipe) / 2.0 + clearance
    out_r = bore_r + wall
    return bore_r, out_r


def _band_geometry(bore_r):
    """Reflective band recess: clamp its depth below the skirt wall so the band can
    never cut through into the bore (which would open the skirt into a ring of
    disconnected slivers), and clamp its height inside the skirt."""
    depth = min(band_depth, wall * 0.5)
    height = max(2.0, min(band_width, skirt - 4.0))
    return depth, height


def _cut_drains(body, bore_r, out_r):
    """Cut drain slots through the skirt wall, open at the bottom face. Each slot
    spans from inside the bore to outside the cap, so it joins two already-open
    regions — it never punctures into a sealed cavity."""
    if drain_count <= 0:
        return body
    # Keep slots narrow enough that the skirt survives as a connected ring: the
    # total slot arc must leave real material between adjacent slots.
    max_w = (2.0 * 3.14159265 * bore_r) / (drain_count * 2.2)
    w = max(1.5, min(drain_w, max_w))
    h = max(2.0, min(skirt * 0.5, skirt - 3.0))
    reach = 2.0 * out_r + 10.0
    for i in range(drain_count):
        ang = 360.0 * i / drain_count
        slot = (
            cq.Workplane("XY")
            .box(reach, w, h, centered=(True, True, False))
            .rotate((0, 0, 0), (0, 0, 1), ang)
        )
        body = body.cut(slot)
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_dome_cap():
    """A domed slip-over cap, revolved as one profile so the dome meets the skirt
    tangentially in a single face rather than as a unioned sphere."""
    bore_r, out_r = _radii()
    rise = max(3.0, out_r * dome_rise)

    # Revolve profile in XZ (x = radius, z = height), swept 360 about Z.
    # Outer wall rises from z=0 to the shoulder, then a dome arc closes it.
    #
    # The dome deliberately ends on a small FLAT apex (apex_r) rather than running
    # to a point on the rotation axis. A profile that touches the axis at a single
    # point revolves into a pole singularity: the mesh comes back as two shells and
    # fails watertight. A few tenths of a millimetre of plateau costs nothing
    # visually and keeps the cap a single closed manifold.
    apex_r = max(0.6, out_r * 0.04)
    prof = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(out_r, 0)                      # bottom face, out to the rim
        .lineTo(out_r, skirt)                  # up the outside of the skirt
        .threePointArc((out_r * 0.72, skirt + rise * 0.72), (apex_r, skirt + rise))
        .lineTo(0, skirt + rise)               # flat apex, back to the axis
        .close()
    )
    body = prof.revolve(360, (0, 0, 0), (0, 1, 0))

    # Hollow it: the skirt bore, open to the bottom face only.
    bore = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .circle(bore_r)
        .extrude(skirt + 1.0)
    )
    body = body.cut(bore)
    body = _cut_drains(body, bore_r, out_r)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_flat_cap():
    """A flat slip-over cap with a chamfered rim: a flat seat for a sign or light."""
    bore_r, out_r = _radii()
    top_t = max(2.0, wall)
    total_h = skirt + top_t

    body = cq.Workplane("XY").circle(out_r).extrude(total_h)
    # Chamfer the top rim so rain runs off and the edge is not a burr.
    try:
        body = body.edges(">Z").chamfer(min(wall * 0.6, top_t * 0.6, 3.0))
    except Exception:
        pass

    bore = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .circle(bore_r)
        .extrude(skirt + 1.0)
    )
    body = body.cut(bore)
    body = _cut_drains(body, bore_r, out_r)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_reflect_cap():
    """A flat cap with a recessed band around the skirt to take a retroreflective
    tape wrap, so the tape sits below the surface and is not scuffed off."""
    bore_r, out_r = _radii()
    top_t = max(2.0, wall)
    total_h = skirt + top_t
    depth, height = _band_geometry(bore_r)

    body = cq.Workplane("XY").circle(out_r).extrude(total_h)
    try:
        body = body.edges(">Z").chamfer(min(wall * 0.6, top_t * 0.6, 3.0))
    except Exception:
        pass

    # Recessed band: an annular groove cut into the OUTSIDE of the skirt. Cut as
    # (big cylinder - small cylinder) so it never reaches the bore.
    band_z0 = max(1.0, (skirt - height) / 2.0)
    band_h = min(height, skirt - band_z0 - 1.0)
    if band_h > 0.5 and depth > 0.05:
        ring = (
            cq.Workplane("XY")
            .workplane(offset=band_z0)
            .circle(out_r + 1.0)
            .circle(out_r - depth)
            .extrude(band_h)
        )
        body = body.cut(ring)

    bore = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .circle(bore_r)
        .extrude(skirt + 1.0)
    )
    body = body.cut(bore)
    body = _cut_drains(body, bore_r, out_r)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "dome_cap": build_dome_cap,
    "flat_cap": build_flat_cap,
    "reflect_cap": build_reflect_cap,
}

result = _dispatch.get(target_part, build_dome_cap)()
