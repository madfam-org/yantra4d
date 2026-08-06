# Battery Pad

An **anti-slip LiPo tray / pad** for FPV & RC craft, generated with **CadQuery**
(B-Rep). Anti-slip ribs hold the pack against vibration, and recessed **strap
channels** let the battery strap seat flush so it cannot creep. Sized to the pack
footprint.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Flat Pad** | `flat_pad` | A grippy base pad with anti-slip ribs and strap channels notched across them. |
| **Walled Tray** | `tray` | A base pad with a raised perimeter wall that captures the pack, with strap notches through the walls. |
| **CG Wedge** | `wedge` | A ramp that tilts the pack tail-up to shift the centre of gravity, with strap channels on the ramp. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pack | `pack_w` / `pack_l` | 35 / 70 mm | Battery pack footprint. |
| Pack | `strap_w` | 20 mm | Strap width the channel accepts. |
| Pack | `margin` | 4.0 mm | Pad overhang beyond the pack. |
| Grip | `pad_thick` | 3.0 mm | Base pad thickness. |
| Grip | `grip_depth` / `grip_pitch` | 1.2 / 4.0 mm | Anti-slip rib height and spacing. |
| Tray | `wall` / `wall_h` | 2.5 / 10 mm | Perimeter wall thickness and height (tray mode). |
| Wedge | `wedge_rise` | 12 mm | Rear rise that tilts the pack (wedge mode). |

## Interfaces

The **battery strap channel** is a recessed cross-slot sized to `strap_w`,
positioned at ~¼ and ~¾ of the pack length (one central channel for short packs)
so the strap lies flush and locks the pack against sliding. The **pack
footprint** (tray pocket) is derived from `pack_w`/`pack_l`, so a tray generated
for a 35×70 pack captures a 35×70 pack.

## Presets

- **4S Pad (35×70)** — flat grippy pad for a common 4S pack.
- **6S Tray (45×105)** — walled tray for a larger 6S pack.
- **CG Wedge (35×70)** — tail-up wedge to move the balance point.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Battery Strap Channel** (`profile`, *internal*) — the recessed strap slot
    cross-section, defined by `strap_w` and `pack_l`.
  - **Pack Footprint** (`pocket`, *internal*) — the captured pack area, defined
    by `pack_w`, `pack_l`, `wall`.
- **Material awareness:** `tolerance_by_material` is declared — pad thickness and
  rib depth are exposed so grip and flex can be tuned per material (a soft TPU
  pad grips hardest).
- **Societal benefit:** a LiPo that shifts in flight ruins handling and can eject
  in a crash; on-demand pads and trays sized to the exact pack hold the battery
  put, and the CG wedge lets a builder tune balance without buying tune parts.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Fillets are clamped and guarded. All modes render
  **watertight** in well under 20 s.
