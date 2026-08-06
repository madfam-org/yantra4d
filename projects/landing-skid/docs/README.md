# Landing Skid

**Printable landing gear for FPV & RC multirotors**, generated with **CadQuery**
(B-Rep). A splayed leg drops from the frame to a skid foot, protecting the belly,
camera and gimbal on landing. It attaches by **clamping around a round arm/boom**
or by **bolting to a frame plate** using the standard square motor bolt pattern.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Boom-Clamp Skid** | `clamp_skid` | A split clamp collar wraps a round arm/boom, then a splayed leg and foot. |
| **Bolt-On Skid** | `bolt_skid` | A flat plate with the square motor bolt pattern, then a splayed leg and foot — bolts under a motor mount or frame plate. |
| **Tall Gear** | `tall_gear` | The bolt-on skid, taller (adds `tall_extra`) with a wider foot, to lift the belly for a camera / gimbal / cargo. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Leg & Foot | `skid_h` | 45 mm | Frame down to the foot. |
| Leg & Foot | `leg_w` / `leg_t` | 8 / 5 mm | Leg cross-section. |
| Leg & Foot | `foot_len` / `foot_w` | 40 / 10 mm | Skid foot size. |
| Leg & Foot | `splay` | 12° | Outward splay for a wider stance. |
| Boom Clamp | `boom_dia` / `clamp_wall` | 12 / 3 mm | Round boom the clamp grips (clamp mode). |
| Bolt Mount | `motor_pattern` | 16x16 | Square bolt pattern (`9x9` M2, `16x16`/`19x19` M3). |
| Bolt Mount | `tall_extra` | 35 mm | Added height for the tall gear (tall mode). |

## Interfaces

Two attachment interfaces cover the two ways a skid mounts. The **boom clamp** is
a split collar bored to `boom_dia` (a socket around a round arm). The **frame
bolt pattern** reuses the shared square motor bolt-pattern helper (the same one
used by `motor-soft-mount` and `prop-guard`), so a bolt-on skid mounts under any
matching motor mount. The leg is splayed by `splay` about the frame level and the
foot is placed exactly where the leg bottom lands, so the geometry stays a clean
solid at any splay angle.

## Presets

- **5-inch Boom Clamp** — clamps a 12 mm freestyle arm.
- **Bolt-On 16x16** — flat-plate skid on the common 16×16 pattern.
- **Camera Tall Gear** — tall bolt-on gear that lifts a camera clear.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Boom Clamp** (`socket`, *internal*) — the split collar bored to the boom,
    defined by `boom_dia`, `clamp_wall`.
  - **Frame Bolt Pattern** (`bolt_pattern`, *16×16 / 19×19 / 9×9 brushless motor
    mount*) — the square 4-hole plate, defined by `motor_pattern`. Interoperable
    with every FPV motor mount and the other drone-Commons parts on the same
    pattern.
- **Material awareness:** `tolerance_by_material` is declared — the clamp bore
  and leg thickness are exposed so grip and impact toughness can be tuned per
  material.
- **Societal benefit:** a belly landing on a camera or gimbal ends an expensive
  part fast; on-demand skids sized to the exact boom or bolt pattern absorb the
  touchdown and lift the payload clear, and a snapped leg is a cheap reprint.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Fillets are clamped and guarded. All modes render
  **watertight** in well under 20 s.
