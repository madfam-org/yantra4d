"""
Water Meter Box Lid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Lids for the utility box that houses a domestic water meter. A stolen, cracked or
missing meter-box lid is a recurring municipal failure with three consequences at
once: the meter is exposed to frost and debris, the open box is a trip hazard and an
ankle trap on a verge or sidewalk, and the utility cannot read the meter without
clearing it out first. Replacement lids are cast or moulded to a per-manufacturer
box, so an older box frequently has no obtainable lid at all and ends up covered
with a paving slab.

Modes are dispatched via `target_part`:
  * "round_lid" — a round drop-in lid for a circular box bore, with a lift slot and
                  an optional reading port.
  * "rect_lid"  — a rectangular lid for a rectangular box mouth, the common domestic
                  meter pit.
  * "lock_tab"  — a separate locking tab that turns under the box lip, so the lid
                  cannot be flipped out by a mower or lifted casually.

Standards encoded (mm):
  Meter-box bores follow the meter and the pit, not one global standard, so the
  cartridge parameterises the BORE rather than pretending a single size exists. The
  common domestic sizes it covers:
    round bores  ~ 180, 230, 300, 380 mm (7, 9, 12, 15 in nominal pits)
    rect mouths  ~ 250x180, 300x230, 380x300 mm
  A drop-in lid needs a bearing ledge: the lid body sits ON the box rim, so the plug
  (the part that drops INTO the bore) is smaller than the flange by `ledge`.
  Lift slot: a hand-tool slot is typically ~50-90 mm long and 12-20 mm wide.

Watertightness strategy (a lid with a stepped plug as a closed manifold):
  Each lid is a SOLID flange with a plug unioned beneath it, the two OVERLAPPING
  volumetrically (a tangent kiss between flange and plug leaves a zero-area seam and
  reports as one non-watertight body). Every opening — lift slot, reading port,
  vents — is cut FULLY THROUGH and breaks out on both faces, so nothing is a blind
  pocket. A blind pocket is the dangerous failure here: it keeps the Euler
  characteristic at 2 and passes a naive watertight check while being wrong, which
  is why the local harness also reports genus.
  Every opening is clamped to sit inside the plug with a full wall of margin, so a
  large port at a small bore can never break out through the rim and shed a sliver.
  Fillets are wrapped in try/except so a crashed blend degrades to a sharp edge.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "round_lid"))
bore_dia = float(PARAM(lambda: bore_dia, 230.0))       # round box bore Ø (mm)
box_w = float(PARAM(lambda: box_w, 300.0))             # rect box mouth width (mm)
box_l = float(PARAM(lambda: box_l, 230.0))             # rect box mouth length (mm)
clearance = float(PARAM(lambda: clearance, 1.5))       # drop-in fit into the bore (mm)
ledge = float(PARAM(lambda: ledge, 12.0))              # bearing ledge on the box rim (mm)
lid_t = float(PARAM(lambda: lid_t, 10.0))              # lid plate thickness (mm)
plug_h = float(PARAM(lambda: plug_h, 14.0))            # how far the plug drops in (mm)
slot_l = float(PARAM(lambda: slot_l, 70.0))            # lift slot length (mm)
slot_w = float(PARAM(lambda: slot_w, 16.0))            # lift slot width (mm)
port_dia = float(PARAM(lambda: port_dia, 0.0))         # reading port Ø, 0 = none (mm)
rib_count = int(PARAM(lambda: rib_count, 4))           # stiffening ribs under the lid
tab_len = float(PARAM(lambda: tab_len, 55.0))          # locking tab length (mm)
tab_w = float(PARAM(lambda: tab_w, 22.0))              # locking tab width (mm)
screw_dia = float(PARAM(lambda: screw_dia, 6.0))       # locking tab pivot screw Ø (mm)

# Clamp so extreme UI values still build watertight.
bore_dia = max(120.0, min(bore_dia, 450.0))
box_w = max(120.0, min(box_w, 500.0))
box_l = max(120.0, min(box_l, 500.0))
clearance = max(0.0, min(clearance, 5.0))
ledge = max(5.0, min(ledge, 40.0))
lid_t = max(5.0, min(lid_t, 30.0))
plug_h = max(4.0, min(plug_h, 50.0))
slot_l = max(25.0, min(slot_l, 140.0))
slot_w = max(8.0, min(slot_w, 40.0))
port_dia = max(0.0, min(port_dia, 120.0))
rib_count = max(0, min(rib_count, 8))
tab_len = max(25.0, min(tab_len, 140.0))
tab_w = max(10.0, min(tab_w, 60.0))
screw_dia = max(3.0, min(screw_dia, 14.0))

MIN_WALL = 3.0   # the thinnest ring of material we will leave around any opening


# ── Shared helpers ───────────────────────────────────────────────────────────
def _through(body, cutter):
    """Subtract a cutter that is already sized to break out on both faces."""
    return body.cut(cutter)


def _slot_solid(cx, cy, length, width, z0, z_len):
    """A rounded-end slot cutter (a stadium: two end circles fused onto a bar).

    The three members are FUSED into one solid rather than merely collected into a
    cq.Compound. Cutting with a compound of OVERLAPPING solids does not raise and
    leaves the CAD solid count at 1, but it tessellates into a thousand loose shells
    and the exported mesh is not watertight. (A compound of *disjoint* cutters is
    fine — that is what the slot arrays elsewhere in the commons rely on. The
    difference is the overlap, so fuse whenever members intersect.)"""
    r = width / 2.0
    bar_l = max(0.1, length - width)
    solid = cq.Solid.makeBox(bar_l, width, z_len,
                             cq.Vector(cx - bar_l / 2.0, cy - r, z0))
    for sx in (-1.0, 1.0):
        cap = cq.Solid.makeCylinder(
            r, z_len, cq.Vector(cx + sx * (bar_l / 2.0), cy, z0)
        )
        solid = solid.fuse(cap)
    return solid


def _fit_slot(avail_half):
    """Clamp the lift slot so it stays inside the plug with a full wall of margin."""
    max_l = 2.0 * (avail_half - MIN_WALL)
    max_w = 2.0 * (avail_half - MIN_WALL)
    if max_l <= 2.0 or max_w <= 2.0:
        return 0.0, 0.0
    w = max(3.0, min(slot_w, max_w, max_l * 0.9))
    l = max(w + 0.5, min(slot_l, max_l))
    return l, w


# ── Part builders ─────────────────────────────────────────────────────────────
def build_round_lid():
    """A round drop-in lid: a flange that bears on the box rim, a plug that drops
    into the bore, a lift slot, an optional reading port and stiffening ribs."""
    plug_r = max(20.0, bore_dia / 2.0 - clearance)
    flange_r = plug_r + ledge
    ov = min(2.0, lid_t * 0.4)

    # Flange plate (the part you see and stand on).
    body = cq.Workplane("XY").circle(flange_r).extrude(lid_t)
    try:
        body = body.edges(">Z").chamfer(min(2.0, lid_t * 0.25))
    except Exception:
        pass

    # Plug hanging below, overlapping the flange volumetrically.
    plug = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -plug_h))
        .circle(plug_r)
        .extrude(plug_h + ov)
    )
    body = body.union(plug)

    # Lift slot geometry is resolved BEFORE the ribs, because the ribs have to be
    # laid out around it.
    l, w = _fit_slot(plug_r)

    # Stiffening ribs under the lid, radial, each overlapping the plug.
    #
    # Ribs are RING ribs, not full-diameter bars: each spans from outside the lift
    # slot out to the plug edge, on both sides. A full-diameter bar gets sliced in
    # two by the slot, and at 7+ ribs two of them straddle 90 degrees so the piece
    # trapped between the slot and the neighbouring rib detaches entirely — the lid
    # then exports as two bodies. Keeping every rib clear of the slot footprint
    # makes that structurally impossible rather than a function of rib count.
    if rib_count > 0:
        rib_t = max(3.0, lid_t * 0.4)
        rib_h = max(2.0, plug_h * 0.5)
        r_out = plug_r * 0.92
        # Start the rib outside the slot's own footprint (plus a wall).
        r_in = (max(l, w) / 2.0 + MIN_WALL) if l > 0.0 else 0.0
        if r_out - r_in > rib_t:
            ribs = None
            for i in range(rib_count):
                ang = 180.0 * i / rib_count
                for sx in (-1.0, 1.0):
                    x0 = r_in if sx > 0 else -r_out
                    bar = cq.Solid.makeBox(
                        r_out - r_in, rib_t, rib_h,
                        cq.Vector(x0, -rib_t / 2.0, -plug_h - rib_h + ov)
                    ).rotate((0, 0, 0), (0, 0, 1), ang)
                    ribs = bar if ribs is None else ribs.fuse(bar)
            if ribs is not None:
                body = body.union(cq.Workplane("XY").newObject([ribs]))

    # Lift slot, through the full lid (open both faces).
    if l > 0.0:
        body = _through(body, _slot_solid(0.0, 0.0, l, w, -plug_h - 30.0,
                                          plug_h + lid_t + 60.0))

    # Optional reading port, clamped inside the plug clear of the slot.
    if port_dia > 1.0:
        max_pr = plug_r - MIN_WALL - w / 2.0 - MIN_WALL
        pr = min(port_dia / 2.0, max(0.0, max_pr / 2.0))
        if pr > 1.0:
            cy = min(plug_r - MIN_WALL - pr, w / 2.0 + MIN_WALL + pr)
            if cy + pr < plug_r - MIN_WALL * 0.5:
                port = cq.Solid.makeCylinder(
                    pr, plug_h + lid_t + 60.0,
                    cq.Vector(0.0, cy, -plug_h - 30.0)
                )
                body = _through(body, port)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_rect_lid():
    """A rectangular lid for a rectangular meter pit mouth."""
    plug_w = max(20.0, box_w - 2.0 * clearance)
    plug_l = max(20.0, box_l - 2.0 * clearance)
    fl_w = plug_w + 2.0 * ledge
    fl_l = plug_l + 2.0 * ledge
    ov = min(2.0, lid_t * 0.4)

    body = cq.Workplane("XY").box(fl_w, fl_l, lid_t, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(8.0, ledge * 0.6))
    except Exception:
        pass

    plug = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -plug_h))
        .box(plug_w, plug_l, plug_h + ov, centered=(True, True, False))
    )
    body = body.union(plug)

    # Ribs across the short axis, under the plug.
    if rib_count > 0:
        rib_t = max(3.0, lid_t * 0.4)
        rib_h = max(2.0, plug_h * 0.5)
        usable = plug_l - 2.0 * MIN_WALL
        if usable > rib_count * rib_t:
            step = usable / float(rib_count + 1)
            # Parallel ribs are disjoint, but they are fused anyway so that the
            # union always receives a single solid — the same rule as elsewhere in
            # this file, applied uniformly rather than case by case.
            ribs = None
            for i in range(rib_count):
                cy = -usable / 2.0 + step * (i + 1)
                bar = cq.Solid.makeBox(
                    plug_w * 0.94, rib_t, rib_h,
                    cq.Vector(-plug_w * 0.47, cy - rib_t / 2.0,
                              -plug_h - rib_h + ov)
                )
                ribs = bar if ribs is None else ribs.fuse(bar)
            if ribs is not None:
                body = body.union(cq.Workplane("XY").newObject([ribs]))

    # Lift slot on the short axis, clamped inside the plug.
    half = min(plug_w, plug_l) / 2.0
    l, w = _fit_slot(half)
    if l > 0.0:
        body = _through(body, _slot_solid(0.0, 0.0, l, w, -plug_h - 30.0,
                                          plug_h + lid_t + 60.0))

    # Optional reading port.
    if port_dia > 1.0:
        max_pr = half - MIN_WALL - w / 2.0 - MIN_WALL
        pr = min(port_dia / 2.0, max(0.0, max_pr / 2.0))
        if pr > 1.0:
            cy = min(plug_l / 2.0 - MIN_WALL - pr, w / 2.0 + MIN_WALL + pr)
            if cy + pr < plug_l / 2.0 - MIN_WALL * 0.5:
                port = cq.Solid.makeCylinder(
                    pr, plug_h + lid_t + 60.0,
                    cq.Vector(0.0, cy, -plug_h - 30.0)
                )
                body = _through(body, port)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_lock_tab():
    """A locking tab that turns under the box lip so the lid cannot be flipped out
    by a mower or lifted casually. Pivots on a single screw through the lid."""
    t = max(4.0, min(lid_t * 0.8, 14.0))
    w = tab_w
    l = tab_len
    hub_r = max(screw_dia / 2.0 + MIN_WALL, w / 2.0)

    # Tab bar from the hub outward, with a rounded nose. The three members overlap,
    # so they are FUSED into a single solid — a compound of overlapping solids
    # tessellates into loose shells (see _slot_solid).
    bar = cq.Solid.makeBox(l, w, t, cq.Vector(0.0, -w / 2.0, 0.0))
    nose = cq.Solid.makeCylinder(w / 2.0, t, cq.Vector(l, 0.0, 0.0))
    hub = cq.Solid.makeCylinder(hub_r, t, cq.Vector(0.0, 0.0, 0.0))
    body = cq.Workplane("XY").newObject([bar.fuse(nose).fuse(hub)])

    # Pivot screw hole through the hub, open both faces.
    screw = cq.Solid.makeCylinder(
        screw_dia / 2.0, t + 20.0, cq.Vector(0.0, 0.0, -10.0)
    )
    body = _through(body, screw)

    # A lightening slot along the bar, clamped well inside the material so it can
    # never break out through an edge.
    sl_w = max(2.0, min(w * 0.35, w - 2.0 * MIN_WALL))
    sl_start = hub_r + MIN_WALL + sl_w / 2.0
    sl_end = l - MIN_WALL - sl_w / 2.0
    if sl_end - sl_start > sl_w:
        body = _through(
            body,
            _slot_solid((sl_start + sl_end) / 2.0, 0.0,
                        sl_end - sl_start, sl_w, -10.0, t + 20.0)
        )

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "round_lid": build_round_lid,
    "rect_lid": build_rect_lid,
    "lock_tab": build_lock_tab,
}

result = _dispatch.get(target_part, build_round_lid)()
