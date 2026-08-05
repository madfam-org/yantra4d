# Snap-Fit Cantilever Kit

Reusable **snap-fit connectors** generated with **CadQuery** (B-Rep). A cantilever
beam whose hooked end deflects to snap over a mating ledge — and the catch that
receives it — so both halves actually clip together. Includes an annular (ring)
snap for round bores, a ball-detent bump variant, and a small test clip.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Parts

| Part | Description |
| :--- | :--- |
| **Cantilever Pair** (`cantilever_pair`) | A cantilever hook on a base **and** the catch block with a window/ledge the hook grabs — the two laid side by side. |
| **Annular Snap** (`annular_snap`) | A shaft with a raised annular bead near the tip **and** a bore piece with a matching internal groove the bead seats into. |
| **Test Clip** (`test_clip`) | A compact single-hook demonstrator for tuning deflection and fit before committing to a design. |

The studio dispatches the active part via `target_part`.

## Snap types (`snap_type`)

| Type | Feature |
| :--- | :--- |
| `cantilever` | Classic hooked beam: an angled lead-in ramp plus an undercut catch face. |
| `annular` | A ring bead that snaps past a bore lip and seats in an internal groove (used by the Annular Snap part). |
| `ball_detent` | A rounded bump on a straight beam — a gentle, repeatable detent. |

## How the halves mate

- **Cantilever:** the catch window is `beam_width + 2·clearance` wide and
  `beam_thick + clearance` tall, so the beam passes through with a printable gap;
  the hook's `hook_depth` undercut then latches behind the ledge above the window.
- **Annular:** the shaft is turned to `bore_dia/2 − clearance` (a slip fit); the
  bead projects `hook_depth` past the bore lip (the snap interference) and seats
  into a groove cut `hook_depth + clearance` deep at the matching axial position.

> **Material note:** the geometry fixes stiffness (`beam_len`, `beam_thick`) and
> engagement (`hook_depth`); the actual **deflection force depends on material**.
> Stiffer filaments (PETG, ABS) hold harder but tolerate less strain than PLA.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Beam | `beam_len` | 20.0 mm | Free cantilever length (longer = softer). |
| Beam | `beam_thick` | 3.0 mm | Root thickness (thicker = stiffer). |
| Beam | `beam_width` | 8.0 mm | Beam width. |
| Engagement | `snap_type` | `cantilever` | Cantilever / annular / ball-detent. |
| Engagement | `hook_depth` | 1.8 mm | Undercut / bead engagement depth. |
| Engagement | `insert_angle` | 35° | Lead-in ramp angle (lower = easier push-in). |
| Engagement | `clearance` | 0.3 mm | Printed gap hook↔ledge / shaft↔bore. |
| Engagement | `wall` | 3.0 mm | Base pad, catch wall, and bore wall thickness. |
| Annular Snap | `bore_dia` | 16.0 mm | Nominal shaft/bore diameter. |

## Presets

- **Enclosure Latch** — a 22 mm hooked latch for snapping enclosure lids shut.
- **Shaft Ring Snap 16 mm** — a 16 mm annular ring snap and its grooved bore.
- **Ball-Detent Test Clip** — a gentle bump detent for tuning repeatable fit.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Cantilever Snap Hook** (`snap`, internal) — the hook/ledge mating geometry,
    defined by `beam_thick`, `hook_depth`, `beam_len`, `beam_width`, `insert_angle`,
    `clearance`. Any catch cut at the same width/height + clearance accepts the hook.
  - **Annular Ring Snap** (`snap`, internal) — `bore_dia`, `hook_depth`, `clearance`,
    `wall`. The ring and groove are cut from the same nominal bore so they mate.
- **Material awareness:** the fit clearance is exposed (`clearance`) so the snap
  gap tunes per material/printer; `tolerance_by_material` is declared. Snap force
  itself is material-dependent and left to the maker.
- **Societal benefit:** snap-fits replace screws and glue with tool-free,
  reversible joints — the backbone of repairable, disassemblable design.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The hook is built as a 2D undercut profile extruded across the beam width, and
  every feature **overlaps** its base (no coplanar-touching faces); all shipped
  presets, parts, and extremes render **watertight**.
