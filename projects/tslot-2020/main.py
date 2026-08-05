"""
T-Slot 2020 Accessory Kit — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The "industrial LEGO" accessory ecosystem. Every part in this cartridge shares a
single Common Denominator Geometry: the aluminium T-slot extrusion profile
(2020 / 3030 / 4040 series, e.g. Bosch Rexroth, OpenBuilds, Misumi HFS). The
slot opening, the wider inner channel, and the channel depth are the denominator
that every drop-in / slide-in accessory locks into. Print an accessory, slide or
twist it into the slot, drop in a screw — no proprietary hardware.

Parts (dispatched via `target_part`):
  * "t_nut"          — the highest-value part. A block sized to the inner channel
                       with a neck that rises through the slot opening, topped by
                       a boss carrying an M3/M4/M5 screw clearance hole. Slides in
                       from the end or (thin enough) drops in and quarter-turns.
  * "corner_bracket" — an L / angle bracket that bolts two extrusions at 90°, with
                       slotted holes on each leg (slide adjustment) and a triangular
                       gusset for stiffness.
  * "cable_clip"     — a twist-in clip: a foot that enters the slot rotated then
                       locks a quarter-turn, with an open C-loop that routes a wire
                       or pneumatic line of a given diameter.
  * "panel_clip"     — retains a panel edge (acrylic / ply) of thickness `panel_t`
                       into the slot: a slot foot + a panel groove.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `slot_series`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""



import cadquery as cq


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


# ── T-slot extrusion profile table (the Common Denominator Geometry) ─────────
# Nominal FDM-relevant dimensions for the standard extrusion families. The three
# load-bearing numbers are:
#   opening       — the gap on the face (mm) a neck must pass through.
#   channel_w     — the wider internal channel width (mm) a T-nut body fills.
#   channel_depth — how deep the channel runs below the face lip (mm).
# lip_z is how far the retaining lips sit below the outer face (the material the
# T-nut body hooks under). Values track Bosch Rexroth / OpenBuilds / Misumi HFS
# nominal profiles; printed fit is dialed in with `slot_fit_clearance`.
SLOT_TABLE = {
    "2020": {"profile": 20.0, "opening": 6.0,  "channel_w": 11.0, "channel_depth": 6.0, "lip_z": 1.8},
    "3030": {"profile": 30.0, "opening": 8.0,  "channel_w": 16.5, "channel_depth": 7.5, "lip_z": 2.0},
    "4040": {"profile": 40.0, "opening": 8.0,  "channel_w": 20.0, "channel_depth": 9.0, "lip_z": 2.2},
}


def slot_spec(key):
    """Look up an extrusion series, tolerant of ints/floats/stray spacing."""
    k = str(key).strip().lower().replace(" ", "").replace("*", "x").replace("x", "")
    if k in ("20", "2020", "200"):
        k = "2020"
    elif k in ("30", "3030", "300"):
        k = "3030"
    elif k in ("40", "4040", "400"):
        k = "4040"
    return SLOT_TABLE.get(k, SLOT_TABLE["2020"])


# Screw clearance-hole diameters (mm) for a printable fit.
SCREW_CLEAR = {"M3": 3.4, "M4": 4.5, "M5": 5.5}


def screw_clear_dia(key):
    k = str(key).strip().upper().replace(" ", "")
    if k in ("3", "3.0", "M3"):
        k = "M3"
    elif k in ("4", "4.0", "M4"):
        k = "M4"
    elif k in ("5", "5.0", "M5"):
        k = "M5"
    return SCREW_CLEAR.get(k, SCREW_CLEAR["M4"])


# ── Parameters ───────────────────────────────────────────────────────────────
slot_series  = str(  PARAM(lambda: slot_series,  "2020"))   # "2020" | "3030" | "4040"
target_part  = str(  PARAM(lambda: target_part, "t_nut"))   # which accessory to build

slot_fit_clearance = float(PARAM(lambda: slot_fit_clearance, 0.3))  # per-side printed fit gap
screw_size   = str(  PARAM(lambda: screw_size,     "M4"))   # M3 | M4 | M5

# T-nut
nut_length   = float(PARAM(lambda: nut_length,    12.0))    # length along the slot axis (mm)
tapped       = bool( PARAM(lambda: tapped,        False))   # heat-set/tapped bore instead of clearance

# Corner bracket
bracket_leg  = float(PARAM(lambda: bracket_leg,   30.0))    # leg length of each arm (mm)
bracket_thick = float(PARAM(lambda: bracket_thick, 5.0))    # bracket wall thickness (mm)
bracket_gusset = bool(PARAM(lambda: bracket_gusset, True))  # add stiffening gusset

# Cable clip
cable_dia    = float(PARAM(lambda: cable_dia,      6.0))    # cable / pneumatic line outer dia (mm)

# Panel clip
panel_t      = float(PARAM(lambda: panel_t,        3.0))    # retained panel thickness (mm)


# ── Derived slot geometry ────────────────────────────────────────────────────
S = slot_spec(slot_series)
PROFILE       = S["profile"]
OPENING       = S["opening"]
CHANNEL_W     = S["channel_w"]
CHANNEL_DEPTH = S["channel_depth"]
LIP_Z         = S["lip_z"]

clr = max(0.0, min(slot_fit_clearance, OPENING / 3.0))  # keep clearance sane

# Fitted dimensions (per-side clearance applied):
BODY_W  = max(1.0, CHANNEL_W - 2.0 * clr)            # T-nut body across the channel
NECK_W  = max(1.0, OPENING - 2.0 * clr)              # neck through the slot opening
# The hooking body must be tall enough to sit under the retaining lips but not
# bottom out the channel. Body occupies from the channel floor up to the lip.
BODY_H  = max(1.6, CHANNEL_DEPTH - LIP_Z - clr)      # body height under the lips
NECK_H  = max(0.8, LIP_Z)                            # neck height through the lip zone

SCREW_D = screw_clear_dia(screw_size)
# A tapped/heat-set bore is intentionally smaller than the clearance hole so a
# machine screw self-taps or a brass heat-set insert grips. (No slow helix.)
TAP_D   = {3.4: 2.5, 4.5: 3.3, 5.5: 4.2}.get(SCREW_D, SCREW_D - 1.2)
BORE_D  = TAP_D if tapped else SCREW_D


# ── Helpers ──────────────────────────────────────────────────────────────────
def safe_fillet(wp, selector, r):
    """Fillet a non-empty edge selection, clamped and non-fatal."""
    if r <= 0.05:
        return wp
    try:
        return wp.edges(selector).fillet(r)
    except Exception:
        return wp  # degenerate radius / bad edge set — leave sharp (non-fatal)


def safe_chamfer(wp, selector, c):
    if c <= 0.05:
        return wp
    try:
        return wp.edges(selector).chamfer(c)
    except Exception:
        return wp


def drill_z(body, points, dia, height, z0):
    """Cut vertical through/blind holes at each (x, y). The bore spans `height`
    starting at z0 (extend past faces at the call site for clean, watertight
    through-cuts)."""
    r = dia / 2.0
    if r <= 0.05 or not points:
        return body
    cutter = (
        cq.Workplane("XY")
        .pushPoints(points)
        .circle(r)
        .extrude(height)
        .translate((0, 0, z0))
    )
    return body.cut(cutter)


# ── Builder: T-nut (the highest-value part) ──────────────────────────────────
def build_t_nut():
    """A drop-in / slide-in T-nut.

    Geometry (base at z=0, grows +Z, screw axis = Z):
      z:[0, BODY_H]            body — fills the inner channel width (BODY_W),
                               hooks under the retaining lips.
      z:[BODY_H, BODY_H+NECK_H] neck — passes through the slot opening (NECK_W).
      z:[.., + boss]           boss — sits proud of the face, drilled for a screw.
    The body length along the slot axis is `nut_length`; make it short to drop-in
    and quarter-turn, or long to slide in from the extrusion end for more grip.
    """
    L = max(6.0, nut_length)

    # Body — the part captured inside the channel.
    body = cq.Workplane("XY").box(L, BODY_W, BODY_H, centered=(True, True, False))
    # Lead-in chamfers on the underside long edges ease insertion / rotation.
    body = safe_chamfer(body, "<Z", min(0.8, BODY_H * 0.3))

    # Neck — narrower, rises through the slot opening.
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, BODY_H))
        .box(L, NECK_W, NECK_H, centered=(True, True, False))
    )

    # Boss — a small pad proud of the extrusion face so the screw has thread
    # engagement and the mating part clamps against a flat.
    boss_h = 1.6
    boss_w = min(NECK_W + 2.0 * clr + 2.0, CHANNEL_W)  # roughly slot-opening wide
    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, BODY_H + NECK_H))
        .box(L, boss_w, boss_h, centered=(True, True, False))
    )

    part = body.union(neck).union(boss)

    # Soften the top boss rim (comfort / cleaner top layer). Non-fatal.
    part = safe_fillet(part, ">Z", min(0.6, boss_h * 0.3))

    # Screw bore straight down the Z axis, through the whole stack.
    total_h = BODY_H + NECK_H + boss_h
    part = drill_z(part, [(0.0, 0.0)], BORE_D, total_h + 2.0, -1.0)

    return part


# ── Builder: corner bracket ──────────────────────────────────────────────────
def build_corner_bracket():
    """An inside 90° angle bracket. Two legs meet at the origin corner; each leg
    carries a slotted hole (slide adjustment) sized for the selected screw. An
    optional triangular gusset stiffens the joint. Bolts to two extrusions using
    T-nuts from this same kit."""
    leg = max(PROFILE * 0.75, bracket_leg)
    t   = max(3.0, bracket_thick)
    width = min(PROFILE - 2.0, max(12.0, PROFILE * 0.8))  # bracket width (Y span)

    # Leg A lies flat in the XY plane (bolts to the top face of a horizontal rail).
    leg_a = cq.Workplane("XY").box(leg, width, t, centered=(False, True, False))
    # Leg B rises vertically in the XZ plane (bolts to a vertical rail's face).
    leg_b = (
        cq.Workplane("XY")
        .box(t, width, leg, centered=(False, True, False))
    )
    bracket = leg_a.union(leg_b)

    # Optional gusset: a right triangle in the XZ plane bridging the two legs.
    if bracket_gusset:
        gspan = min(leg, leg) * 0.7
        gy = max(3.0, width * 0.35)
        pts = [(t, t), (gspan, t), (t, gspan)]
        gusset = (
            cq.Workplane("XZ")
            .polyline(pts).close()
            .extrude(gy)
            .translate((0, gy / 2.0, 0))
        )
        bracket = bracket.union(gusset)

    # Slotted holes: one along each leg for slide adjustment. A slot is a pill —
    # two bored circles joined by a rectangular cut.
    slot_len = leg * 0.4
    r = SCREW_D / 2.0
    a_center = t + (leg - t) / 2.0  # midway along leg A's free length

    # Leg A slot (bore in Z through the flat leg).
    a_pts = [(a_center - slot_len / 2.0, 0.0), (a_center + slot_len / 2.0, 0.0)]
    bracket = drill_z(bracket, a_pts, SCREW_D, t + 2.0, -1.0)
    slot_cut_a = (
        cq.Workplane("XY")
        .box(slot_len, SCREW_D, t + 2.0, centered=(True, True, False))
        .translate((a_center, 0.0, -1.0))
    )
    bracket = bracket.cut(slot_cut_a)

    # Leg B slot (bore in Y through the vertical leg — cut along X thickness).
    b_center = t + (leg - t) / 2.0
    cyl_h = t + 2.0
    for zc in (b_center - slot_len / 2.0, b_center + slot_len / 2.0):
        cyl = (
            cq.Workplane("XZ")
            .circle(r)
            .extrude(cyl_h)
            .translate((0, cyl_h - 1.0, 0))  # start behind the leg's front face
            .translate((t / 2.0, 0, zc))
        )
        bracket = bracket.cut(cyl)
    slot_cut_b = (
        cq.Workplane("XY")
        .box(t + 2.0, SCREW_D, slot_len, centered=(True, True, False))
        .translate((t / 2.0, 0.0, b_center))
    )
    bracket = bracket.cut(slot_cut_b)

    # Break the sharp outer corner.
    bracket = safe_fillet(bracket, "|Y", min(2.0, t * 0.4))
    return bracket


# ── Builder: cable clip (twist-in) ───────────────────────────────────────────
def build_cable_clip():
    """A twist-in cable clip: a rectangular foot enters the slot and, rotated a
    quarter turn, its long axis spans the inner channel so it cannot pull out. A
    solid post rises above the face, bored through with a cable channel; a mouth
    slot cut from the top opens the bore into a C so a wire / pneumatic line of
    `cable_dia` snaps in from above."""
    d = max(2.0, cable_dia)

    # Foot: spans the inner channel (captured), passes through the opening on its
    # short axis. Same body/neck logic as the T-nut but no screw.
    foot = cq.Workplane("XY").box(BODY_W, max(NECK_W, OPENING - 2.0 * clr), BODY_H, centered=(True, True, False))
    foot = safe_chamfer(foot, "<Z", min(0.8, BODY_H * 0.3))
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, BODY_H))
        .box(max(NECK_W, OPENING - 2.0 * clr), max(NECK_W, OPENING - 2.0 * clr), NECK_H, centered=(True, True, False))
    )
    clip = foot.union(neck)

    # Solid post above the face. The cable bore runs through it along Y; the post
    # is sized to leave a `wall` of material all around the bore.
    base_z = BODY_H + NECK_H
    wall = max(1.6, d * 0.4)                 # material around the cable bore
    post_w = d + 2.0 * wall                  # X footprint of the post
    post_d = d + 2.0 * wall                  # Y depth of the post (bore axis)
    bore_z = base_z + wall + d / 2.0         # centre height of the cable bore
    post_h = bore_z + d / 2.0 + wall         # top of the post above z=0

    post = (
        cq.Workplane("XY")
        .box(post_w, post_d, post_h - base_z, centered=(True, True, False))
        .translate((0, 0, base_z))
    )
    post = safe_fillet(post, "|Z", min(2.0, wall * 0.8))
    clip = clip.union(post)

    # Cable bore: a horizontal cylinder through the post along Y (extends past
    # both faces for a clean, watertight through-cut).
    bore = (
        cq.Workplane("XZ")
        .circle(d / 2.0)
        .extrude(post_d + 2.0)
        .translate((0, (post_d + 2.0) / 2.0, 0))   # centre on Y=0
        .translate((0, 0, bore_z))
    )
    clip = clip.cut(bore)

    # Mouth: a vertical slot (slightly narrower than the cable so it snaps and
    # retains) cut from the top of the post straight down into the bore. It spans
    # the full post depth in Y and overshoots the top in Z — never tangent.
    mouth_w = d * 0.75
    mouth = (
        cq.Workplane("XY")
        .box(mouth_w, post_d + 2.0, post_h, centered=(True, True, False))
        .translate((0, 0, bore_z))   # from bore centre up past the top
    )
    clip = clip.cut(mouth)
    return clip


# ── Builder: panel clip ──────────────────────────────────────────────────────
def build_panel_clip():
    """Retains a panel edge (acrylic / ply) into the extrusion. A slot foot roots
    the clip in the channel; above the face a slotted jaw grips a panel of
    thickness `panel_t`, holding its edge against the extrusion face."""
    pt = max(1.0, panel_t)

    # Slot foot (captured) + neck through opening.
    foot = cq.Workplane("XY").box(BODY_W, max(NECK_W, OPENING - 2.0 * clr), BODY_H, centered=(True, True, False))
    foot = safe_chamfer(foot, "<Z", min(0.8, BODY_H * 0.3))
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, BODY_H))
        .box(NECK_W, max(NECK_W, OPENING - 2.0 * clr), NECK_H, centered=(True, True, False))
    )
    clip = foot.union(neck)

    # Above the face: a block with a groove that captures the panel edge. The
    # groove opens away from the extrusion so the panel lies flat on the face.
    base_z = BODY_H + NECK_H
    jaw_len = pt + 2.0 * 2.0        # groove wall (2mm) each side of the panel
    jaw_h = max(6.0, pt * 3.0)
    jaw_w = max(10.0, PROFILE * 0.6)

    jaw = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(jaw_len / 2.0 - 1.0, 0, base_z))
        .box(jaw_len, jaw_w, jaw_h, centered=(True, True, False))
    )
    clip = clip.union(jaw)

    # Panel groove: a slot cut into the jaw's outer face (a channel the panel
    # edge slides into). Open at the top for insertion.
    groove_z0 = base_z + max(2.0, jaw_h * 0.3)  # leave a floor under the panel
    groove = (
        cq.Workplane("XY")
        .box(pt + 0.4, jaw_w + 2.0, jaw_h, centered=(True, True, False))
        .translate((jaw_len / 2.0 - 1.0, 0, groove_z0 + jaw_h / 2.0))
    )
    clip = clip.cut(groove)

    clip = safe_fillet(clip, ">Z", min(0.6, 1.0))
    return clip


# ── Dispatch ─────────────────────────────────────────────────────────────────
_BUILDERS = {
    "t_nut": build_t_nut,
    "corner_bracket": build_corner_bracket,
    "cable_clip": build_cable_clip,
    "panel_clip": build_panel_clip,
}

_part = target_part if target_part in _BUILDERS else "t_nut"
result = _BUILDERS[_part]()
