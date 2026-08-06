# Slow-Feed Pet Bowl

A food bowl whose floor carries a maze of concentric rings and radial spokes so
a fast-eating dog or cat has to work the kibble out of the channels, slowing
gulping and easing digestion. Generated with **CadQuery** (B-Rep). Also a raised
bowl stand and a drop-in maze insert that converts an existing plain bowl.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print the bowl and maze insert in **food-safe filament** and clean regularly.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Slow-Feed Bowl** | `slow_bowl` | A tapered bowl with the maze ridges built integrally into the floor. |
| **Bowl Stand** | `bowl_stand` | A raised, flared ring that cradles a bowl base at a comfortable height. |
| **Maze Insert** | `maze_insert` | Just the maze puck, to drop into an existing bowl. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bowl | `bowl_dia` | 180.0 mm | Top inner diameter. |
| Bowl | `bowl_depth` | 55.0 mm | Inner depth. |
| Bowl | `wall` | 4.0 mm | Wall / floor thickness. |
| Maze | `maze_rings` | 3 | Concentric ridge rings (more = slower). |
| Maze | `maze_spokes` | 6 | Radial ridges (0 = rings only). |
| Maze | `ridge_h` | 22.0 mm | Ridge height (trimmed below the rim). |
| Maze | `ridge_t` | 6.0 mm | Ridge thickness. |
| Stand | `stand_h` | 70.0 mm | Raised stand height. |

## Presets

- **Large-Dog Slow Bowl** — 200 mm, 3 rings + 8 spokes.
- **Cat Slow Bowl** — 120 mm, gentler maze.
- **Raised Bowl Stand** — 90 mm elevated stand.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Slow-Feed Maze** (`surface`, internal) — the floor ridge field, defined by
    `maze_rings`, `maze_spokes`, `ridge_h`, `ridge_t`, `bowl_dia`. The same maze
    parameters drive both the integral bowl and the drop-in insert.
- **Material awareness:** `tolerance_by_material` is declared — insert diameter
  can be nudged for the print material to sit low in the target bowl.
- **Societal benefit:** a slow-feed maze tuned to the animal's size and eating
  speed reduces bloat and gulping, printable at any diameter.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Maze ridges overlap the floor volumetrically, so all outputs are
  **watertight**.
