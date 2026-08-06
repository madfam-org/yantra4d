# Universal Threaded Adapter Kit

A parametric **any-to-any threaded adapter** — the universal *translator* for
threads — generated with **CadQuery** (B-Rep). Pick a thread standard for each
end and get a printable adapter that mates the two. **Every thread is a real
single-start helical rib** (`makeHelix` + swept trapezoid fused into the wall),
sized to nominal standard geometry.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Use note:** printed threads are for low-pressure / non-potable use unless you
> validate them; NPT is modelled as a straight thread for printability (real NPT
> is 1:16 tapered).

## Thread standards

| Key | Standard | Major Ø | Pitch |
| :--- | :--- | :---: | :---: |
| **GHT34** | Garden Hose 3/4" | 26.44 mm | 2.209 mm (11.5 TPI) |
| **NPT12** | NPT 1/2" pipe | 21.34 mm | 1.814 mm (14 TPI) |
| **BSP12** | BSPP / G 1/2" | 20.96 mm | 1.814 mm (14 TPI) |
| **M20** | ISO metric M20 | 20.0 mm | 2.5 mm |
| **M24** | ISO metric M24 | 24.0 mm | 3.0 mm |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Male → Female** | `male_to_female` | Male thread (end **A**) on the bottom + female thread (end **B**) on top: the core any-to-any translator, with a through bore. |
| **Double Male** | `double_male` | Male thread **A** + male thread **B** on a central hex body: joins two female fittings. |
| **Hose Bib Adapter** | `hose_bib` | Female thread **A** on the bottom (drops onto a spigot / hose bib) + male thread **B** on top: the garden-hose-to-pipe / tap adapter, hex grip. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Thread Ends | `thread_a` / `thread_b` | GHT34 / NPT12 | Standard for each end (male / female per mode). |
| Fit & Body | `clearance` | 0.4 mm | Per-side printed-thread gap. |
| Fit & Body | `wall` | 3 mm | Radial wall around the thread. |
| Fit & Body | `turns` | 3.0 | Engagement; snapped to a half-integer, capped at 3.5. |
| Fit & Body | `bore` | 10 mm | Through bore (fluid path). |
| Fit & Body | `hex_grip` | on | Hex wrench flats on the middle body. |

## Presets

- **GHT → NPT** — connect a garden hose to a pipe.
- **NPT ↔ BSP Joiner** — a double-male joining two female fittings.
- **Hose-Bib GHT → NPT** — female GHT onto a bib, male NPT out.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Thread End A** (`thread`, *GHT / NPT / BSP / M20 / M24*) — the end-A screw
    interface (`thread_a`, `clearance`, `turns`).
  - **Thread End B** (`thread`, *GHT / NPT / BSP / M20 / M24*) — the end-B screw
    interface (`thread_b`, `clearance`, `turns`).
  - **Fluid Bore** (`socket`, *internal*) — the through bore (`bore`).
- **Material awareness:** the printed-thread fit is exposed as `clearance`;
  `tolerance_by_material` is declared.
- **Societal benefit:** thread standards are a tower of Babel — GHT won't meet
  NPT, NPT won't meet BSP or metric; the retail answer is a wall of single-purpose
  brass adapters. A parametric any-to-any translator prints exactly the adapter
  you need, on demand, from open geometry.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained + sandbox-safe: params via `PARAM(lambda: name, default)`, final
  solid assigned to `result`.
- **Threads are real helical ribs.** A trapezoidal profile is swept along a
  genuine `makeHelix` path; the rib root is pushed into the wall (`overlap`) for a
  watertight volumetric union. Male cores are made taller than the thread run so
  both rib ends are buried in the cylinder.
- **Half-integer turn count.** Engagement is snapped to `floor(turns)+0.5`
  (clamped 1.5–3.5): an integer count degenerates the OCCT helical sweep to a
  negative-volume / null body. The 3.5-turn cap bounds the multi-thread boolean.
- The **hex grip** is applied to the *middle body only* — building the mid as a
  hex prism keeps the threaded ends round (intersecting the whole part with a hex
  would truncate them). All three modes across every standard pair, and the
  MIN/MAX extremes, render watertight with a single body.
