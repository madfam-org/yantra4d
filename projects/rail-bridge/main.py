"""
Rail Standard Bridge — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A CAPSTONE multi-standard adapter that bridges the three accessory-rail families
that would otherwise never interoperate: the MIL-STD-1913 ("Picatinny") rail, the
NATO accessory rail, and the Arca-Swiss 38 mm tripod dovetail. Each mode is a
single adapter block that carries ONE standard's male profile on its TOP face and
a DIFFERENT standard's male profile on its BOTTOM face — so a clamp/head built for
family A can carry a device built for family B.

Modes (dispatched via `target_part`):
  * "pic_to_nato"  — Picatinny (MIL-STD-1913) rail on TOP, NATO dovetail on BOTTOM.
  * "pic_to_arca"  — Picatinny rail on TOP, Arca-Swiss 38 mm dovetail on BOTTOM.
  * "nato_to_arca" — NATO dovetail on TOP, Arca-Swiss 38 mm dovetail on BOTTOM.

Real cross-section geometry (nominal, dimensionally real, all mm):
  Picatinny (MIL-STD-1913): overall width 21.20, flat top 15.70, height 4.45,
    lower flange band 3.15, recoil-groove pitch 10.0, groove width 5.35.
  NATO accessory rail: top platform 21.2, ~44° flanks, dovetail height 6.0.
  Arca-Swiss: 38.0 mm dovetail platform, ~45° flanks, ~9.0 mm block height.

Watertight strategy (thread-free by design → every render is fast):
  Every profile is a closed 2D wire extruded along the block length and UNIONED
  into a central slab whose faces the profiles overlap into (never a tangent kiss).
  Recoil grooves and bolt/relief holes are cut LAST as through-features that vent
  to a face. Fillets are applied only to the clean base slab, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── MIL-STD-1913 nominal constants (mm) ──────────────────────────────────────
PIC_W_BOTTOM = 21.20   # overall width at the lower locating flange
PIC_TOP_W = 15.70      # flat top width (0.617")
PIC_FLANGE_H = 3.15    # height of the lower flange band the clamp grips
PIC_TOP_H = 4.45       # total rail height above its base plane
PIC_GROOVE_PITCH = 10.00  # recoil-groove on-centre spacing (0.394")
PIC_GROOVE_W = 5.35    # recoil-groove width (0.206")
PIC_GROOVE_DEPTH = 3.30   # recoil-groove depth

# NATO accessory rail nominal (mm)
NATO_TOP_W = 21.20     # platform width
NATO_FLANK = 44.0      # flank angle from vertical (deg)
NATO_H = 6.00          # dovetail block height

# Arca-Swiss nominal (mm)
ARCA_TOP_W = 38.00     # dovetail platform width
ARCA_FLANK = 45.0      # flank angle from vertical (deg)
ARCA_H = 9.00          # dovetail block height


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "pic_to_nato"))
# "pic_to_nato" | "pic_to_arca" | "nato_to_arca"

slots = int(PARAM(lambda: slots, 4))          # Picatinny recoil grooves → length
dovetail_len = float(PARAM(lambda: dovetail_len, 50.0))  # dovetail run length (Y, mm)
core_th = float(PARAM(lambda: core_th, 6.0))  # central slab thickness between the two profiles (mm)
relief_d = float(PARAM(lambda: relief_d, 6.6))  # 1/4-20 relief / pass-through hole (mm)
grip_notch = bool(PARAM(lambda: grip_notch, True))  # NATO safety notch on dovetail faces

# Clamp to sane ranges so extreme UI values still build watertight.
slots = max(2, min(slots, 12))
dovetail_len = max(24.0, min(dovetail_len, 140.0))
core_th = max(3.0, min(core_th, 16.0))
relief_d = max(3.0, min(relief_d, 12.0))


# ── Cross-section wires ──────────────────────────────────────────────────────
def picatinny_profile():
    """MIL-STD-1913 rail cross-section as a closed wire in XY (X=width, Y=height,
    base at Y=0). Symmetric about X=0. Upper section narrows from the 21.2 mm
    flange to the 15.7 mm flat top through the 45° clamping flanks."""
    xb = PIC_W_BOTTOM / 2.0
    xt = PIC_TOP_W / 2.0
    y_flange = PIC_FLANGE_H
    y_neck = y_flange + 1.30
    y_top = PIC_TOP_H
    pts = [
        (-xb, 0.0), (-xb, y_flange), (-xb, y_neck),
        (-xt, y_top), (xt, y_top),
        (xb, y_neck), (xb, y_flange), (xb, 0.0),
    ]
    return cq.Workplane("XY").polyline(pts).close()


def dovetail_profile(top_w, height, flank_ang):
    """A dovetail cross-section in XY (X=width, Y=height, base at Y=0), wider at
    the base (undercut). Used for both NATO and Arca profiles."""
    flank_dx = height * math.tan(math.radians(flank_ang))
    htw = top_w / 2.0
    hbw = htw + flank_dx
    pts = [
        (-hbw, 0.0), (hbw, 0.0),
        (htw, height), (-htw, height),
    ]
    return cq.Workplane("XY").polyline(pts).close()


# ── Profile → oriented solid on a given face of the core slab ────────────────
def _extrude_profile(profile_wp, length):
    """Extrude an XY cross-section along +Z, then orient so width→X, height→+Z,
    length→Y, centred in Y. Returns a solid rooted at z=0 growing upward."""
    return (
        profile_wp
        .extrude(length)
        .rotate((0, 0, 0), (1, 0, 0), 90)     # height(Y)→+Z, length(Z)→−Y
        .translate((0, length / 2.0, 0))       # centre in Y
    )


def profile_solid(kind, length, mount_up):
    """Build a rail/dovetail profile solid sitting on one face of the core slab.

    kind: "pic" | "nato" | "arca". `mount_up=True` sits it on the TOP face of the
    slab growing +Z; `mount_up=False` mirrors it under the BOTTOM face growing −Z.
    Both overlap `0.6` mm into the slab so the union is a clean volumetric fusion.
    Returns (solid, profile_height, footprint_width)."""
    if kind == "pic":
        prof, h, fw = picatinny_profile(), PIC_TOP_H, PIC_W_BOTTOM
    elif kind == "nato":
        prof, h, fw = dovetail_profile(NATO_TOP_W, NATO_H, NATO_FLANK), NATO_H, NATO_TOP_W
    else:  # arca
        prof, h, fw = dovetail_profile(ARCA_TOP_W, ARCA_H, ARCA_FLANK), ARCA_H, ARCA_TOP_W
    solid = _extrude_profile(prof, length)
    if mount_up:
        solid = solid.translate((0, 0, core_th - 0.6))   # bury 0.6 into slab top
    else:
        # Mirror about the slab mid-plane: flip in Z so the profile grows downward.
        solid = solid.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, 0.6))
    return solid, h, fw


def add_recoil_grooves(body, length, top_z, fw):
    """Transverse recoil grooves across a Picatinny top at the 10 mm pitch."""
    n = slots
    span = (n - 1) * PIC_GROOVE_PITCH
    y0 = -span / 2.0
    cutter_w = fw + 4.0
    for i in range(n):
        y = y0 + i * PIC_GROOVE_PITCH
        groove = (
            cq.Workplane("XY")
            .box(cutter_w, PIC_GROOVE_W, PIC_GROOVE_DEPTH + 1.0, centered=(True, True, False))
            .translate((0, y, top_z - PIC_GROOVE_DEPTH))
        )
        body = body.cut(groove)
    return body


def add_safety_notch(body, length, top_z, kind):
    """A shallow transverse safety notch across a NATO/Arca dovetail platform mid-
    length (the NATO recoil stop). Cosmetic-functional; opens to the top face."""
    if not grip_notch or kind == "pic":
        return body
    notch = (
        cq.Workplane("XY")
        .box(NATO_TOP_W + 4.0, 1.6, 1.4, centered=(True, True, False))
        .translate((0, 0, top_z - 1.4))
    )
    return body.cut(notch)


# ── Bridge builder ───────────────────────────────────────────────────────────
def build_bridge(top_kind, bot_kind):
    """A double-sided adapter: a core slab with `top_kind` male profile on top and
    `bot_kind` male profile underneath. A central relief bore passes right through
    both profiles and the slab (vents both ends → no trapped void), letting a
    1/4-20 bolt or wiring pass and keeping the print solid."""
    length = _bridge_length(top_kind, bot_kind)
    # Slab wide enough to host the wider of the two footprints.
    slab_w = max(_footprint(top_kind), _footprint(bot_kind)) + 3.0

    core = cq.Workplane("XY").box(slab_w, length, core_th, centered=(True, True, False))
    try:
        core = core.edges("|Y").fillet(min(1.2, core_th / 3.0))
    except Exception:
        pass

    top_solid, top_h, top_fw = profile_solid(top_kind, length, mount_up=True)
    bot_solid, bot_h, bot_fw = profile_solid(bot_kind, length, mount_up=False)
    body = core.union(top_solid).union(bot_solid)

    top_z = core_th + top_h
    if top_kind == "pic":
        body = add_recoil_grooves(body, length, top_z, top_fw)
    else:
        body = add_safety_notch(body, length, top_z, top_kind)

    # Central through relief bore (Z): from below the bottom profile up through the
    # top profile → open at both ends.
    br = max(1.5, relief_d / 2.0)
    total_h = core_th + top_h + bot_h + 4.0
    bore = (
        cq.Workplane("XY")
        .circle(br)
        .extrude(total_h)
        .translate((0, 0, -(bot_h + 2.0)))
    )
    body = body.cut(bore)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _footprint(kind):
    return {"pic": PIC_W_BOTTOM, "nato": NATO_TOP_W, "arca": ARCA_TOP_W}[kind]


def _bridge_length(top_kind, bot_kind):
    """Length is driven by the Picatinny groove field when present, else the
    dovetail_len slider — but always long enough for the Arca standard grip."""
    if "pic" in (top_kind, bot_kind):
        pic_len = slots * PIC_GROOVE_PITCH + 4.0
        return max(pic_len, 30.0)
    return dovetail_len


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pic_to_arca":
    result = build_bridge("pic", "arca")
elif target_part == "nato_to_arca":
    result = build_bridge("nato", "arca")
else:
    result = build_bridge("pic", "nato")
