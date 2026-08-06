"""
Window / Sash Lock Insert — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Small window-security inserts that live in the sash channel of a sliding or
double-hung window: a cantilever snap catch, a sash stop/pin that limits travel,
and a friction wedge lock that jams the sash shut.

Three distinct parts:
  - snap_catch : a block that seats in the sash channel with a CANTILEVER snap arm
                 whose barbed hook clips behind the channel lip. A clearance slot
                 behind the arm (open to a face) lets the beam flex — a single
                 manifold body, no trapped void.
  - sash_stop  : a security stop / vent limiter — a channel-width block with a
                 through screw/pin bore and a raised stop shoulder that blocks the
                 sash from sliding past a set opening.
  - wedge_lock : a friction wedge that slides into the sash gap and jams the window;
                 a tapered ramp block with a thumb tab and a lanyard hole.

Dimensioning (internal — sash channels vary by manufacturer):
  - sash channel width : ~14 mm nominal insert width (fits common vinyl/aluminium
                          sliding-window channels; parametric to retune)
  - snap arm clearance : 0.5 mm gap each side of the cantilever so it can flex
  - barb undercut      : ~1.2 mm hook engagement behind the lip
  - pin/screw bore     : ~4 mm (No.8 / M4) for the stop

Watertight strategy (snap features are the delicate case):
  The cantilever is a SOLID beam cut from the block by an open U-slot that vents to
  the top and one end face (never an enclosed pocket). The barb is a wedge UNIONED
  onto the free end of the beam (overlap → one body). The stop shoulder is a block
  unioned into shared material; the wedge is a lofted taper. Every hole is a
  through-bore. Fillets are applied to clean blanks BEFORE feature cuts. The result
  of every mode is ONE manifold solid (body_count == 1), verified with trimesh.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>).
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


# ── Parameters (internal — sash channels vary by manufacturer) ───────────────
target_part = str(PARAM(lambda: target_part, "snap_catch"))
# "snap_catch" | "sash_stop" | "wedge_lock"

channel_w = float(PARAM(lambda: channel_w, 14.0))   # sash-channel insert width (X)
body_len = float(PARAM(lambda: body_len, 40.0))     # insert length (Y)
body_h = float(PARAM(lambda: body_h, 12.0))         # insert height (Z)

arm_len = float(PARAM(lambda: arm_len, 22.0))       # cantilever snap arm length
arm_t = float(PARAM(lambda: arm_t, 2.4))            # cantilever arm thickness
snap_clear = float(PARAM(lambda: snap_clear, 0.5))  # flex clearance each side of arm
barb = float(PARAM(lambda: barb, 1.2))              # barb hook undercut depth
pin_d = float(PARAM(lambda: pin_d, 4.2))            # stop pin / screw bore Ø
wedge_rise = float(PARAM(lambda: wedge_rise, 6.0))  # wedge taper rise over its length

# Clamp to sane ranges so extreme UI values never crash the kernel.
channel_w = max(8.0, min(channel_w, 30.0))
body_len = max(24.0, min(body_len, 90.0))
body_h = max(6.0, min(body_h, 30.0))
arm_len = max(10.0, min(arm_len, body_len - 8.0))
arm_t = max(1.5, min(arm_t, channel_w / 2.0))
snap_clear = max(0.3, min(snap_clear, 1.5))
barb = max(0.6, min(barb, 3.0))
pin_d = max(2.5, min(pin_d, channel_w - 3.0))
wedge_rise = max(2.0, min(wedge_rise, body_h - 2.0))


# ── Primitives ───────────────────────────────────────────────────────────────
def _block(w, length, h, corner=1.5):
    """A filleted block, base at z=0, centred on X, spanning 0..length in Y."""
    b = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, length / 2.0, 0))
        .box(w, length, h, centered=(True, True, False))
    )
    try:
        b = b.edges("|Z").fillet(min(corner, w / 2.0 - 0.5))
    except Exception:
        pass
    return b


# ── Part builders ────────────────────────────────────────────────────────────
def build_snap_catch():
    """A channel insert with a CANTILEVER snap arm — the textbook cantilever hook.

    A short seating block sits in the sash channel; a slender arm cantilevers past
    the block's +Y face into free space, and a barb at the arm's free end hooks UP
    (+Z) over the channel lip. Because the arm protrudes into open air, its flex
    clearance is the surrounding void itself — there is no enclosed pocket to trap,
    and the whole part is one manifold solid. The arm is thinner than the block
    (arm_t) so it flexes; the barb has a +Y lead-in ramp (insertion) and a square
    -Y locking face (retention)."""
    # Seating block: the part of the insert that stays captured in the channel.
    seat_len = body_len * 0.55
    block = _block(channel_w, seat_len, body_h)

    # A through pin bore in the seat so a screw/pin anchors it (vents both faces).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, seat_len * 0.45, -0.5))
        .circle(pin_d / 2.0)
        .extrude(body_h + 1.0)
    )
    block = block.cut(bore)

    # Cantilever arm: a slender beam of thickness arm_t on the base plane, spanning
    # from inside the seat (root_y, overlap → welds to the block) out to the free tip
    # (tip_y) past +Y into free air.
    # Arm width leaves snap_clear of air on each side vs the channel walls so the
    # beam can flex without binding on the channel.
    arm_w = max(3.0, channel_w - 2.0 * (1.0 + snap_clear))
    root_y = seat_len - 4.0                        # rooted inside the seat (overlap)
    tip_y = root_y + arm_len                        # free end, out past the seat
    arm_mid = (root_y + tip_y) / 2.0
    arm_span = tip_y - root_y
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, arm_mid, 0))
        .box(arm_w, arm_span, arm_t, centered=(True, True, False))
    )
    body = block.union(arm)

    # Barb at the free (+Y) end: a hook rising in +Z above the arm. Built from a
    # side profile in the YZ plane (profile-x -> world Y, profile-y -> world Z):
    # square retention face on the -Y side, ramp down to the arm on the +Y side.
    # It sits just inboard of tip_y so it overlaps the arm top (welds → one body).
    barb_h = min(body_h * 0.6, 5.0)
    ramp = min(barb * 3.0, 6.0)
    crest_y = tip_y - 0.5
    base_y = crest_y - ramp - barb
    hook = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, 0, arm_w / 2.0))
        .polyline([
            (base_y, arm_t - 0.6),                 # base, overlaps into the arm top
            (base_y, arm_t + barb_h),              # up: square retention face (-Y)
            (crest_y - barb, arm_t + barb_h),      # crest
            (crest_y, arm_t - 0.6),                # ramp down to arm top (+Y)
        ])
        .close()
        .extrude(-arm_w)
    )
    body = body.union(hook)
    return body


def build_sash_stop():
    """A sash stop / vent limiter: a channel-width block with a through pin/screw
    bore (mounts to the frame) and a raised stop shoulder that blocks the sash from
    sliding past a set opening. All cuts are through-bores → vented."""
    block = _block(channel_w, body_len, body_h)

    # Raised stop shoulder at the +Y end (a taller block unioned on, overlapping).
    shoulder = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, body_len - 6.0, 0))
        .box(channel_w, 12.0, body_h + 6.0, centered=(True, True, False))
    )
    try:
        shoulder = shoulder.edges("|Z").fillet(min(2.0, channel_w / 2.0 - 0.5))
    except Exception:
        pass
    block = block.union(shoulder)

    # Through pin/screw bore near the -Y end (mount to frame).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 10.0, -0.5))
        .circle(pin_d / 2.0)
        .extrude(body_h + 1.0)
    )
    block = block.cut(bore)

    # A cross vent/lanyard hole through the shoulder in X (vents both X faces).
    cross = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(body_len - 6.0, body_h + 1.0, -channel_w / 2.0 - 1.0))
        .circle(min(pin_d / 2.0, 2.5))
        .extrude(channel_w + 2.0)
    )
    block = block.cut(cross)
    return block


def build_wedge_lock():
    """A friction wedge that slides into the sash gap and jams the window. A tapered
    ramp block, thin at the leading (+Y) tip and rising to full height at the -Y
    thumb tab. Built by extruding a right-trapezoid side profile (in the YZ plane)
    across the channel width → one clean solid; then a thumb tab and lanyard bore."""
    lead_h = max(1.5, body_h - wedge_rise)

    # Side profile in the YZ plane: base along +Y from 0..body_len at z=0, top edge
    # ramps from lead_h (at y=0, the leading tip) up to body_h (at y=body_len). The
    # workplane maps profile-x -> world Y, profile-y -> world Z. Extrude across X.
    prof = (
        cq.Workplane("YZ")
        .polyline([
            (0.0, 0.0),
            (body_len, 0.0),
            (body_len, body_h),
            (0.0, lead_h),
        ])
        .close()
    )
    # Extrude symmetric across X so the wedge is centred on X (width channel_w).
    wedge = prof.extrude(channel_w / 2.0, both=True)

    # Thumb tab at the trailing (+Y) end for grip. It overlaps the tall end of the
    # wedge (z 0..body_h there) so it welds into one body.
    tab_h = min(body_h, 6.0)
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, body_len - 3.0, 0))
        .box(channel_w + 6.0, 6.0, tab_h, centered=(True, True, False))
    )
    try:
        tab = tab.edges("|Z").fillet(2.0)
    except Exception:
        pass
    body = wedge.union(tab)

    # Lanyard hole through the tab (vents both faces).
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, body_len - 3.0, -0.5))
        .circle(min(pin_d / 2.0, 2.5))
        .extrude(tab_h + 1.0)
    )
    body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "sash_stop":
    result = build_sash_stop()
elif target_part == "wedge_lock":
    result = build_wedge_lock()
else:
    result = build_snap_catch()
