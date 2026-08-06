# T-Slot 2020 Accessory Kit

The "industrial LEGO" accessory ecosystem, generated with **CadQuery** (B-Rep).
On-demand **T-nuts, corner brackets, and cable/panel clips** that lock into
standard aluminium **T-slot extrusion** (2020 / 3030 / 4040 series). Every part
is sized from one shared denominator — the extrusion's slot profile — so a
missing T-nut or a broken bracket never stalls a build.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **T-Nut** | `t_nut` | The highest-value part. A block sized to the inner channel with a neck through the slot opening and a bossed screw hole. Short = drop-in and quarter-turn; long = slide in from the extrusion end. |
| **Corner Bracket** | `corner_bracket` | An L / angle bracket that bolts two extrusions at 90°, with a slotted hole per leg (slide adjustment) and an optional stiffening gusset. |
| **Cable Clip** | `cable_clip` | A twist-in clip: the foot enters the slot then locks a quarter-turn; a bored C-loop routes a wire or pneumatic line and snaps shut from the top. |
| **Panel Clip** | `panel_clip` | Retains a panel edge (acrylic / plywood) of thickness `panel_t` into the slot — a slot foot plus a grooved jaw. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Extrusion Profile | `slot_series` | `2020` | Extrusion family: `2020` / `3030` / `4040`. Sets slot opening, inner-channel width, and channel depth. |
| Extrusion Profile | `slot_fit_clearance` | 0.3 mm | Per-side printed-fit gap; tune per printer/material. |
| Fastener | `screw_size` | `M4` | Screw clearance-hole size: M3 (3.4) / M4 (4.5) / M5 (5.5 mm). |
| T-Nut | `nut_length` | 12 mm | Length along the slot axis. |
| T-Nut | `tapped` | off | Smaller bore for a self-tapping screw or brass heat-set insert. |
| Corner Bracket | `bracket_leg` | 30 mm | Length of each arm. |
| Corner Bracket | `bracket_thick` | 5.0 mm | Leg wall thickness. |
| Corner Bracket | `bracket_gusset` | on | Triangular corner stiffener. |
| Cable Clip | `cable_dia` | 6.0 mm | Routed wire / pneumatic line diameter. |
| Panel Clip | `panel_t` | 3.0 mm | Retained panel edge thickness. |

## Modeled Slot Geometry

The three load-bearing dimensions per series (the Common Denominator Geometry):

| Series | Profile | Slot Opening | Inner Channel | Channel Depth |
| :--- | :--- | :--- | :--- | :--- |
| **2020** | 20 mm | ~6.0 mm | ~11.0 mm | ~6.0 mm |
| **3030** | 30 mm | ~8.0 mm | ~16.5 mm | ~7.5 mm |
| **4040** | 40 mm | ~8.0 mm | ~20.0 mm | ~9.0 mm |

The T-nut body fills the **inner channel** (hooking under the retaining lips),
its **neck** passes through the **slot opening**, and `slot_fit_clearance` is
subtracted per side so the printed part actually slides in. Values track Bosch
Rexroth / OpenBuilds / Misumi HFS nominal profiles.

## Presets

- **M5 T-Nut for 2020** — the everyday drop-in nut.
- **Long Slide-In T-Nut (4040)** — 30 mm body for high-grip end loading.
- **2020 Corner Bracket** — gusseted 30 mm angle bracket.
- **6 mm Cable Clip (2020)** — routes a typical wire bundle.
- **3 mm Acrylic Panel Clip (2020)** — retains an acrylic enclosure panel.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **T-Slot Extrusion Profile** (`profile`) — standard *T-slot 20/30/40 series
    (e.g. Bosch Rexroth / OpenBuilds / Misumi HFS)*. Defined by `slot_series`,
    `slot_fit_clearance`, `screw_size`. This is the denominator every accessory
    in the kit shares; anything printed against the same series + clearance locks
    into the same extrusion. Cross-commons compatible with the
    `extrusion-hyperobject` and `framing-hyperobject` projects that model the
    extrusion stock itself.
- **Material awareness:** `slot_fit_clearance` is exposed so the fit can be tuned
  per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** frees maker-space and industrial framing from proprietary
  hardware — a broken bracket or missing T-nut is reprinted on demand against one
  global denominator.
- **License:** CERN-OHL-W-2.0

## Print Tips

- Print T-nuts and clips **flat on the build plate**; the slot foot's chamfered
  underside is the natural first layer and eases insertion.
- Print corner brackets with the legs meeting at a bottom corner so both bolt
  faces have layers in shear, not peel.
- Start with `slot_fit_clearance = 0.3 mm` on a calibrated printer; increase
  toward 0.5 mm for looser tolerances, or set 0.0 for a tight interference fit.
- **PETG or ABS/ASA** for load-bearing brackets; **PLA** is fine for cable/panel
  clips and fit checks.

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. Part selection is dispatched through `target_part`. The
  final solid is assigned to `result`.
- All shipped presets and defaults render **watertight** across every series.
