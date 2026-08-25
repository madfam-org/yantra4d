"""
Stormwater Grate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The missing surface element of the commons drainage chain. `downspout-adapter` takes
roof water out of a rectangular spout into a round outlet, and `drain-trap` seals the
run against sewer gas — but nothing published covers the point where water actually
ENTERS the system: the grate. A grate is the one drainage part that is simultaneously
a hydraulic aperture, a pedestrian surface and a debris filter, and it is the part
that is missing, cracked or stolen most often.

Modes are dispatched via `target_part`:
  * "slot_grate"  — a rectangular grate with a parallel slot array, the standard
                    channel/trench grate; slot pitch and width are parameters.
  * "round_grate" — a round drop-in grate whose spigot matches the published
                    downspout-adapter / drain-trap outlet bore series.
  * "leaf_dome"   — a domed leaf guard that sits over the grate and keeps leaf fall
                    out of the throat, the usual reason a gully backs up.

Standards encoded (mm):
  Drop-in bore series (shared with downspout-adapter `outlet_dia` and drain-trap):
    50, 68, 75, 87, 100, 110 — the common round downpipe / drain sizes. The default
    68 is the standard round rainwater downpipe.
  Slot geometry: a bicycle-safe grate needs slots ACROSS the direction of travel, or
  slots no wider than ~13 mm if run along it; heel-safe pedestrian guidance keeps a
  slot under ~13 mm as well. The slot width range here spans 4-30 mm so the part can
  also be authored as a coarse yard grate, and the manifest warns above 13 mm.

Watertightness strategy (a patterned boolean array as a closed manifold):
  The grate is a SOLID plate from which the slot array is cut. Two things make an
  array like this fail, and both are handled explicitly rather than hoped over:
    1. A slot that lands flush with the frame edge leaves a knife-edge sliver or
       severs the bar entirely. Every slot is therefore clamped to sit inside a
       margin of at least one bar width from the frame, and the SLOT COUNT is
       derived from the space actually available rather than taken from the UI.
    2. A pitch smaller than the slot width leaves zero bar between slots, which
       merges every slot into one void and drops the frame's interior. The pitch is
       floored at `slot_w + min_bar` so a bar always survives.
  Every slot is cut fully through and breaks out on both faces, so no slot is a blind
  pocket (a blind pocket keeps Euler characteristic at 2 and silently passes a
  watertight check while being geometrically wrong). Stacked bodies OVERLAP
  volumetrically. Fillets are wrapped in try/except so a crashed blend degrades to a
  sharp edge rather than aborting the build.

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


# ── Drop-in outlet bore series (mm) ──────────────────────────────────────────
# Shared with the published downspout-adapter (`outlet_dia`) and drain-trap.
OUTLET_SERIES = {
    "d50": 50.0,
    "d68": 68.0,     # standard round rainwater downpipe
    "d75": 75.0,
    "d87": 87.0,
    "d100": 100.0,
    "d110": 110.0,
}


def outlet_d(name):
    """Drop-in outlet diameter (mm), defaulting to the 68 mm downpipe."""
    return OUTLET_SERIES.get(name, OUTLET_SERIES["d68"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "slot_grate"))
frame_w = float(PARAM(lambda: frame_w, 150.0))          # grate footprint width (mm)
frame_l = float(PARAM(lambda: frame_l, 250.0))          # grate footprint length (mm)
plate_t = float(PARAM(lambda: plate_t, 8.0))            # grate plate thickness (mm)
slot_w = float(PARAM(lambda: slot_w, 10.0))             # slot width (mm)
slot_pitch = float(PARAM(lambda: slot_pitch, 18.0))     # slot centre pitch (mm)
rim = float(PARAM(lambda: rim, 10.0))                   # solid frame margin (mm)
outlet = str(PARAM(lambda: outlet, "d68"))              # drop-in bore series key
clearance = float(PARAM(lambda: clearance, 0.6))        # spigot fit into the bore (mm)
spigot_len = float(PARAM(lambda: spigot_len, 20.0))     # spigot depth into the pipe (mm)
dome_rise = float(PARAM(lambda: dome_rise, 0.45))       # leaf dome height / radius
lip_drop = float(PARAM(lambda: lip_drop, 12.0))         # leaf dome skirt drop (mm)

# Clamp so extreme UI values still build watertight.
frame_w = max(60.0, min(frame_w, 600.0))
frame_l = max(60.0, min(frame_l, 900.0))
plate_t = max(3.0, min(plate_t, 25.0))
slot_w = max(4.0, min(slot_w, 30.0))
slot_pitch = max(6.0, min(slot_pitch, 60.0))
rim = max(4.0, min(rim, 40.0))
clearance = max(0.0, min(clearance, 2.0))
spigot_len = max(6.0, min(spigot_len, 60.0))
dome_rise = max(0.15, min(dome_rise, 0.85))
lip_drop = max(4.0, min(lip_drop, 40.0))


# ── Slot array layout ────────────────────────────────────────────────────────
MIN_BAR = 2.0    # the thinnest bar of material we will ever leave between slots


def _slot_layout(span, length_avail):
    """Lay out slots across `span` (the open width, frame margins already removed).

    Returns (positions, width). The COUNT is derived from the space available rather
    than taken from the UI, and the pitch is floored so a bar always survives — those
    two rules are what keep the array from merging into one void or shedding slivers
    at the frame edge."""
    if span <= 0.0 or length_avail <= 0.0:
        return [], 0.0
    w = min(slot_w, max(1.0, span - 2.0 * MIN_BAR))
    if w <= 0.5:
        return [], 0.0
    pitch = max(slot_pitch, w + MIN_BAR)
    # Usable centre band: first and last slot must keep a full bar to the frame.
    lo = -span / 2.0 + MIN_BAR + w / 2.0
    hi = +span / 2.0 - MIN_BAR - w / 2.0
    if hi < lo:
        return [0.0], w      # only room for a single central slot
    n = int(math.floor((hi - lo) / pitch)) + 1
    n = max(1, min(n, 200))
    used = (n - 1) * pitch
    start = -used / 2.0
    return [start + i * pitch for i in range(n)], w


def _cut_slots(body, positions, w, cut_len, z0, z_len, along_x):
    """Cut the slot array fully through the plate (open on both faces).

    All the slot cutters are collected into ONE compound and subtracted in a single
    boolean. Cutting them one at a time re-evaluates the whole solid on every slot,
    which is O(n^2) in practice: a 900 mm grate on a 6 mm pitch (145 slots) took 66 s
    slot-by-slot and about a second as one compound. The cutters are disjoint by
    construction — the pitch is floored at slot_w + MIN_BAR — so unioning them is
    exact, not an approximation."""
    if not positions or w <= 0.0:
        return body
    solids = []
    for p in positions:
        if along_x:
            sw, sl, cx, cy = w, cut_len, p, 0.0
        else:
            sw, sl, cx, cy = cut_len, w, 0.0, p
        solids.append(
            cq.Solid.makeBox(sw, sl, z_len,
                             cq.Vector(cx - sw / 2.0, cy - sl / 2.0, z0))
        )
    return body.cut(cq.Workplane("XY").newObject([cq.Compound.makeCompound(solids)]))


# ── Part builders ─────────────────────────────────────────────────────────────
def build_slot_grate():
    """A rectangular grate with a parallel slot array — the standard trench/channel
    grate. Slots run across the short axis, which is the bicycle-safe orientation."""
    body = cq.Workplane("XY").box(frame_w, frame_l, plate_t, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(4.0, rim * 0.4))
    except Exception:
        pass

    # Open area available after the solid frame margin, on both axes.
    open_l = frame_l - 2.0 * rim
    open_w = frame_w - 2.0 * rim
    if open_l > 2.0 * MIN_BAR and open_w > 1.0:
        # Slots are spaced ALONG the length and run ACROSS the width.
        positions, w = _slot_layout(open_l, open_w)
        body = _cut_slots(body, positions, w, open_w, -1.0, plate_t + 2.0,
                          along_x=False)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_round_grate():
    """A round drop-in grate on the published outlet bore series: a disc of slots
    over a spigot that plugs into a downpipe or gully throat."""
    d = outlet_d(outlet)
    spig_r = d / 2.0 - clearance          # spigot slips INTO the bore
    spig_r = max(3.0, spig_r)
    # The flange must overhang the bore so the grate sits on the pipe rim.
    flange_r = max(d / 2.0 + rim, spig_r + rim)
    ov = min(1.5, plate_t * 0.5)

    # Flange plate.
    body = cq.Workplane("XY").circle(flange_r).extrude(plate_t)
    try:
        body = body.edges(">Z").chamfer(min(1.5, plate_t * 0.3))
    except Exception:
        pass

    # Spigot hanging below, overlapping the flange volumetrically.
    spig = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -spigot_len))
        .circle(spig_r)
        .extrude(spigot_len + ov)
    )
    body = body.union(spig)

    # Hollow the spigot so water passes: a bore open at the bottom face and up into
    # the slot field, so it is never a sealed void.
    inner_r = max(1.5, spig_r - max(2.0, plate_t * 0.4))
    throat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -spigot_len - 1.0))
        .circle(inner_r)
        .extrude(spigot_len + 1.0)
    )
    body = body.cut(throat)

    # Slot array across the throat, cut fully through the flange, batched into one
    # boolean (see _cut_slots for why).
    span = 2.0 * inner_r
    positions, w = _slot_layout(span, span)
    cutters = []
    for p in positions:
        # Chord length at each slot position keeps the cut inside the throat circle.
        half = abs(p) + w / 2.0
        if half >= inner_r:
            continue
        chord = 2.0 * math.sqrt(max(0.0, inner_r * inner_r - half * half))
        if chord <= 0.5:
            continue
        cutters.append(
            cq.Solid.makeBox(chord, w, plate_t + 2.0,
                             cq.Vector(-chord / 2.0, p - w / 2.0, -1.0))
        )
    if cutters:
        body = body.cut(
            cq.Workplane("XY").newObject([cq.Compound.makeCompound(cutters)])
        )

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_leaf_dome():
    """A domed leaf guard that sits over a gully or downpipe throat. Leaf fall, not
    silt, is what actually backs a gully up, and a dome sheds it instead of catching
    it. Slots are cut through the dome wall so water still passes."""
    d = outlet_d(outlet)
    spig_r = max(3.0, d / 2.0 - clearance)
    base_r = spig_r + max(3.0, rim * 0.6)
    rise = max(6.0, base_r * dome_rise)
    t = max(2.0, min(plate_t, base_r * 0.5))

    # Dome as ONE revolved profile with a small FLAT apex. A profile that runs to a
    # point on the rotation axis revolves into a pole singularity and the mesh comes
    # back as two shells; a fraction of a millimetre of plateau avoids it entirely.
    apex_r = max(0.6, base_r * 0.05)
    prof = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(base_r, 0)
        .lineTo(base_r, lip_drop * 0.0 + t)
        .threePointArc((base_r * 0.72, t + rise * 0.72), (apex_r, t + rise))
        .lineTo(0, t + rise)
        .close()
    )
    body = prof.revolve(360, (0, 0, 0), (0, 1, 0))

    # Skirt hanging below the dome, so it locates on the throat.
    skirt = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -lip_drop))
        .circle(spig_r + max(1.5, t * 0.6))
        .extrude(lip_drop + t)
    )
    body = body.union(skirt)

    # Central throat, open bottom to top-inside so the dome is a shell, not a slug.
    inner_r = max(1.5, spig_r - max(1.5, t * 0.6))
    throat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -lip_drop - 1.0))
        .circle(inner_r)
        .extrude(lip_drop + t + 1.0)
    )
    body = body.cut(throat)

    # Radial inlet slots around the skirt: water enters at the sides, leaves stay out.
    n = max(3, min(12, int(2.0 * math.pi * spig_r / max(6.0, slot_w + MIN_BAR))))
    w = max(2.0, min(slot_w, (2.0 * math.pi * spig_r) / (n * 2.2)))
    h = max(2.0, min(lip_drop * 0.6, lip_drop - 2.0))
    reach = 4.0 * base_r + 20.0
    cutters = []
    for i in range(n):
        ang = 360.0 * i / n
        box = cq.Solid.makeBox(
            reach, w, h, cq.Vector(-reach / 2.0, -w / 2.0, -lip_drop + 1.0)
        )
        cutters.append(box.rotate((0, 0, 0), (0, 0, 1), ang))
    if cutters:
        # One boolean rather than n (see _cut_slots). The radial cutters DO meet at
        # the axis, but a compound cut is a union-then-subtract, so overlap is fine.
        body = body.cut(
            cq.Workplane("XY").newObject([cq.Compound.makeCompound(cutters)])
        )

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "slot_grate": build_slot_grate,
    "round_grate": build_round_grate,
    "leaf_dome": build_leaf_dome,
}

result = _dispatch.get(target_part, build_slot_grate)()
