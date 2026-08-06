# Fridge Can Dispenser

A gravity-fed can dispenser generated with **CadQuery** (B-Rep). Load cans on top,
they roll down an inclined lane, and you take the front one from the bottom while
the next rolls into place. Sized to the can diameter (`can_dia`, **66 mm standard
soda can** by default).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Single Lane** | `single_lane` | One gravity lane, cans single file with a front stop. |
| **Double Lane** | `double_lane` | Two side-by-side lanes sharing a centre wall (2× capacity). |
| **Compact** | `compact` | A short single lane (≤3 cans) for small fridges / door shelves. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Can Size | `can_dia` | 66 mm | **Can diameter (66 = soda, 53 = slim).** |
| Can Size | `can_len` | 123 mm | Can length lying across the lane. |
| Can Size | `capacity` | 5 | Cans queued per lane (compact caps at 3). |
| Gravity Rail | `incline` | 6° | Slope so cans roll forward. |
| Gravity Rail | `clearance` | 2.0 mm | Per-side gap so cans roll freely. |
| Gravity Rail | `front_lip` | 12 mm | Curb that holds the lead can until taken. |
| Gravity Rail | `feed` | single-lane | Reference feed style select. |
| Structure | `wall` | 2.4 mm | Wall and floor thickness. |

## Presets

- **Soda Can Lane (5)** — 66 mm cans, single lane of five.
- **Double Soda Rack** — two lanes of five 66 mm cans.
- **Slim Can (Door Shelf)** — 53 mm slim cans, compact three-can lane.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:**
  - **Can Gravity Rail** (`rail`, standard **"standard can Ø"**) — the sloped
    U-channel lane, defined by `can_dia`, `can_len`, `incline`, `clearance`,
    `front_lip`. Any can matching `can_dia` (± clearance) feeds; changing
    `can_dia` alone retargets soda / slim / seltzer. Each lane reuses this rail.
- **Material awareness:** side `clearance` is exposed so roll fit can be tuned per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** turns loose fridge cans into a first-in-first-out queue that
  keeps the coldest cans forward and reclaims shelf space.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The body is a solid block with each lane cut as a **tilted box**, so the sloped
  floor and retaining walls are watertight by construction (verified: interior
  floor rises monotonically front→back, ~3→30 mm at defaults; double-lane keeps a
  solid centre wall). Front dispensing window + top loading opening are separate cuts.
- The script is **self-contained** (sandbox-safe): parameters via
  `PARAM(lambda: name, default)`; the final solid is assigned to `result`.
