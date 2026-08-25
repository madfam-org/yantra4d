"""
PV Cable Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Cable management for photovoltaic strings. PV lead (4-6 mm2 double-insulated solar
cable) runs are dressed along a module frame lip, a rail, or bundled to each other.
The cable bore lands on the real PV lead outside diameter series so a printed clip
grips the cable you actually have, and the frame jaw lands on real anodised module
frame lip thicknesses.

Modes are dispatched via `target_part`:
  * "frame_clip"  — a C-jaw that hooks over a module frame lip and carries one or
                    two cable channels; the workhorse for dressing leads along the
                    long edge of a panel.
  * "rail_clip"   — a screw-mount saddle that holds a cable bundle down onto a rail
                    or purlin.
  * "twin_bundle" — an open figure-of-eight that pairs the + and - leads of a string
                    so they run together and enclose minimal loop area.

Standards encoded (mm):
  PV lead Ø: 4 mm2 ~ 5.5-6.0, 6 mm2 ~ 6.5-7.2 (double-insulated H1Z2Z2-K family).
  The cable series here spans 5.0-7.0 nominal, matching the published mc4-holder
  `cable_dia` range so a clip and a strain-relief block agree on the same lead.
  Module frame lip thickness: 1.5-3.0 typical anodised aluminium extrusion wall;
  the jaw spans 1.0-6.0 so it also fits a rail flange or a doubled edge.

Watertightness strategy (open jaws and channels as closed manifolds):
  Every part is a SOLID blank from which channels and the jaw slot are cut. A cable
  channel is cut with a mouth slot that OPENS it to the outside, so it is never a
  sealed internal void; a C-jaw is cut by a rectangular slot that opens to one face,
  leaving one connected solid rather than two pieces. Stacked bodies OVERLAP
  volumetrically (never a tangent kiss, which leaves a zero-area seam). Fillets are
  applied to the blank BEFORE any cut, and are wrapped in try/except so a crashed
  fillet degrades to a sharp edge instead of aborting the build.

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


# ── Standard dimensions (mm) ─────────────────────────────────────────────────
PV_LEAD_D = 6.5      # 6 mm2 H1Z2Z2-K solar lead Ø (matches mc4-holder cable_dia)
FRAME_LIP_T = 2.0    # typical anodised module frame lip thickness


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "frame_clip"))
cable_dia = float(PARAM(lambda: cable_dia, PV_LEAD_D))    # PV lead Ø (mm)
cable_count = int(PARAM(lambda: cable_count, 2))          # leads carried
clearance = float(PARAM(lambda: clearance, 0.4))          # slop per side (mm)
wall = float(PARAM(lambda: wall, 2.6))                    # clip wall (mm)
depth = float(PARAM(lambda: depth, 14.0))                 # clip length along cable (mm)
lip_t = float(PARAM(lambda: lip_t, FRAME_LIP_T))          # module frame lip thickness (mm)
jaw_depth = float(PARAM(lambda: jaw_depth, 12.0))         # how far the jaw reaches over the lip (mm)
mouth = float(PARAM(lambda: mouth, 0.70))                 # channel mouth as a fraction of bore Ø
screw_dia = float(PARAM(lambda: screw_dia, 4.0))          # mount screw Ø (mm)

# Clamp so extreme UI values still build watertight.
cable_dia = max(3.0, min(cable_dia, 12.0))
cable_count = max(1, min(cable_count, 4))
clearance = max(0.0, min(clearance, 1.2))
wall = max(1.6, min(wall, 6.0))
depth = max(6.0, min(depth, 40.0))
lip_t = max(1.0, min(lip_t, 6.0))
jaw_depth = max(5.0, min(jaw_depth, 30.0))
mouth = max(0.45, min(mouth, 0.90))
screw_dia = max(2.0, min(screw_dia, 8.0))


# ── Derived geometry ─────────────────────────────────────────────────────────
def _bore_r():
    """Cable channel radius (lead OD + clearance per side)."""
    return cable_dia / 2.0 + clearance


def _channel_pitch(bore_r):
    """Center distance between adjacent cable channels, always leaving a real web
    of material between them (never tangent, which would sever the part)."""
    return 2.0 * bore_r + max(1.2, wall * 0.6)


def _cut_channel(body, cx, cz, bore_r, length, open_up=True):
    """Cut a cable channel along Y at (cx, cz), plus a mouth slot that opens it to
    the +Z (or -Z) face so the channel is never a sealed internal void."""
    bore = (
        cq.Workplane("XZ")
        .workplane(offset=-length / 2.0 - 1.0)
        .center(cx, cz)
        .circle(bore_r)
        .extrude(length + 2.0)
    )
    body = body.cut(bore)

    # Mouth: a slot narrower than the bore so the cable clicks in and is retained.
    mw = max(0.8, 2.0 * bore_r * mouth)
    # Reach well past the outer surface in the opening direction.
    reach = 4.0 * bore_r + wall + 10.0
    z0 = cz if open_up else cz - reach
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0.0, z0))
        .box(mw, length + 2.0, reach, centered=(True, True, False))
    )
    return body.cut(slot)


# ── Part builders ─────────────────────────────────────────────────────────────
def build_frame_clip():
    """A C-jaw hooking over a module frame lip, carrying the cable channels on its
    outer face. The jaw slot opens to one side, so the part stays one solid."""
    bore_r = _bore_r()
    pitch = _channel_pitch(bore_r)

    jaw_gap = lip_t + 2.0 * clearance
    # Jaw block: back leg + throat + front leg, all one blank; the throat is cut.
    jaw_w = 2.0 * wall + jaw_gap
    # Channel bank sits on top of the jaw; its width must span every channel.
    bank_w = (cable_count - 1) * pitch + 2.0 * bore_r + 2.0 * wall
    body_w = max(jaw_w, bank_w)
    jaw_h = jaw_depth + wall
    bank_h = 2.0 * bore_r + 2.0 * wall
    overlap = min(1.5, wall * 0.6)

    # Jaw blank (a solid box; the throat slot is cut next).
    jaw = cq.Workplane("XY").box(body_w, depth, jaw_h, centered=(True, True, False))
    try:
        jaw = jaw.edges("|Y").fillet(min(1.5, wall * 0.5))
    except Exception:
        pass

    # Channel bank rises from the jaw, overlapping into it volumetrically.
    bank = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, jaw_h - overlap))
        .box(body_w, depth, bank_h + overlap, centered=(True, True, False))
    )
    body = jaw.union(bank)

    # Cut the jaw throat: a slot opening downward (-Z) that swallows the frame lip.
    # Centered on the blank, it leaves a leg of `wall` on each side.
    throat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(jaw_gap, depth + 2.0, jaw_depth + 1.0, centered=(True, True, False))
    )
    body = body.cut(throat)

    # Cable channels along the top of the bank, mouths opening up.
    x0 = -(cable_count - 1) * pitch / 2.0
    cz = jaw_h + wall + bore_r
    for i in range(cable_count):
        body = _cut_channel(body, x0 + i * pitch, cz, bore_r, depth, open_up=True)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_rail_clip():
    """A screw-mount saddle: a base plate with a channel bank, screwed to a rail or
    purlin. Screw holes clear both faces so nothing is a blind pocket."""
    bore_r = _bore_r()
    pitch = _channel_pitch(bore_r)

    bank_w = (cable_count - 1) * pitch + 2.0 * bore_r + 2.0 * wall
    # End pads carry the screws, kept clear of the bank and of the plate edge.
    pad = screw_dia / 2.0 + 3.0
    base_w = bank_w + 2.0 * (2.0 * pad)
    base_t = max(2.4, wall)
    bank_h = 2.0 * bore_r + 2.0 * wall
    overlap = min(1.2, base_t * 0.6)

    base = cq.Workplane("XY").box(base_w, depth, base_t, centered=(True, True, False))
    try:
        base = base.edges("|Z").fillet(min(2.5, wall))
    except Exception:
        pass

    bank = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_t - overlap))
        .box(bank_w, depth, bank_h + overlap, centered=(True, True, False))
    )
    try:
        bank = bank.edges("|Y").fillet(min(1.5, wall * 0.5))
    except Exception:
        pass
    body = base.union(bank)

    # Screws through the end pads, open both faces.
    for sx in (-1.0, 1.0):
        cx = sx * (bank_w / 2.0 + pad)
        scr = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0.0, -1.0))
            .circle(screw_dia / 2.0)
            .extrude(base_t + 2.0)
        )
        body = body.cut(scr)

    # Cable channels, mouths opening up.
    x0 = -(cable_count - 1) * pitch / 2.0
    cz = base_t + wall + bore_r
    for i in range(cable_count):
        body = _cut_channel(body, x0 + i * pitch, cz, bore_r, depth, open_up=True)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_twin_bundle():
    """An open figure-of-eight that pairs the + and - leads of a string. Two stacked
    channels, mouths opening to OPPOSITE faces so each lead clicks in from its own
    side and the web between them is never severed."""
    bore_r = _bore_r()
    web = max(1.2, wall * 0.6)

    body_w = 2.0 * bore_r + 2.0 * wall
    body_h = 4.0 * bore_r + 2.0 * wall + web
    body = cq.Workplane("XY").box(body_w, depth, body_h, centered=(True, True, False))
    try:
        body = body.edges("|Y").fillet(min(2.0, wall * 0.7))
    except Exception:
        pass

    z_low = wall + bore_r
    z_high = z_low + 2.0 * bore_r + web

    # Lower channel opens DOWN, upper channel opens UP: opposite mouths keep the
    # central web intact and give a true figure-of-eight snap.
    body = _cut_channel(body, 0.0, z_low, bore_r, depth, open_up=False)
    body = _cut_channel(body, 0.0, z_high, bore_r, depth, open_up=True)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "frame_clip": build_frame_clip,
    "rail_clip": build_rail_clip,
    "twin_bundle": build_twin_bundle,
}

result = _dispatch.get(target_part, build_frame_clip)()
