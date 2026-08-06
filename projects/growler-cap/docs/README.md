# Growler Cap / Handle

A replacement sealing cap for standard **32 oz / 64 oz screw-top growlers**, which
almost universally use the **38 mm "38-400"** continuous-thread finish. Generated
with **CadQuery** (B-Rep). The functional interface is a **real 38-400 female
helical thread** (38 mm major diameter, coarse ~4.2 mm pitch).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Sealing Cap** | `sealing_cap` | A plain 38-400 female-threaded cap with a sealed top and grip knurl — a drop-in replacement for a lost or perished growler cap. |
| **Handle Cap** | `handle_cap` | The same cap with an integral D-handle loop across the top, so a heavy full growler is easy to carry. |
| **Carbonation Cap** | `carbonation_cap` | A cap with a raised central boss bored for a gas-line grommet, for home carbonation / low-pressure serving. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Thread & Fit | `clearance` | 0.5 mm | Per-side printed-thread slop (coarse threads print looser). |
| Thread & Fit | `turns` | 1.5 | 38-400 turns (snapped to a half-integer internally). |
| Cap Body | `wall` | 3.0 mm | Radial wall around the thread. |
| Cap Body | `top_th` | 3.0 mm | Sealed-top thickness. |
| Cap Body | `grip_knurl` | on | Vertical grip flutes. |
| Handle | `handle_w` | 12 mm | Carry-handle strap width. |
| Handle | `handle_h` | 34 mm | Handle loop height. |
| Handle | `handle_t` | 8 mm | Handle strap thickness. |
| Carbonation Port | `port_dia` | 9.5 mm | Gas-line grommet bore (suits 3/8" line). |
| Carbonation Port | `boss_dia` | 20 mm | Raised central boss diameter. |
| Carbonation Port | `boss_h` | 8 mm | Boss height above the cap. |

## Presets

- **Standard 38 mm Sealing Cap** — the everyday replacement cap.
- **Carry-Handle Cap** — cap + D-handle loop.
- **Carbonation / Serving Cap** — cap + gas-port boss.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **38-400 Growler Thread** (`thread`, 38-400 continuous-thread finish) — the
    female growler-neck thread, defined by `clearance`, `turns`, `wall`. This starts
    a new growler-thread family cluster (no existing Commons member shares it yet).
- **Material awareness:** `clearance` is exposed so the printed thread fit can be
  tuned per material and shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** growler caps are routinely lost or their liners perish,
  retiring an otherwise-good glass or steel growler; an on-demand 38-400 cap keeps
  the vessel in service, the handle variant carries a heavy full growler, and the
  carbonation variant lets homebrewers carbonate and serve without proprietary
  hardware.
- **License:** CERN-OHL-W-2.0

## Food / beverage contact & material responsibility

This cap seals a vessel for beer, kombucha, and other beverages. FDM prints are
**not inherently food-safe**: layer lines harbor bacteria and many filaments and
colorants are not food-contact rated. Sealing pressurized or carbonated beverages
with a printed cap is **your responsibility** — choose a certified food-contact
filament, verify the seal, do not exceed safe pressures, and treat printed
beverage-contact parts as short-lived. The carbonation port is a mounting boss for a
grommet + line, not a rated pressure fitting.

## Thread modeling notes (watertight + fast)

- Threads are **volumetric fused helical ribs** swept along a genuine `makeHelix`
  path and unioned into the bore wall.
- The turn count is forced to a **half-integer** (`floor(n)+0.5`); a whole-integer
  count degenerates the OCCT helical sweep into a null body.
- **The socket has a closed base.** An open-ended threaded socket terminates the
  helical rib at a free rim and tessellates non-watertight; the gas port is cut
  through the closed top afterward.

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. No cross-file imports.
