# Jewelry Blanks

Parametric ring and bracelet blanks generated with **CadQuery** (B-Rep), sized by
standard ring size. A plain band, a signet blank with a flat top face for
engraving or setting, and an open bangle bracelet.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Ring sizing

Ring inner diameter is derived from **US ring size** via the standard conversion:

```
inner_dia (mm) = 11.63 + 0.8128 × size
```

so US 7 → 17.32 mm, US 10 → 19.76 mm, matching published ring-size charts. The
`ring_size` slider runs US 3-14 in quarter sizes.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Ring Band** | `ring_band` | A plain band with a `flat`, `domed`, or `comfort` cross-section. |
| **Signet Blank** | `signet_blank` | A band carrying a raised **flat plateau** (the signet face) for engraving or as a bezel-setting blank. |
| **Bracelet** | `bracelet` | An open bangle: a large ring with an angular gap, sized by wrist diameter. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Ring Size | `ring_size` | 7.0 | US ring size (3-14). Drives inner diameter. |
| Band | `band_w` / `band_t` | 6.0 / 2.0 mm | Band width (finger axis) / radial thickness. |
| Band | `profile` | domed | Cross-section: flat / domed / comfort. |
| Signet Face | `signet_w` / `signet_l` / `signet_h` | 12 / 14 / 2.5 mm | Flat face width / length / plateau height. |
| Bracelet | `wrist_dia` | 60 mm | Bangle interior diameter. |
| Bracelet | `gap_deg` | 70° | Opening so the bangle slips on. |

## Presets

- **US 7 Domed Band** — the everyday ring blank.
- **US 10 Signet Blank** — a flat-face signet for engraving.
- **Open Bangle (60 mm)** — a wrist bangle with a 70° opening.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Ring Band** (`profile`, US/EU ring sizing) — the finger interface, defined
    by `ring_size`, `band_w`, `band_t`, `profile`. Sizing follows the standard
    US conversion so blanks map to real finger sizes.
  - **Signet Face** (`surface`, internal) — the flat engraving/setting plateau,
    defined by `signet_w`, `signet_l`, `signet_h`.
- **Material awareness:** band thickness and profile are exposed so the fit and
  shrink can be tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** made-to-size ring and bracelet blanks for makers — a
  fitted starting point for casting patterns, resin jewelry, or direct prints at
  any finger size without a jeweler's mandrel.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard. The final solid is assigned to `result`.
- The signet plateau's inner side is trimmed to the band OD so it fuses
  volumetrically and never floats inside the finger hole.
- All shipped presets and defaults render **watertight**.
