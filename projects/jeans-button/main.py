"""Jeans Tack Button — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The no-sew tack button of jeans and workwear — the rigid hard good the Fashion Cabinet
`jeans-button` notion places and bridges to here for its geometry. A domed button head on
a hollow socket that the tack (a separate nail) rivets into through the waistband. Printed
rigid it stands in for the metal jeans button.

Modes (dispatched via `target_part`):
  * "set"    — button head + tack side by side.
  * "button" — the head + socket only.
  * "tack"   — the nail that sets it.

Geometry: the head is a chamfered cylinder; the socket a bored cylinder under it; the tack
a small cylinder with a flat head. Small boolean count → fast, watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `head_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
head_dia  = float(PARAM(lambda: head_dia,  17.0))    # button head diameter (mm)
head_h    = float(PARAM(lambda: head_h,    5.0))     # head height (mm)
socket_dia = float(PARAM(lambda: socket_dia, 9.0))   # socket (under-head) diameter (mm)
socket_h  = float(PARAM(lambda: socket_h,  4.0))     # socket height (mm)
tack_dia  = float(PARAM(lambda: tack_dia,  4.0))     # tack (nail) shank diameter (mm)
tack_h    = float(PARAM(lambda: tack_h,    10.0))    # tack length (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|button|tack

# ── Safe clamps ──────────────────────────────────────────────────────────────
head_dia   = max(10.0, min(head_dia, 28.0))
head_h     = max(2.0, min(head_h, 10.0))
socket_dia = max(5.0, min(socket_dia, head_dia - 3.0))
socket_h   = max(2.0, min(socket_h, 10.0))
tack_dia   = max(2.0, min(tack_dia, socket_dia - 1.0))
tack_h     = max(4.0, min(tack_h, 20.0))


def build_button():
    """Domed head over a bored socket."""
    head = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, socket_h + head_h / 2.0))
        .circle(head_dia / 2.0)
        .extrude(head_h)
    )
    try:
        head = head.edges(">Z").fillet(min(head_h, head_dia * 0.15) * 0.9)
    except Exception:
        pass
    socket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, socket_h / 2.0))
        .circle(socket_dia / 2.0)
        .extrude(socket_h)
    )
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, socket_h / 2.0))
        .circle((tack_dia + 0.4) / 2.0)
        .extrude(socket_h + head_h)
        .translate((0, 0, -1.0))
    )
    return head.union(socket).cut(bore)


def build_tack():
    """The nail: a flat head + a shank."""
    flat_h = 1.4
    head = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, flat_h / 2.0))
        .circle(tack_dia * 0.9)
        .extrude(flat_h)
    )
    shank = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, flat_h + tack_h / 2.0))
        .circle(tack_dia / 2.0)
        .extrude(tack_h)
    )
    return head.union(shank)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "button":
    result = build_button()
elif target_part == "tack":
    result = build_tack()
else:
    result = build_button().union(build_tack().translate((head_dia, 0, 0)))
