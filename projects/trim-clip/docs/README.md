# Trim Panel Clip

A parametric **automotive trim clip** generated with **CadQuery** (B-Rep) — a
drop-in replacement for the brittle plastic clips that always snap when you pull
a door card, trim panel, or under-tray. A retention barb passes through the panel
hole and springs behind it.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Push Clip** | `push_clip` | A fir-tree clip: a stack of tapered barb rings that ratchet through a round/square hole. |
| **Edge Clip** | `edge_clip` | A U-shaped clip that slides over a panel edge, with inward grip bumps on each arm. |
| **Rivet Clip** | `rivet_clip` | An expanding rivet: a hollow barbed shank bored for a spreader pin. |

The studio dispatches the active part via `target_part`; each mode renders a
distinct retention body around the shared hole interface.

## The retention interface

The barb-through-hole is sized directly from the panel hole. The shank core sits
a hair under the hole so it inserts; each **barb** is a cone that flares to
`hole_r + barb_grip` at its upper lip, so pushing in slides over it while pulling
out catches the wide lip behind the panel. A `square` hole switches the shank to
a square anti-rotation prism. The first barb sits about one `panel_t` below the
flange so the panel nips between flange and barb.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Panel Hole | `hole_dia` | 8.0 mm | Diameter of the panel hole. |
| Panel Hole | `hole_shape` | `round` | `round` (cylindrical) or `square` (anti-rotation) shank. |
| Panel Hole | `panel_t` | 2.5 mm | Panel thickness the clip grips behind. |
| Retention | `barb_count` | 3 | Fir-tree barb rings (Push mode). |
| Retention | `barb_grip` | 1.6 mm | Barb overhang past the hole, per side. |
| Head & Shank | `head_dia` / `head_thick` | 16 / 2 mm | Retainer flange size. |
| Head & Shank | `shank_len` | 14.0 mm | Shank length below the flange. |
| Head & Shank | `wall` | 2.0 mm | Generic wall / arm thickness. |
| Edge Clip | `edge_gap` / `edge_reach` | 2.5 / 16 mm | Edge slot gap (= panel thickness) and grip reach. |

## Presets

- **Door Card 8 mm** — a 3-barb fir-tree push clip for a 2.5 mm door card.
- **Trim Edge Flange** — a U-clip over a 2 mm flange.
- **Under-Tray Rivet 10 mm** — an expanding rivet for a 3 mm under-tray.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Panel Barb Clip** (`snap`, internal) — the retention barb geometry sized
    to `hole_dia`, `hole_shape`, `panel_t`, `barb_count`, `barb_grip`. Any panel
    with a matching hole accepts a clip from this family.
  - **Panel Edge Grip** (`snap`, internal) — the U-channel edge grip, defined by
    `edge_gap`, `edge_reach`, `wall`.
- **Material awareness:** barb overhang and shank clearance tune the snap force
  per material/printer (a stiffer filament needs less overhang);
  `tolerance_by_material` is declared.
- **Societal benefit:** the plastic clip is the single most-broken car part
  during any interior repair; a printable clip family sized to the hole and panel
  thickness makes each one a cents-of-filament reprint in the exact retention
  profile the panel needs.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Barbs are lofted frusta unioned onto the shank (with a cylinder fallback), and
  the rivet bore fully traverses the shell, so every shipped preset renders
  **watertight**.
