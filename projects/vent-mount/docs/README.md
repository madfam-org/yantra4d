# Car Vent / Dash Phone Mount

A phone/accessory mount that clips onto a car A/C vent blade, generated with
**CadQuery** (B-Rep). The J-hook clip hangs over a vent fin of thickness `blade_t`
with a sprung back leg for a friction hold.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cradle Mount** | `cradle_mount` | Vent clip + an adjustable phone cradle (floor lip + two side arms sized to `phone_w`). |
| **Magnetic Mount** | `magnetic_mount` | Vent clip + a disc carrying magnet pockets for a magnetic phone plate. |
| **Vent Clip Only** | `clip_only` | Just the vent-blade clip. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Vent Clip | `blade_t` | 2.0 mm | Vent fin thickness the hook grips. |
| Vent Clip | `clip_w` | 22 mm | Clip span across the blade. |
| Vent Clip | `clip_drop` | 18 mm | How far the hook hangs down the front. |
| Vent Clip | `clip_clear` | 0.3 mm | Throat clearance so it slides on. |
| Vent Clip | `wall` | 3.0 mm | Clip / body wall thickness. |
| Cradle | `phone_w` | 72 mm | Phone width for the cradle arms. |
| Magnet Pockets | `magnet_d` | 8.1 mm | Pocket diameter (≈ 8 mm magnet). |
| Magnet Pockets | `magnet_h` | 2.1 mm | Pocket depth. |

## The clip interface

The clip is a J-hook whose **throat opening equals `blade_t` + `clip_clear`**, so
it grips the driver's actual vent fin. Measure your vent blade and set `blade_t` —
the throat is verified open (the blade slides into a real gap, not a solid block).

## Presets

- **Thin-Blade Cradle** — a 1.5 mm blade with a phone cradle.
- **Thick-Blade Magnetic** — a 3.0 mm blade with a magnetic disc.
- **Spare Vent Clip** — just the clip.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interface:** **Vent Blade Clip** (`snap`, internal) — defined by `blade_t`,
  `clip_clear`, `clip_drop`. The throat is sized to the real vent fin; any body
  built on the same clip shares the grip geometry.
- **Material awareness:** `tolerance_by_material` — the sprung friction grip depends
  on filament stiffness, so tune `clip_clear` / `wall` per material.
- **Societal benefit:** car phone mounts are consumable plastic that break; a
  right-sized, repairable clip printed on demand replaces them.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
