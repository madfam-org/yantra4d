# Rail Standard Bridge

A **capstone multi-standard adapter** that bridges the three accessory-rail
families that would otherwise never interoperate: the **MIL-STD-1913
(Picatinny)** rail, the **NATO accessory dovetail**, and the **Arca-Swiss 38 mm**
tripod dovetail. Generated with **CadQuery** (B-Rep). Each mode is a single block
that carries one standard's male profile on its **top** face and a different
standard's male profile on its **bottom** face — so a clamp or head built for one
family can carry a device built for another.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Picatinny ↔ NATO** | `pic_to_nato` | MIL-STD-1913 rail on top, NATO dovetail underneath — drop a NATO accessory onto a Picatinny rail (or vice versa). |
| **Picatinny ↔ Arca-Swiss** | `pic_to_arca` | Picatinny rail on top, Arca-Swiss 38 mm dovetail underneath — clamp a Picatinny accessory into an Arca tripod head. |
| **NATO ↔ Arca-Swiss** | `nato_to_arca` | NATO dovetail on top, Arca-Swiss dovetail underneath — carry a NATO device on an Arca head. |

## Real cross-section geometry

| Standard | Nominal dimensions (mm) |
| :--- | :--- |
| Picatinny (MIL-STD-1913) | overall width 21.20, flat top 15.70, height 4.45, flange band 3.15, groove pitch 10.0, groove width 5.35 |
| NATO accessory rail | platform 21.2, ~44° flanks, height 6.0 |
| Arca-Swiss | platform 38.0, ~45° flanks, block height 9.0 |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Rail Detail | `slots` | 4 | Picatinny recoil grooves (10 mm pitch); sets the bridge length. |
| Bridge Body | `dovetail_len` | 50 mm | Run length of the NATO↔Arca dovetail bridge. |
| Bridge Body | `core_th` | 6 mm | Slab thickness between the top and bottom profiles. |
| Bridge Body | `relief_d` | 6.6 mm | Central pass-through bore (1/4-20 clearance), vents both ends. |
| Rail Detail | `grip_notch` | on | Transverse recoil-stop notch across the dovetail platform. |

## Presets

- **Picatinny to NATO (4 slot)** — the everyday tactical cross-adapter.
- **Picatinny to Arca-Swiss** — mount a rail accessory to a tripod head.
- **NATO to Arca-Swiss** — carry a NATO device on an Arca plate.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces (this object bridges THREE families):**
  - **Picatinny MIL-STD-1913 Rail** (`rail`, MIL-STD-1913 Picatinny) — the male
    rail cross-section; **compatible with** `picatinny-rail`.
  - **NATO Accessory Dovetail** (`rail`, NATO accessory rail) — the male NATO
    dovetail; **compatible with** `nato-rail`.
  - **Arca-Swiss 38 mm Dovetail** (`profile`, Arca-Swiss 38mm) — the male Arca
    dovetail; **compatible with** `arca-plate`, `arca-l-bracket`,
    `arca-gopro-bridge`.
- **Material awareness:** `relief_d` and the fixed profile clearances let the fit
  be tuned per material; `tolerance_by_material` is declared.
- **Societal benefit:** Picatinny, NATO and Arca-Swiss rails each dominate a
  different world — optics/firearms, tactical accessories, and photography — and
  none of them mate. A printed double-sided bridge collapses three incompatible
  ecosystems into an interoperable one, without a proprietary cross-adapter per
  pairing.
- **License:** CERN-OHL-W-2.0

## Geometry notes (watertight + fast)

- **Thread-free by design** — every interface here is a rail/dovetail profile, so
  each render is fast and robust.
- Every profile is a **closed 2D wire extruded along the length and unioned** into
  a central slab whose faces the profiles overlap into (never a tangent kiss).
- Recoil grooves, the safety notch, and the central relief bore are cut **last**
  as through-features that vent to a face — no trapped voids.
- Fillets are applied only to the clean base slab, wrapped in `try/except`.

## Print notes

- Print with the **larger** profile down as the bed face for the flattest, most
  dimensionally accurate mating surface, or split the print if your bed is small.
- The dovetail flanks are the load-bearing surfaces — orient layers so they run
  along the flank, not across it, for the strongest grip.
