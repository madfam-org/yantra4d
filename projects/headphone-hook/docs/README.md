# Headphone / Headset Hook

A headset hook generated with **CadQuery** (B-Rep) that hangs a headset by its
headband from a broad, rounded cradle so the band does not develop a dent. Pick
the mount style that suits your setup.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Under-Desk Hook** | `under_desk_hook` | An L-bracket: a top plate screwed to the underside of a desktop, an arm dropping down and reaching forward into an up-turned cradle. |
| **Wall Hook** | `wall_hook` | A flat vertical screw plate with a hook arm reaching out and up into the cradle. |
| **Desk Clamp** | `desk_clamp` | A screwless C-clamp that grips a desk edge of thickness `desk_t`, with the cradle on the front. |

The studio dispatches the active part via `target_part`
(`under_desk_hook` / `wall_hook` / `desk_clamp`); the same choice is exposed as
the `mount` parameter so the script works when driven purely by parameter
values. Each mode renders distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Mount | `mount` | `under_desk` | `under_desk`, `wall`, or `clamp`. |
| Cradle & Arm | `cradle_w` | 28.0 mm | Width of the rounded band saddle. |
| Cradle & Arm | `reach` | 55.0 mm | How far the cradle projects (Under-Desk, Wall). |
| Cradle & Arm | `drop` | 45.0 mm | Arm drop below the desktop (Under-Desk). |
| Cradle & Arm | `thick` | 8.0 mm | Arm / plate / jaw thickness. |
| Fixing | `plate_w` / `plate_len` | 40 / 55 mm | Screw plate size (screw modes). |
| Fixing | `screw_dia` | 4.5 mm | Screw clearance hole (M4 ≈ 4.5). |
| Fixing | `desk_t` | 25.0 mm | Desk edge thickness (Clamp). |
| Fixing | `clamp_depth` | 45.0 mm | Clamp grip depth over the desktop (Clamp). |

## Presets

- **Under-Desk Headset** — a 30 mm cradle L-bracket for under a desktop.
- **Wall (wide cradle)** — a 45 mm wide-cradle wall plate.
- **Clamp (25 mm desk)** — a screwless clamp for a 25 mm desk edge.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Mount Screw Pattern** (`bolt_pattern`, internal) — the two-hole screw
    plate for the Under-Desk and Wall mounts, defined by `plate_w`,
    `plate_len`, `screw_dia`, and `thick`.
  - **Desk-Edge Clamp Profile** (`profile`, internal) — the C-section that grips
    a `desk_t`-thick edge over `clamp_depth`.
  - **Headband Cradle** (`profile`, internal) — the broad half-round saddle
    (`cradle_w`, `reach`) shared by every mount.
- **Material awareness:** screw clearance follows the metric screw (M4 ≈ 4.5 mm);
  the clamp jaw gap equals the raw `desk_t`, so add a per-material clearance for
  a firm grip. `tolerance_by_material` is declared.
- **Societal benefit:** reclaims desk space and protects an expensive headset —
  a broad, load-spreading cradle prevents the headband dent, and the screwless
  clamp adapts to any desk thickness without drilling.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- The clamp mouth is eased with boolean lead-in chamfers rather than a
  `.fillet()`, because filleting the C + cradle topology yields a non-manifold
  shell; every mode and preset renders **watertight**.
