# DIN Rail Relay Holder

Holds **cube relays** and **solid-state relays (SSRs)** on standard top-hat
**DIN rail (TS35, DIN EN 60715 — 35 mm across the lips, 7.5 mm deep)**, generated
with **CadQuery** (B-Rep). Part of the **Yantra4D Hyperobjects Commons**. Official
visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Socket Cradle** | `socket_cradle` | Four walls above the DIN clip forming a pocket a plug-in cube relay drops into (open top vents it), with a wire-access window in the front wall. |
| **Finger-Safe Guard** | `finger_guard` | A relay channel capped by a louvred roof so a probe can't touch live terminals but wires still exit and heat escapes. |
| **SSR Heat-Sink Mount** | `ssr_heatsink` | A vertical face plate the SSR bolts flat against, backed by a row of cooling fins, with two SSR bolt slots. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Relay Body | `relay_w` / `relay_l` / `relay_h` | 28 / 28 / 32 mm | Relay body footprint and height. |
| Features | `wall` | 2.6 mm | Cradle / guard / face wall thickness. |
| Features | `fin_count` / `fin_h` | 6 / 16 mm | SSR cooling fins (`ssr_heatsink`). |
| Features | `vent_w` | 3.0 mm | Louvre slot width (`finger_guard`). |
| DIN Clip | `plate_th` | 4.0 mm | Mount-plate thickness of the clip back. |

## The DIN clip (why it grips, and stays watertight)

The clip back is the proven **DIN TS35 idiom**: a mount plate with a **rigid
reference hook** and a **compliant spring hook**, each an XZ profile extruded
symmetrically about the rail axis and **unioned with overlap** into the plate.
The relay cavity is **open at the top** (or vented through the louvres) so no
sealed void forms; the wire window, louvres and bolt slots are **through-cuts**.
Cradle walls and fins are **unioned overlapping solids** (never tangent). Blanks
are filleted before feature cuts.

## Presets

- **Cube Relay (28 mm)** — the reference cradle for a common plug-in cube relay.
- **40A SSR Heat-Sink** — a wide finned face for a 40 A solid-state relay.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **DIN TS35 Rail Clip** (`rail`, *DIN EN 60715*) — the top-hat clip back.
    Mates `din-module`, `busbar-support`, `devboard-tray`, `din-rail-clip`.
  - **Relay Body Cradle** (`pocket`, *internal*) — the captured relay volume
    defined by `relay_w`, `relay_l`, `relay_h`.
- **Material awareness:** `tolerance_by_material` is declared — the relay pocket
  fit and spring-hook grip tune per material/printer.
- **Societal benefit:** relays and SSRs are the switching muscle of control
  panels, but off-the-shelf DIN holders are brand-specific and finger-safe guards
  are often missing on retrofits; a printed cradle, guard or finned mount keeps
  switching gear on the rail, touch-safe and cooled.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- All shipped modes and per-mode extreme parameter cases render **watertight**,
  single-body, in well under 20 s.
