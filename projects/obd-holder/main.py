"""
OBD-II / Fuse Tap Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Under-dash organisers for vehicle electronics: a cradle that holds an OBD-II
diagnostic dongle out of the footwell, a block that organises spare blade fuses
and fuse taps, and a panel bracket with the trapezoidal OBD-II connector opening
for relocating the diagnostic port.

  * "dongle_holder"  — a pocket cradle sized to an ELM327-class OBD-II dongle
                       body, with a strap slot and screw ears
                       (target_part == "dongle_holder").
  * "fuse_organizer" — a block with a row of ATO/ATC pockets and a row of Mini
                       pockets to store spare blade fuses and taps
                       (target_part == "fuse_organizer").
  * "obd_bracket"    — a mounting plate with the SAE J1962 trapezoidal connector
                       opening and screw holes, to panel-mount / relocate the
                       OBD-II port (target_part == "obd_bracket").

Real dimensions:
  - OBD-II (SAE J1962 Type A) connector face ≈ 25 mm wide × 13 mm tall trapezoid
    (~11 mm at the short parallel side); dongle body ≈ 48 × 25 × 24 mm (varies).
  - ATO/ATC blade fuse: body ≈ 19.1 mm wide × 5.1 mm thick; blade pitch ≈ 9.5 mm.
  - Mini (APM/ATM) fuse: body ≈ 10.9 mm wide × 3.6 mm thick; blade pitch ≈ 5.1 mm.

Watertight strategy (the brief's pocket rule): each holder is a SOLID block with
pockets cut DOWN from the top face (open to outside → vented, no trapped void).
The OBD bracket is a solid plate with a trapezoidal through-opening (open both
faces) and through screw holes. Screw ears and straps are unioned onto the block
overlapping into shared material. Fillets on clean blanks BEFORE cutting. Each
result is one manifold solid.

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
target_part = str(PARAM(lambda: target_part, "dongle_holder"))  # dongle_holder | fuse_organizer | obd_bracket

dongle_w = float(PARAM(lambda: dongle_w, 48.0))   # OBD dongle body width (mm)
dongle_h = float(PARAM(lambda: dongle_h, 25.0))   # OBD dongle body height (mm)
dongle_d = float(PARAM(lambda: dongle_d, 24.0))   # OBD dongle body depth (mm)
wall = float(PARAM(lambda: wall, 2.6))            # cradle / block wall thickness (mm)
clearance = float(PARAM(lambda: clearance, 0.5))  # pocket slip clearance (per side)
obd_w = float(PARAM(lambda: obd_w, 25.0))         # OBD connector face width (mm)
obd_h = float(PARAM(lambda: obd_h, 13.0))         # OBD connector face height (mm)
ato_count = int(float(PARAM(lambda: ato_count, 4)))   # number of ATO fuse pockets
mini_count = int(float(PARAM(lambda: mini_count, 4)))  # number of Mini fuse pockets
screw_d = float(PARAM(lambda: screw_d, 4.2))      # mounting screw hole (mm)

# ── Clamps ───────────────────────────────────────────────────────────────────
dongle_w = max(25.0, min(dongle_w, 90.0))
dongle_h = max(12.0, min(dongle_h, 60.0))
dongle_d = max(12.0, min(dongle_d, 60.0))
wall = max(1.6, min(wall, 6.0))
clearance = max(0.0, min(clearance, 1.5))
obd_w = max(18.0, min(obd_w, 40.0))
obd_h = max(9.0, min(obd_h, 25.0))
ato_count = max(1, min(ato_count, 10))
mini_count = max(0, min(mini_count, 10))
screw_d = max(2.5, min(screw_d, 8.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _trapezoid(top_w, bottom_w, height):
    """A symmetric trapezoid wire in XY, centred, narrower at +Y (the OBD-II
    D-shape). Returned as a Workplane profile ready to extrude."""
    htw = top_w / 2.0
    hbw = bottom_w / 2.0
    hh = height / 2.0
    return (
        cq.Workplane("XY")
        .polyline([
            (-hbw, -hh),
            (hbw, -hh),
            (htw, hh),
            (-htw, hh),
        ])
        .close()
    )


def _screw_ears(block_w, block_d, z0, thick, hole_d):
    """Two flat screw ears flanking a block along X, with a through hole each.
    Returned as (ears_solid_with_holes). Ears overlap into the block."""
    ear_r = hole_d / 2.0 + 3.0
    ex = block_w / 2.0 + ear_r - 2.0
    ears = None
    for sx in (-1, 1):
        ear = (
            cq.Workplane("XY")
            .workplane(offset=z0)
            .center(sx * ex, 0)
            .circle(ear_r)
            .extrude(thick)
        )
        ears = ear if ears is None else ears.union(ear)
    # holes
    holes = None
    for sx in (-1, 1):
        h = (
            cq.Workplane("XY")
            .workplane(offset=z0 - 0.5)
            .center(sx * ex, 0)
            .circle(hole_d / 2.0)
            .extrude(thick + 1.0)
        )
        holes = h if holes is None else holes.union(h)
    return ears, holes


# ── Part builders ────────────────────────────────────────────────────────────
def build_dongle_holder():
    """A cradle: a solid block with a dongle-shaped pocket cut down from the top,
    a front strap slot, and two screw ears. The pocket is open to the top (and
    to the front via the strap) → vented."""
    pw = dongle_w + 2.0 * clearance
    pd = dongle_d + 2.0 * clearance
    bw = pw + 2.0 * wall
    bd = pd + 2.0 * wall
    bh = dongle_h * 0.7 + wall  # cradle holds ~70% of the body height

    block = cq.Workplane("XY").box(bw, bd, bh, centered=(True, True, False))
    try:
        block = block.edges("|Z").fillet(min(4.0, wall * 1.2))
    except Exception:
        pass

    # Dongle pocket cut down from the top (open to top → vented).
    pocket = (
        cq.Workplane("XY")
        .workplane(offset=wall)
        .box(pw, pd, bh, centered=(True, True, False))
    )
    body = block.cut(pocket)

    # Strap slot: a shallow channel cut straight across the block for a zip-tie
    # or velcro strap to hold the dongle in. It runs through in X and opens to
    # the top of the pocket, so it always vents to a face (no trapped void).
    strap = (
        cq.Workplane("XY")
        .workplane(offset=bh * 0.35)
        .box(bw + 2.0, 4.0, 8.0, centered=(True, True, False))
    )
    body = body.cut(strap)

    # Screw ears.
    ears, holes = _screw_ears(bw, bd, 0.0, min(bh, wall + 4.0), screw_d)
    body = body.union(ears).cut(holes)
    return body


def build_fuse_organizer():
    """A block with a row of ATO/ATC pockets and a row of Mini pockets, each a
    blind well cut into the top to hold a blade fuse upright. The wells open
    cleanly through the top face (the cutter overshoots the top by a clear
    margin so no paper-thin coincident sliver is left) and leave a solid floor
    of thickness `wall` — vented, no trapped void."""
    ato_bw, ato_th = 19.1, 5.1
    mini_bw, mini_th = 10.9, 3.6
    slot_depth = 12.0
    # Wall between adjacent pockets must survive the per-side clearance, or wide
    # pockets merge into one slot and coincident faces break manifoldness. Keep
    # at least a 1.5 mm rib after clearance is added to both neighbours.
    gap = max(3.0, 2.0 * clearance + 1.5)

    row1_w = ato_count * (ato_th + gap) + gap
    row2_w = mini_count * (mini_th + gap) + gap if mini_count else 0.0
    inner_w = max(row1_w, row2_w, 20.0)
    inner_d = ato_bw + 2.0 * gap
    bw = inner_w + 2.0 * wall
    bd = inner_d + 2.0 * wall + (mini_bw + 2.0 * gap + wall if mini_count else 0.0)
    bh = slot_depth + wall

    block = cq.Workplane("XY").box(bw, bd, bh, centered=(True, True, False))
    # Round only the OUTER vertical edges, and keep the fillet small so it never
    # reaches the pocket mouths near the top rim.
    try:
        block = block.edges("|Z").fillet(min(2.0, wall * 0.4))
    except Exception:
        pass
    body = block

    # Each pocket is cut from the floor top (z = wall) upward, overshooting the
    # block top by 3 mm so it opens the top face on a full, clean rim.
    over = 3.0
    cut_len = slot_depth + over
    # Pockets are cut sequentially: they all open the block top face, and cutting
    # a Compound of many top-opening pockets leaves coincident faces that break
    # the boolean (verified). Sequential cuts stay manifold; the count is small.
    def _pocket(x, y, th):
        return (
            cq.Workplane("XY")
            .workplane(offset=wall)
            .center(x, y)
            .rect(th + 2.0 * clearance, ato_bw + 2.0 * clearance if th == ato_th else mini_bw + 2.0 * clearance)
            .extrude(cut_len)
        )

    # ATO row pockets (front half).
    y_ato = bd / 2.0 - wall - ato_bw / 2.0 - gap
    x0 = -(ato_count - 1) * (ato_th + gap) / 2.0
    for i in range(ato_count):
        body = body.cut(_pocket(x0 + i * (ato_th + gap), y_ato, ato_th))
    # Mini row pockets (rear half).
    if mini_count:
        y_mini = -bd / 2.0 + wall + mini_bw / 2.0 + gap
        mx0 = -(mini_count - 1) * (mini_th + gap) / 2.0
        for i in range(mini_count):
            body = body.cut(_pocket(mx0 + i * (mini_th + gap), y_mini, mini_th))
    return body


def build_obd_bracket():
    """A mounting plate with the SAE J1962 trapezoidal connector opening and two
    screw holes, to panel-mount / relocate the OBD-II port. Solid plate, trapezoid
    through-opening (both faces open), through screw holes."""
    frame_w = obd_w + 2.0 * wall + 6.0
    frame_h = obd_h + 2.0 * wall + 6.0
    th = max(4.0, wall + 1.0)
    plate = cq.Workplane("XY").box(frame_w, frame_h, th, centered=(True, True, False))
    try:
        plate = plate.edges("|Z").fillet(min(4.0, wall))
    except Exception:
        pass
    # Trapezoidal opening through the plate.
    top_w = max(obd_w * 0.82, 6.0)   # short parallel side ≈ 11/13.5 of the wide side
    opening = (
        _trapezoid(top_w, obd_w, obd_h)
        .extrude(th + 2.0)
        .translate((0, 0, -1.0))
    )
    body = plate.cut(opening)
    # Two screw holes flanking the opening.
    hx = frame_w / 2.0 - max(4.0, wall + 1.0)
    holes = (
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .pushPoints([(-hx, 0.0), (hx, 0.0)])
        .circle(screw_d / 2.0)
        .extrude(th + 1.0)
    )
    body = body.cut(holes)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "fuse_organizer":
    result = build_fuse_organizer()
elif target_part == "obd_bracket":
    result = build_obd_bracket()
else:  # "dongle_holder"
    result = build_dongle_holder()
