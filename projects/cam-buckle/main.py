"""Cam Buckle — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The lever-cam strap lock used on tie-downs, luggage compression straps, roof-rack straps
and camera slings: the tape runs under a toothed cam lever and over a fixed anvil bar; pull
the tape and the cam rides up and lets it through, let go and the load rotates the cam down
onto the tape and locks it. Squeeze the lever to release. Two parts on one pin. This is the
rigid hard good the Fashion Cabinet `cam-buckle` notion places and bridges to here.

Nominal webbing 20 / 25 / 38 / 50 mm; the pin bore is sized for a printed or metal pin.

Modes (dispatched via `target_part`):
  * "set"  — body and cam lever laid out side by side on one plate.
  * "body" — the frame: two side cheeks, the anvil bar, the webbing tail slot, pin bores.
  * "cam"  — the lever: hub with a through bore, an offset toothed cam face, a thumb tail.

Geometry: the body is a rounded slab hollowed by one open-ended pocket (never a sealed
void), with the anvil bar unioned back across it with real overlap and the pin bores cut
clean through both cheeks. The cam is a hub cylinder unioned to a lofted eccentric lobe and
a flat thumb pad; its grip teeth are flat-topped lofted ribs, never knife edges. No fillets
run after a complex cut; every cutter overshoots both faces.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `webbing_w`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
webbing_w  = float(PARAM(lambda: webbing_w,  25.0))  # nominal webbing width (mm)
webbing_t  = float(PARAM(lambda: webbing_t,  1.6))   # webbing thickness (mm)
cheek_t    = float(PARAM(lambda: cheek_t,    3.0))   # side cheek wall thickness (mm)
pin_dia    = float(PARAM(lambda: pin_dia,    3.0))   # cam pivot pin diameter (mm)
cam_throw  = float(PARAM(lambda: cam_throw,  3.0))   # cam lobe eccentricity (mm)
pin_clear  = float(PARAM(lambda: pin_clear,  0.35))  # bore clearance on the pin (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|body|cam

# ── Safe clamps ──────────────────────────────────────────────────────────────
webbing_w  = max(15.0, min(webbing_w, 50.0))
webbing_t  = max(0.8, min(webbing_t, 4.0))
cheek_t    = max(2.0, min(cheek_t, 6.0))
pin_dia    = max(2.0, min(pin_dia, 6.0))
cam_throw  = max(1.2, min(cam_throw, 6.0))
pin_clear  = max(0.15, min(pin_clear, 0.8))

# ── Derived geometry ─────────────────────────────────────────────────────────
inner_w  = webbing_w + 1.5                        # clear span between the cheeks (Y)
outer_w  = inner_w + 2.0 * cheek_t                # overall width (Y)
throat_h = max(webbing_t * 2.0 + 2.0, 5.0)        # clear height of the tape throat (Z)
body_h   = throat_h + 2.0 * cheek_t               # overall body height (Z)
anvil_d  = max(3.0, min(cheek_t * 1.5, throat_h * 0.55))   # anvil bar diameter
slot_t   = max(webbing_t + 0.4, 1.2)              # tail slot opening (Z)

# Cam hub radius: enough meat round the bore, plus the throw.
hub_r    = pin_dia / 2.0 + max(1.6, pin_dia * 0.55)
lobe_r   = hub_r + cam_throw                      # cam lobe outer radius at the bite
cam_w    = inner_w - 1.2                          # cam width across the throat (Y)
tail_len = max(hub_r * 2.4, 12.0)                 # thumb-lever length (X)

# Body length: pivot zone + throat + webbing tail block.
pivot_x  = 0.0                                    # cam pivot sits at the origin
anvil_x  = lobe_r + max(2.5, webbing_t * 1.5)     # anvil sits ahead of the cam bite
tailb_l  = max(8.0, anvil_d * 2.4)                # webbing tail block length (X)
body_x0  = -(hub_r + cheek_t + 2.0)               # rear face of the body
body_x1  = anvil_x + anvil_d / 2.0 + tailb_l      # front face of the body
body_len = body_x1 - body_x0
corner_r = min(2.5, cheek_t * 0.8)


def _rounded_slab(length, width, thick, rad):
    """Rounded-rectangle slab, X = length, Y = width, resting on Z = 0."""
    r = max(0.3, min(rad, min(length, width) / 2.0 - 0.3))
    return (
        cq.Workplane("XY")
        .rect(length, width)
        .extrude(thick)
        .edges("|Z")
        .fillet(r)
    )


def build_body():
    """Cheeks + anvil bar + tail slot + pin bores, all from one hollowed slab."""
    body = _rounded_slab(body_len, outer_w, body_h, corner_r).translate(
        ((body_x0 + body_x1) / 2.0, 0.0, 0.0))

    # Throat: an open-ended pocket running out through BOTH X ends, so nothing is
    # ever a sealed internal void. Overshoots in X by 10 mm at each end.
    throat = (
        cq.Workplane("XY")
        .box(body_len + 20.0, inner_w, throat_h)
        .translate(((body_x0 + body_x1) / 2.0, 0.0, body_h / 2.0))
    )
    body = body.cut(throat)

    # Anvil bar: a cylinder spanning Y across the throat, overlapping both cheeks by
    # 1 mm each side so the union is genuinely solid.
    anvil_len = outer_w + 2.0
    # The bar's centre sits BELOW the throat floor so its lower half is buried in the
    # body — a real overlap, never a tangent touch on the floor plane.
    anvil = (
        cq.Workplane("XZ")
        .circle(anvil_d / 2.0)
        .extrude(anvil_len)
        .translate((anvil_x, anvil_len / 2.0,
                    body_h / 2.0 - throat_h / 2.0 + anvil_d * 0.35))
    )
    body = body.union(anvil)

    # Webbing tail block: a floor slab across the front of the throat with a tape slot
    # through it, so the dead end can be sewn round a bar rather than knotted. It is
    # OVERSIZED in Y and Z and then trimmed by the body's own outline, so it never
    # leaves a sliver against the cheek walls.
    blk_cx = body_x1 - tailb_l / 2.0
    blk = (
        cq.Workplane("XY")
        .box(tailb_l - 1.0, outer_w + 4.0, throat_h + 2.0)
        .translate((blk_cx, 0.0, body_h / 2.0))
        .intersect(_rounded_slab(body_len, outer_w, body_h, corner_r).translate(
            ((body_x0 + body_x1) / 2.0, 0.0, 0.0)))
    )
    body = body.union(blk)
    slot = (
        cq.Workplane("XY")
        .box(max(2.5, webbing_t * 2.0 + 1.0), webbing_w + 20.0, slot_t)
        .translate((blk_cx, 0.0, body_h / 2.0))
    )
    body = body.cut(slot)

    # Pin bores through both cheeks, overshooting in Y.
    bore = (
        cq.Workplane("XZ")
        .circle(pin_dia / 2.0 + pin_clear / 2.0)
        .extrude(outer_w + 20.0)
        .translate((pivot_x, (outer_w + 20.0) / 2.0 - (outer_w / 2.0 + 10.0),
                    body_h / 2.0 + throat_h / 2.0 - hub_r * 0.35))
    )
    return body.cut(bore)


def _cam_teeth(base_solid):
    """Flat-topped grip ribs along the cam lobe's biting arc.

    Each rib is a small cylinder whose CENTRE sits inside the lobe surface, so it is
    always deeply overlapped rather than tangent, and stands proud by `rib_h`. A round
    section has no knife edge at all — the bite comes from the rib pitch, not sharpness.
    """
    n = 5
    rib_r = max(0.5, min(1.0, cam_throw * 0.28))
    rib_h = max(0.3, min(0.6, cam_throw * 0.16))
    solid = base_solid
    # The lobe's centre and radius (see build_cam): ribs are placed on ITS surface.
    lx, lz = cam_throw * 0.75, -cam_throw * 0.35
    lr = hub_r * 0.92
    for i in range(n):
        a = math.radians(-70.0 + 140.0 * i / max(1, n - 1))
        # Sink the rib centre so only rib_h of it clears the lobe surface.
        r_at = lr + rib_h - rib_r
        cx = lx + r_at * math.cos(a)
        cz = lz + r_at * math.sin(a)
        rib = (
            cq.Workplane("XZ")
            .circle(rib_r)
            .extrude(cam_w)
            .translate((cx, cam_w / 2.0, cz))
        )
        solid = solid.union(rib)
    return solid


def build_cam():
    """Hub cylinder + eccentric lofted lobe + thumb tail, with a through bore."""
    # The cam is modelled with its pivot at the origin, axis along Y, then laid flat.
    hub = (
        cq.Workplane("XZ")
        .circle(hub_r)
        .extrude(cam_w)
        .translate((0.0, cam_w / 2.0, 0.0))
    )
    # Eccentric lobe: a second cylinder offset by the throw, overlapping the hub.
    lobe = (
        cq.Workplane("XZ")
        .circle(hub_r * 0.92)
        .extrude(cam_w)
        .translate((cam_throw * 0.75, cam_w / 2.0, -cam_throw * 0.35))
    )
    body = hub.union(lobe)

    # Thumb tail: a tapered flat lever running back from the hub, overlapping it.
    lever = (
        cq.Workplane("XZ")
        .moveTo(-hub_r * 0.6, hub_r * 0.2)
        .lineTo(-tail_len, hub_r * 0.55)
        .lineTo(-tail_len, hub_r * 0.55 + max(1.8, hub_r * 0.35))
        .lineTo(-hub_r * 0.6, hub_r * 0.9)
        .close()
        .extrude(cam_w)
        .translate((0.0, cam_w / 2.0, 0.0))
    )
    body = body.union(lever)
    body = _cam_teeth(body)

    # Pivot bore through the hub, overshooting both Y faces.
    bore = (
        cq.Workplane("XZ")
        .circle(pin_dia / 2.0 + pin_clear)
        .extrude(cam_w + 20.0)
        .translate((0.0, (cam_w + 20.0) / 2.0 - (cam_w / 2.0 + 10.0), 0.0))
    )
    return body.cut(bore)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "body":
    result = build_body()
elif target_part == "cam":
    result = build_cam()
else:
    gap = max(6.0, outer_w * 0.22)
    frame = build_body().translate((0.0, outer_w / 2.0 + gap / 2.0, 0.0))
    # Lay the cam beside the frame, hub axis vertical is wrong for printing — it prints
    # best on a flat cheek, which is how it is already oriented (axis along Y).
    lever = build_cam().translate(
        (tail_len * 0.3, -(outer_w / 2.0 + gap / 2.0), lobe_r + 1.0))
    result = cq.Workplane("XY").add(frame).add(lever)
