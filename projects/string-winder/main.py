"""
String Winder / Peg Aid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The peg winder that every guitarist keeps in the case: a crank whose socket fits
over the tuning-machine BUTTON so strings wind up fast, plus a notch that pops
acoustic bridge pins. The functional interface is the tuner-button socket (a
cupped slot that grips the button) and the bridge-pin slot.

Real dimensions encoded (nominal):
  - Tuner post ~6 mm; tuner buttons run ~14-19 mm across the flats.
  - Bridge pins taper ~5 mm at the head; the puller slot is ~5-6 mm.
  - String gauges .010-.046 in (0.25-1.17 mm) inform the string-notch sizes.

Modes:
  - peg_winder : a curved crank handle ending in a cupped button socket, with a
    bridge-pin puller notch cut in the rim (the classic tool).
  - pin_puller : a standalone fork lever that hooks under and pops bridge pins.
  - multi_socket: a knob carrying several button sockets of different widths so
    one tool fits open-gear, sealed and classical tuners.

Watertight strategy:
  The button socket is a blind cup bored from the OPEN end (vents to outside) —
  not a sealed cavity. The bridge-pin slot is an obround through-cut in the rim.
  The handle is a solid lofted body unioned into the socket boss with overlap.
  Blanks are fillet-cleaned BEFORE feature cuts. No trapped voids.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` pre-injected; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    """Injected global if present else default; `except` catches the unbound-name
    NameError the sandbox raises (globals()/NameError are hidden)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "peg_winder"))
# "peg_winder" | "pin_puller" | "multi_socket"

button_w   = float(PARAM(lambda: button_w, 16.0))   # tuner button width across flats (mm)
socket_dep = float(PARAM(lambda: socket_dep, 10.0)) # socket cup depth (mm)
fit_clear  = float(PARAM(lambda: fit_clear, 0.4))   # socket fit slop (per side)
handle_len = float(PARAM(lambda: handle_len, 70.0)) # crank handle length (mm)
pin_slot   = float(PARAM(lambda: pin_slot, 5.5))    # bridge-pin puller slot (mm)
wall       = float(PARAM(lambda: wall, 4.0))        # body wall thickness (mm)

# Clamp to sane ranges so extreme UI values still build watertight.
button_w   = max(10.0, min(button_w, 24.0))
socket_dep = max(5.0, min(socket_dep, 18.0))
fit_clear  = max(0.0, min(fit_clear, 1.0))
handle_len = max(35.0, min(handle_len, 120.0))
pin_slot   = max(3.0, min(pin_slot, 9.0))
wall       = max(3.0, min(wall, 8.0))

_sock_w = button_w + 2.0 * fit_clear       # socket internal width
_boss_r = _sock_w / 2.0 + wall             # socket boss outer radius


# ── Helpers (inlined) ─────────────────────────────────────────────────────────
def _button_socket(inner_w, depth, boss_r, z0):
    """A cupped socket boss: a solid cylinder with a hexagonal-ish blind pocket
    bored from the TOP (open end, vented). The pocket is an obround so it grips
    both round and slabbed buttons. Returns the boss solid, pocket open upward."""
    boss = cq.Workplane("XY").circle(boss_r).extrude(depth + wall).translate((0, 0, z0))
    # Blind pocket from the top (open end) — obround grips flats or round.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0 + wall))
        .slot2D(inner_w, inner_w * 0.72, angle=0)
        .extrude(depth + 1.0)
    )
    boss = boss.cut(pocket)
    try:
        boss = boss.edges(">Z").fillet(min(wall * 0.4, 1.2))
    except Exception:
        pass
    return boss


# ── Part builders ────────────────────────────────────────────────────────────
def build_peg_winder():
    """A curved crank handle ending in a cupped button socket, with a bridge-pin
    puller notch cut in the socket rim."""
    boss = _button_socket(_sock_w, socket_dep, _boss_r, 0.0)
    boss_h = socket_dep + wall

    # Handle: a solid horizontal capsule (obround bar) reaching out to +X from
    # the boss, unioned in with overlap. Obround gives a comfortable grip barrel
    # and is far more mesh-robust than a two-wire loft.
    grip_r = max(6.0, wall + 3.0)
    handle = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, boss_h * 0.4, 0))
        .center(_boss_r - wall + handle_len / 2.0, 0)
        .slot2D(handle_len, grip_r * 1.6, angle=0)
        .extrude(grip_r, both=True)
    )
    body = boss.union(handle)

    # Bridge-pin puller notch: an obround slot cut into the boss rim from +Y,
    # through the wall (vents to outside).
    notch = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, boss_h * 0.5, _boss_r))
        .slot2D(pin_slot, pin_slot * 0.7, angle=0)
        .extrude(-wall * 2.5)
    )
    body = body.cut(notch)
    return body


def build_pin_puller():
    """A standalone fork lever: a flat handle ending in a forked slot that hooks
    under an acoustic bridge pin's head and levers it out."""
    length = handle_len + 20.0
    body_h = 20.0
    th = wall + 2.0
    plate = cq.Workplane("XY").box(length, body_h, th, centered=(True, True, False))
    try:
        plate = plate.edges("|Z").fillet(3.0)
    except Exception:
        pass

    # Fork slot: an obround open-ended slot cut from the -X end inward, sized to
    # slip around the pin shaft under the head. Vents out the end → no cavity.
    fork = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-length / 2.0 + pin_slot * 1.4, 0, -1.0))
        .slot2D(pin_slot * 3.0, pin_slot, angle=0)
        .extrude(th + 2.0)
    )
    body = plate.cut(fork)

    # A fulcrum bump under the fork so it levers cleanly.
    bump = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-length / 2.0 + pin_slot * 3.5, 0, 0))
        .circle(body_h * 0.35)
        .extrude(-3.0)
    )
    body = body.union(bump)

    # A grip hole at the far end (through, vented).
    grip = cq.Workplane("XY").circle(6.0).extrude(th + 2.0).translate((length / 2.0 - 12.0, 0, -1.0))
    body = body.cut(grip)
    return body


def build_multi_socket():
    """A knob carrying three button sockets of different widths (open-gear,
    sealed, classical) around its rim, so one tool fits several tuner types."""
    widths = [max(10.0, button_w - 4.0), button_w, min(24.0, button_w + 4.0)]
    knob_r = _boss_r + 14.0
    knob_h = socket_dep + wall
    knob = cq.Workplane("XY").circle(knob_r).extrude(knob_h)
    try:
        knob = knob.edges("|Z").fillet(3.0)
    except Exception:
        pass

    # Grip flutes around the knob (single polar-array cut = one boolean).
    try:
        flutes = (
            cq.Workplane("XY")
            .polarArray(radius=knob_r, startAngle=0, angle=360, count=16)
            .rect(1.6, 4.5)
            .extrude(knob_h + 2.0)
            .translate((0, 0, -1.0))
        )
        knob = knob.cut(flutes)
    except Exception:
        pass

    body = knob
    # Three sockets bored from the TOP at 3 radial positions (blind cups, vented).
    for i, w in enumerate(widths):
        ang = 2.0 * math.pi * i / 3.0
        x = (knob_r * 0.45) * math.cos(ang)
        y = (knob_r * 0.45) * math.sin(ang)
        iw = w + 2.0 * fit_clear
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, wall))
            .slot2D(iw, iw * 0.72, angle=0)
            .extrude(socket_dep + 1.0)
        )
        body = body.cut(pocket)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pin_puller":
    result = build_pin_puller()
elif target_part == "multi_socket":
    result = build_multi_socket()
else:
    result = build_peg_winder()
