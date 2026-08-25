import cadquery as cq
import math


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "cuff")
palm_dia = float(PARAM(lambda: palm_dia, 42.0))
handle_dia = float(PARAM(lambda: handle_dia, 12.0))
band_wall = float(PARAM(lambda: band_wall, 4.0))
band_w = float(PARAM(lambda: band_w, 28.0))
clearance = float(PARAM(lambda: clearance, 0.5))
strap_w = float(PARAM(lambda: strap_w, 25.0))

# ─── Real-world reference dimensions (cited as an internal socket standard) ────
# Adaptive "universal cuff" occupational-therapy aid: a band around the palm
#   (~40 mm across the hand) with a socket that grips a utensil handle. Common
#   cutlery/pen/toothbrush handles are ~8–16 mm; a strap slot takes ~25 mm webbing.
CUFF_OPENING_FRAC = 0.55   # palm-band mouth as a fraction of palm diameter
SLOT_T = 3.0               # strap slot thickness


def _fillet_safe(wp, sel, r):
    try:
        return wp.edges(sel).fillet(r)
    except Exception:
        return wp


def _palm_band(bore_d, wall, width):
    """An open C-band for the hand: a ring with a mouth cut on +X so it slips over
    the palm. Bore axis along Z; mouth opens to a face → no trapped void."""
    r_in = bore_d / 2.0
    r_out = r_in + wall
    ring = cq.Workplane("XY").circle(r_out).circle(r_in).extrude(width)
    mouth = CUFF_OPENING_FRAC * bore_d
    gap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(r_out, 0, -1.0))
        .box(r_out * 2.0, mouth, width + 2.0, centered=(True, True, False))
    )
    return ring.cut(gap)


def _utensil_socket_block(bore_d, width):
    """A solid pad carrying a utensil socket (a blind bore, open at the top so the
    utensil pushes in). Returned centred on -X (palm side is +X)."""
    bore_r = (bore_d + 2.0 * clearance) / 2.0
    pad_w = bore_d + 2.0 * band_wall + 4.0
    pad_h = width
    pad_len = bore_d + 2.0 * band_wall + 6.0

    pad = cq.Workplane("XY").box(pad_len, pad_w, pad_h, centered=(True, True, False))
    pad = _fillet_safe(pad, "|Z", 2.0)
    # Vertical socket bore, open to the TOP face only (blind at ~85% depth).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, pad_h * 0.15))
        .cylinder(pad_h, bore_r, centered=(True, True, False))
    )
    pad = pad.cut(bore)
    return pad, pad_len


# ─── Mode 1: universal cuff (palm band + utensil socket) ──────────────────────
def build_cuff():
    """A palm C-band joined to a utensil socket so a user with limited grip can
    hold a fork, pen or toothbrush. Deep overlap between band and socket pad keeps
    it one watertight body."""
    band = _palm_band(palm_dia + 2.0 * clearance, band_wall, band_w)
    palm_r_out = (palm_dia + 2.0 * clearance) / 2.0 + band_wall

    pad, pad_len = _utensil_socket_block(handle_dia, band_w)
    pad_x = -(palm_r_out + pad_len / 2.0 - band_wall)   # overlap the band
    pad = pad.translate((pad_x, 0, 0))

    body = band.union(pad)
    body = _fillet_safe(body, "|Z", 1.0)
    return body


# ─── Mode 2: strap cuff (palm band with webbing slots) ────────────────────────
def build_strap_cuff():
    """A cuff whose palm band takes a hook-and-loop STRAP through two slots (so it
    cinches to any hand) plus the utensil socket. Slots pass fully through the band
    wall → open, not sealed."""
    band = _palm_band(palm_dia + 2.0 * clearance, band_wall + 2.0, band_w)
    palm_r_out = (palm_dia + 2.0 * clearance) / 2.0 + band_wall + 2.0

    pad, pad_len = _utensil_socket_block(handle_dia, band_w)
    pad_x = -(palm_r_out + pad_len / 2.0 - band_wall)
    pad = pad.translate((pad_x, 0, 0))
    body = band.union(pad)

    # Two strap slots through the band wall on +/-Y (webbing threads around palm).
    sw = min(strap_w, band_w - 4.0)
    for sign in (1.0, -1.0):
        a = math.radians(90.0 * sign)
        cx = math.cos(a) * palm_r_out
        cy = math.sin(a) * palm_r_out
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, band_w / 2.0))
            .box(band_wall * 6.0, SLOT_T, sw, centered=(True, True, True))
        )
        body = body.cut(slot)

    # NOTE: no trailing fillet here — filleting this feature-laden solid (mouth gap
    # + socket bore + two strap slots) produces degenerate faces at extreme params
    # (non-watertight). The band and pad are already filleted where safe.
    return body


# ─── Mode 3: built-up wide grip (handle enlarger) ─────────────────────────────
def build_wide_grip():
    """A fat cylindrical grip that slides ONTO a thin utensil handle to enlarge it
    for a weak grip. A tube: solid outer cylinder with a through bore for the
    handle (open both ends) → watertight, with shallow finger flutes for purchase."""
    bore_r = (handle_dia + 2.0 * clearance) / 2.0
    outer_r = bore_r + max(6.0, band_wall + 4.0)
    length = max(90.0, band_w * 3.0)

    grip = cq.Workplane("XY").circle(outer_r).extrude(length)
    grip = _fillet_safe(grip, "|Z", 2.0)
    bore = (
        cq.Workplane("XY")
        .cylinder(length + 2.0, bore_r, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    grip = grip.cut(bore)

    # Shallow vertical finger flutes (one polar-array boolean, cheap + watertight).
    try:
        flutes = (
            cq.Workplane("XY")
            .polarArray(radius=outer_r, startAngle=0, angle=360, count=12)
            .rect(1.2, 3.6)
            .extrude(length + 2.0)
            .translate((0, 0, -1.0))
        )
        grip = grip.cut(flutes)
    except Exception:
        pass
    return grip


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cuff":
    result = build_cuff()
elif target_part == "strap_cuff":
    result = build_strap_cuff()
elif target_part == "wide_grip":
    result = build_wide_grip()
else:
    result = build_cuff()
