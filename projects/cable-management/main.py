"""
Cable Comb / Clip / Raceway — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Desk- and wall-cable management in three parts, all sharing one internal cable
channel profile so a cable routed through a comb, snapped into a clip, and run
in a raceway is dimensioned consistently.

Three parts (dispatched through `target_part`):
  * "clip"    — a C-clip whose open mouth snaps around a cable of `cable_dia`.
                The mount is selectable (`mount_type`): a screw-hole flange, an
                adhesive pad, or a t-slot-style tab that slides into a rail.
  * "comb"    — a bar with `slot_count` open-top slots of `cable_dia` that comb a
                ribbon of cables into parallel lanes.
  * "raceway" — a U-channel duct of `channel_w` × `channel_h` with an optional
                snap-on lid that closes the top.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cable_dia`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "clip"))    # clip | comb | raceway
mount_type = str(PARAM(lambda: mount_type, "screw"))     # screw | adhesive | tslot

cable_dia = float(PARAM(lambda: cable_dia, 6.0))         # nominal cable diameter (mm)
wall = float(PARAM(lambda: wall, 2.4))                   # structural wall thickness

# Clip
clip_gap = float(PARAM(lambda: clip_gap, 0.75))         # mouth opening factor of cable_dia
clip_len = float(PARAM(lambda: clip_len, 10.0))         # clip length along the cable

# Comb
slot_count = int(PARAM(lambda: slot_count, 5))          # number of cable lanes
comb_h = float(PARAM(lambda: comb_h, 14.0))             # comb bar height
comb_t = float(PARAM(lambda: comb_t, 6.0))              # comb bar thickness (along cable)

# Raceway
channel_w = float(PARAM(lambda: channel_w, 16.0))       # internal channel width
channel_h = float(PARAM(lambda: channel_h, 12.0))       # internal channel height
raceway_len = float(PARAM(lambda: raceway_len, 80.0))   # raceway length
raceway_lid = bool(PARAM(lambda: raceway_lid, True))    # generate a snap-on lid

# Sanitize
cable_dia = max(1.5, cable_dia)
wall = max(1.2, wall)
slot_count = max(1, min(24, slot_count))


# ── Shared helpers ────────────────────────────────────────────────────────────
def screw_flange(width, thick, hole_dia=4.2):
    """A small mounting ear with a countersunk-friendly through hole, lying flat
    on XY with its base at z=0, centred on the origin in X."""
    ear = cq.Workplane("XY").box(width, width, thick, centered=(True, True, False))
    try:
        ear = ear.edges("|Z").fillet(min(width / 3.0, 3.0))
    except Exception:
        pass
    bore = (
        cq.Workplane("XY")
        .circle(hole_dia / 2.0)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    return ear.cut(bore)


def tslot_tab(width, thick):
    """A T-slot-style tab: a neck plus a wider head that slides into a rail
    channel. Base at z=0, extends up +Z, centred in X."""
    neck_w = width * 0.5
    head_w = width
    neck = cq.Workplane("XY").box(neck_w, thick, thick, centered=(True, True, False))
    head = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, thick))
        .box(head_w, thick, thick, centered=(True, True, False))
    )
    return neck.union(head)


# ── Clip ───────────────────────────────────────────────────────────────────────
def build_clip():
    """A C-profile that snaps around a cable, plus a selectable mount below it.

    The C is an annulus (outer R, inner R) with a mouth cut on top sized to
    `clip_gap × cable_dia` so the cable presses in and is retained. Extruded
    along the cable by `clip_len`."""
    r_in = cable_dia / 2.0
    r_out = r_in + wall
    length = max(cable_dia, clip_len)

    # Annular C lying with its axis along Y (the cable direction).
    ring = (
        cq.Workplane("XZ")
        .circle(r_out)
        .circle(r_in)
        .extrude(length)
        .translate((0, -length / 2.0, r_out))   # lift so base sits near z=0
    )
    # Mouth: remove a top wedge/slot so the cable can enter. Width = gap.
    mouth_w = max(1.0, min(clip_gap, 0.95) * cable_dia)
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, r_out + r_in * 0.4))
        .box(mouth_w, length + 2.0, r_out * 2.0, centered=(True, True, False))
    )
    clip = ring.cut(mouth)

    # Mount underneath (base of the C is at z≈0).
    clip = clip.union(_clip_mount(r_out, length))
    return clip


def _clip_mount(r_out, length):
    """Attach the selected mount to the underside of the clip. Returns a solid
    that overlaps the clip body so the union is watertight."""
    base_w = max(r_out * 2.0, 12.0)
    if mount_type == "adhesive":
        # A flat pad the clip sits on (adhesive foam goes on its underside).
        pad = cq.Workplane("XY").box(base_w, length, wall, centered=(True, True, False))
        try:
            pad = pad.edges("|Z").fillet(min(base_w / 4.0, 3.0))
        except Exception:
            pass
        return pad.translate((0, 0, 0))
    if mount_type == "tslot":
        # A short foot plus a T-tab underneath (tab hangs below z=0).
        foot = cq.Workplane("XY").box(base_w, length, wall, centered=(True, True, False))
        tab = tslot_tab(base_w * 0.6, wall).translate((0, 0, -2.0 * wall))
        return foot.union(tab)
    # default: screw flange centred under the clip
    return screw_flange(base_w, wall)


# ── Comb ────────────────────────────────────────────────────────────────────────
def build_comb():
    """A bar with `slot_count` open-top slots that separate cables into lanes.
    Each slot is `cable_dia` wide with a rounded bottom; the bar runs along X."""
    slot_w = cable_dia
    pitch = slot_w + wall
    bar_w = slot_count * pitch + wall
    h = max(cable_dia + wall + 2.0, comb_h)
    t = max(cable_dia * 0.6, comb_t)

    bar = cq.Workplane("XY").box(bar_w, t, h, centered=(True, True, False))
    try:
        bar = bar.edges("|Y").fillet(min(wall, 1.5))
    except Exception:
        pass

    # Cut each lane slot from the top; leave a floor of `wall` under each slot.
    x0 = -bar_w / 2.0 + wall + slot_w / 2.0
    slot_depth = h - wall
    for i in range(slot_count):
        x = x0 + i * pitch
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0, h - slot_depth + slot_depth / 2.0))
            .box(slot_w, t + 2.0, slot_depth, centered=(True, True, True))
        )
        bar = bar.cut(slot)

    # Two screw ears so the comb can be fixed to a desk edge.
    ear_off = bar_w / 2.0 - wall
    for sx in (-1, 1):
        ear = screw_flange(max(8.0, 2.0 * wall + 4.0), wall).rotate(
            (0, 0, 0), (1, 0, 0), 90
        )
        ear = ear.translate((sx * (ear_off + wall), 0, wall + 1.0))
        try:
            bar = bar.union(ear)
        except Exception:
            pass
    return bar


# ── Raceway ─────────────────────────────────────────────────────────────────────
def build_raceway():
    """A U-channel duct: floor + two side walls, hollow along its length (Y).
    Optionally a snap-on lid printed alongside it."""
    w_in = max(cable_dia + 2.0, channel_w)
    h_in = max(cable_dia + 1.0, channel_h)
    length = max(cable_dia * 3.0, raceway_len)
    w_out = w_in + 2.0 * wall
    h_out = h_in + wall

    outer = (
        cq.Workplane("XY")
        .box(w_out, length, h_out, centered=(True, True, False))
    )
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall))
        .box(w_in, length + 2.0, h_in + wall, centered=(True, True, False))
    )
    channel = outer.cut(cavity)

    # Retention lips at the top inner edges so a lid can snap in.
    lip = min(0.8, wall * 0.4)
    for sx in (-1, 1):
        bead = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * (w_in / 2.0), 0, h_out - lip))
            .box(2.0 * lip, length, lip, centered=(True, True, False))
        )
        try:
            channel = channel.union(bead)
        except Exception:
            pass

    if not raceway_lid:
        return channel

    # Snap lid: a plate that spans the outer width with two down-tabs that catch
    # the lips. Printed to one side so it does not intersect the channel.
    lid = _raceway_lid(w_in, w_out, h_out, length, lip)
    lid = lid.translate((w_out + 8.0, 0, 0))
    return channel.union(lid)


def _raceway_lid(w_in, w_out, h_out, length, lip):
    plate = cq.Workplane("XY").box(w_out, length, wall, centered=(True, True, False))
    tabs = None
    for sx in (-1, 1):
        tab = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * (w_in / 2.0 - lip), 0, -2.0))
            .box(2.0 * lip, length, 2.0 + lip, centered=(True, True, False))
        )
        tabs = tab if tabs is None else tabs.union(tab)
    if tabs is not None:
        plate = plate.union(tabs)
    return plate


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "comb":
    result = build_comb()
elif target_part == "raceway":
    result = build_raceway()
else:
    result = build_clip()
