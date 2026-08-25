"""
Sign Post Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Brackets that mount a sign blank to a street-furniture post. Two real interfaces meet
here and neither is negotiable if the part is to fit anything: the POST SECTION on one
side (U-channel or square tube, in the sections actually rolled for signage) and the
SIGN BLANK HOLE SPACING on the other (the punched hole pattern sign blanks arrive with).

Modes are dispatched via `target_part`:
  * "u_channel"  — a bracket for a U-channel (hat-section) post, the ubiquitous US
                   green sign post; keys into the post's punched hole line.
  * "square_tube" — a bracket for square tube post (the perforated telespar family
                   and EU square sections), clamping the tube on two faces.
  * "blade_arm"  — a perpendicular blade/finger arm that stands a sign off the post
                   at 90 degrees, for a street-name blade or a fingerpost.

Standards encoded (mm):
  U-channel signage post sections (nominal web width across the flat):
    2 lb/ft  ~ 44.5 (1.75 in),  3 lb/ft ~ 50.8 (2.00 in),  4 lb/ft ~ 57.2 (2.25 in)
  Square tube posts: 1.75 in = 44.45, 2.00 in = 50.80, 2.25 in = 57.15, plus a
  metric 60.0 section. Perforated square tube is punched on a 1 in (25.4 mm) pitch.
  Sign-blank hole spacing: blanks are punched with 3/8 in (9.53 mm) holes; the
  common vertical spacings are 100 mm, 150 mm and 12 in (304.8 mm) between centres.
  Post bolt pitch: 25.4 mm (1 in), matching perforated tube and U-channel punching.

Watertightness strategy (a bracket as a closed manifold):
  Every part is a SOLID blank from which the post pocket and the bolt holes are cut.
  The post pocket is ALWAYS opened to at least one face — it is a channel or a
  three-sided clamp, never a sealed internal void. Every bolt hole runs fully through
  and breaks out on both faces, so no hole is a blind pocket (a blind pocket keeps
  Euler characteristic at 2 and silently passes a watertight check while being wrong).
  Stacked bodies OVERLAP volumetrically; a tangent kiss leaves a zero-area seam.
  Hole positions and counts are clamped against the plate they sit in, so a large
  bolt at a tight spacing can never break out through an edge and shed a sliver.
  Fillets are wrapped in try/except so a crashed blend degrades to a sharp edge.

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


# ── Post sections (mm) ───────────────────────────────────────────────────────
# U-channel signage posts, quoted by weight per foot; `w` is the web width across
# the flat, `d` the depth of the channel from web to flange tip.
U_CHANNEL = {
    "u_2lb": {"w": 44.5, "d": 22.0},
    "u_3lb": {"w": 50.8, "d": 25.0},
    "u_4lb": {"w": 57.2, "d": 28.0},
}

# Square tube posts (perforated telespar family and a metric section).
SQUARE_TUBE = {
    "sq_1_75": 44.45,   # 1.75 in
    "sq_2_00": 50.80,   # 2.00 in
    "sq_2_25": 57.15,   # 2.25 in
    "sq_60": 60.00,     # metric 60 mm
}

BOLT_PITCH = 25.4       # 1 in punching pitch on perforated tube and U-channel


def u_geo(name):
    """U-channel section, defaulting to the 3 lb/ft post."""
    return U_CHANNEL.get(name, U_CHANNEL["u_3lb"])


def sq_size(name):
    """Square tube across-flats size (mm), defaulting to 2.00 in."""
    return SQUARE_TUBE.get(name, SQUARE_TUBE["sq_2_00"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "u_channel"))
u_section = str(PARAM(lambda: u_section, "u_3lb"))       # U-channel post section
sq_section = str(PARAM(lambda: sq_section, "sq_2_00"))   # square tube post section
clearance = float(PARAM(lambda: clearance, 0.6))         # slop around the post (mm)
wall = float(PARAM(lambda: wall, 5.0))                   # bracket wall (mm)
plate_h = float(PARAM(lambda: plate_h, 120.0))           # bracket height up the post (mm)
sign_bolt = float(PARAM(lambda: sign_bolt, 9.53))        # sign-blank bolt Ø (3/8 in)
sign_spacing = float(PARAM(lambda: sign_spacing, 100.0)) # sign-blank hole spacing (mm)
post_bolt = float(PARAM(lambda: post_bolt, 8.0))         # post bolt Ø (mm)
post_holes = int(PARAM(lambda: post_holes, 2))           # post bolts through the bracket
arm_len = float(PARAM(lambda: arm_len, 90.0))            # blade arm projection (mm)
arm_t = float(PARAM(lambda: arm_t, 10.0))                # blade arm thickness (mm)

# Clamp so extreme UI values still build watertight.
clearance = max(0.0, min(clearance, 2.5))
wall = max(3.0, min(wall, 14.0))
plate_h = max(40.0, min(plate_h, 320.0))
sign_bolt = max(4.0, min(sign_bolt, 16.0))
sign_spacing = max(40.0, min(sign_spacing, 305.0))
post_bolt = max(4.0, min(post_bolt, 16.0))
post_holes = max(1, min(post_holes, 6))
arm_len = max(30.0, min(arm_len, 300.0))
arm_t = max(5.0, min(arm_t, 25.0))


# ── Shared helpers ───────────────────────────────────────────────────────────
def _post_bolt_zs(height):
    """Z positions for the post bolts, on the real 1 in punching pitch where the
    bracket is tall enough, otherwise spread evenly.

    Positions are clamped to keep a full bolt-radius-plus-wall margin from both
    ends, so a large bolt on a short bracket can never break out of the plate."""
    margin = post_bolt / 2.0 + max(2.5, wall * 0.5)
    lo, hi = margin, height - margin
    if hi <= lo:
        return [height / 2.0]
    n = post_holes
    span = (n - 1) * BOLT_PITCH
    if n > 1 and span <= (hi - lo):
        z0 = (height - span) / 2.0
        return [z0 + i * BOLT_PITCH for i in range(n)]
    if n == 1:
        return [height / 2.0]
    step = (hi - lo) / float(n - 1)
    return [lo + i * step for i in range(n)]


def _sign_bolt_zs(height):
    """Z positions for the sign-blank bolts, on `sign_spacing` centres, clamped so
    both holes stay inside the plate with a full margin."""
    margin = sign_bolt / 2.0 + max(2.5, wall * 0.5)
    lo, hi = margin, height - margin
    if hi <= lo:
        return [height / 2.0]
    sp = min(sign_spacing, hi - lo)
    if sp < 1.0:
        return [height / 2.0]
    z0 = (height - sp) / 2.0
    return [z0, z0 + sp]


def _drill_y(body, zs, dia, x_center, y_from, y_len):
    """Drill holes along Y (through the plate thickness) at each z. Every hole runs
    fully through and breaks out on both faces — never a blind pocket."""
    for z in zs:
        h = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(x_center, z, -y_from))
            .circle(dia / 2.0)
            .extrude(y_len)
        )
        body = body.cut(h)
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_u_channel():
    """A bracket for a U-channel post: a back plate that beds against the post web,
    with a shallow channel pocket that locates on the web and post bolts through it.
    The sign blank bolts to the front face on its own punched spacing."""
    g = u_geo(u_section)
    pw = g["w"] + 2.0 * clearance          # web width plus fit
    plate_w = pw + 2.0 * wall
    plate_t = wall + max(2.0, wall * 0.5)  # thickness front-to-back
    pocket_d = min(max(1.5, wall * 0.5), plate_t - wall * 0.6)

    body = cq.Workplane("XY").box(plate_w, plate_t, plate_h, centered=(True, True, False))
    try:
        body = body.edges("|Y").fillet(min(4.0, wall * 0.8))
    except Exception:
        pass

    # Locating pocket for the post web, opened to the back (-Y) face: a channel, so
    # it is never a sealed void.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, -plate_t / 2.0 - 0.5, -1.0))
        .box(pw, pocket_d + 0.5, plate_h + 2.0, centered=(True, False, False))
    )
    body = body.cut(pocket)

    # Post bolts on the 1 in punching pitch, through the full plate thickness.
    body = _drill_y(body, _post_bolt_zs(plate_h), post_bolt, 0.0,
                    plate_t / 2.0 + 1.0, plate_t + 2.0)

    # Sign-blank bolts, offset to either side of the post centreline so they clear
    # the post bolts, at the blank's own vertical spacing.
    x_off = pw / 2.0 + wall / 2.0
    for sx in (-1.0, 1.0):
        body = _drill_y(body, _sign_bolt_zs(plate_h), sign_bolt, sx * x_off,
                        plate_t / 2.0 + 1.0, plate_t + 2.0)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_square_tube():
    """A bracket for a square tube post: a three-sided clamp that wraps the tube on
    three faces and bolts through, leaving the fourth face open so the bracket can be
    fitted without dismantling the post."""
    s = sq_size(sq_section) + 2.0 * clearance
    outer = s + 2.0 * wall
    front_t = wall + max(2.0, wall * 0.5)   # front plate is thicker: it carries the sign

    body = (
        cq.Workplane("XY")
        .box(outer, outer + (front_t - wall), plate_h, centered=(True, True, False))
    )
    try:
        body = body.edges("|Z").fillet(min(4.0, wall * 0.8))
    except Exception:
        pass

    # Tube pocket, opened to the -Y face (three-sided clamp -> never a sealed void).
    y_back = -(outer + (front_t - wall)) / 2.0
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, y_back - 0.5, -1.0))
        .box(s, s + 0.5 + wall, plate_h + 2.0, centered=(True, False, False))
    )
    body = body.cut(pocket)

    # Post bolts through the two side cheeks (along X, fully through both).
    reach = outer + 10.0
    for z in _post_bolt_zs(plate_h):
        h = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, z, -reach / 2.0))
            .circle(post_bolt / 2.0)
            .extrude(reach)
        )
        body = body.cut(h)

    # Sign-blank bolts through the front plate (along Y).
    x_off = min(s / 2.0 + wall / 2.0, outer / 2.0 - sign_bolt / 2.0 - wall * 0.6)
    depth_y = outer + (front_t - wall) + 2.0
    for sx in (-1.0, 1.0):
        body = _drill_y(body, _sign_bolt_zs(plate_h), sign_bolt, sx * x_off,
                        -y_back + 1.0, depth_y)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_blade_arm():
    """A perpendicular arm that stands a sign off the post at 90 degrees, for a
    street-name blade or a fingerpost. The post collar and the arm are one blank."""
    s = sq_size(sq_section) + 2.0 * clearance
    collar_out = s + 2.0 * wall
    arm_h = max(30.0, min(plate_h, 140.0))
    ov = min(2.0, wall * 0.6)

    # Post collar: a square sleeve, opened to -Y like the clamp so it can be fitted
    # over an installed post.
    collar = cq.Workplane("XY").box(collar_out, collar_out, arm_h,
                                    centered=(True, True, False))
    try:
        collar = collar.edges("|Z").fillet(min(4.0, wall * 0.8))
    except Exception:
        pass

    # Arm projecting in +X, overlapping into the collar volumetrically.
    arm_w = max(arm_t, wall * 2.0)
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(collar_out / 2.0 - ov, 0.0, 0.0))
        .box(arm_len + ov, arm_w, arm_h, centered=(False, True, False))
    )
    body = collar.union(arm)

    # Tube pocket through the collar, opened to -Y.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, -collar_out / 2.0 - 0.5, -1.0))
        .box(s, s + 0.5 + wall, arm_h + 2.0, centered=(True, False, False))
    )
    body = body.cut(pocket)

    # Post bolts through the collar cheeks (along X, fully through).
    reach = collar_out + arm_len + 20.0
    for z in _post_bolt_zs(arm_h):
        h = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, z, -reach / 2.0))
            .circle(post_bolt / 2.0)
            .extrude(reach / 2.0)   # stop before the arm so the arm stays solid
        )
        body = body.cut(h)

    # Sign-blank bolts through the arm, drilled along Y at the blank's spacing but
    # laid out along the arm's length (X) since the arm is the mounting face.
    margin = sign_bolt / 2.0 + max(2.5, wall * 0.6)
    x_start = collar_out / 2.0 + margin
    x_end = collar_out / 2.0 + arm_len - margin
    if x_end > x_start:
        sp = min(sign_spacing, x_end - x_start)
        xs = [x_start, x_start + sp] if sp >= 1.0 else [(x_start + x_end) / 2.0]
        zc = arm_h / 2.0
        for x in xs:
            h = (
                cq.Workplane("XZ")
                .transformed(offset=cq.Vector(x, zc, -(arm_w / 2.0 + 1.0)))
                .circle(sign_bolt / 2.0)
                .extrude(arm_w + 2.0)
            )
            body = body.cut(h)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "u_channel": build_u_channel,
    "square_tube": build_square_tube,
    "blade_arm": build_blade_arm,
}

result = _dispatch.get(target_part, build_u_channel)()
