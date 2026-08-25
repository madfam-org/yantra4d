# Bottle-to-Bottle Coupler

Joins two **PCO-1881** bottles neck-to-neck. Generated with **CadQuery** (B-Rep).
Every end is a **real single-start helical thread** (27.43 mm thread major diameter,
2.7 mm pitch) that mates with the same PCO-1881 neck used by the `bottle-thread`,
`bird-feeder`, `faircap-filter`, and `pet-dispenser` cartridges.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Straight Coupler** | `straight_coupler` | Female PCO thread on both ends with an open through-channel — invert-and-store two bottles, or transfer between them. |
| **Tornado Tube** | `tornado_coupler` | Both ends threaded, but a solid central web keeps only a small orifice, so draining water spins into a visible vortex — the classic "tornado tube" science demo. |
| **Funnel Coupler** | `funnel_coupler` | Female PCO thread on one end opening into a wide catch funnel for pouring / decanting into the bottle. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Thread & Fit | `clearance` | 0.4 mm | Per-side printed-thread slop on each end. |
| Thread & Fit | `turns` | 3.5 | PCO-1881 turns per end (snapped to a half-integer internally). |
| Coupler Body | `wall` | 2.8 mm | Radial wall around each thread. |
| Coupler Body | `web_th` | 3.0 mm | Central web thickness (straight / tornado). |
| Coupler Body | `bore_margin` | 1.6 mm | Wall left around the through-channel / throat. |
| Tornado Orifice | `vortex_dia` | 8 mm | Central vortex orifice diameter. |
| Funnel | `funnel_dia` | 90 mm | Funnel mouth diameter. |
| Funnel | `funnel_h` | 55 mm | Funnel cone height. |
| Funnel | `funnel_wall` | 1.8 mm | Funnel cone wall. |

## Presets

- **Two-Bottle Storage Joiner** — invert-and-store.
- **Classic Tornado Tube** — the water-vortex demonstrator.
- **Decant Funnel** — thread onto one bottle, pour through the funnel.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **PCO-1881 Neck Thread (×2)** (`thread`, PCO 1881) — the female bottle-neck
    threads, defined by `clearance`, `turns`, `wall`. **Compatible with**
    `bottle-thread`, `bird-feeder`, `faircap-filter`, and `pet-dispenser`.
- **Material awareness:** `clearance` is exposed so the printed thread fit can be
  tuned per material and shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** turns two abundant PET bottles into a bigger closed system
  with no new vessel — store, run a free vortex science demo, or decant — all from
  bottles that would otherwise be waste.
- **License:** CERN-OHL-W-2.0

## Food contact & material responsibility

The straight and funnel couplers can carry drinking water and beverages. FDM prints
are **not inherently food-safe**: layer lines harbor bacteria and many filaments and
colorants are not food-contact rated. Using this part with anything you will drink is
**your responsibility** — choose a certified food-contact filament, print with a
clean nozzle, and treat printed liquid-handling parts as short-lived.

## Thread modeling notes (watertight + fast)

- Threads are **volumetric fused helical ribs** swept along a genuine `makeHelix`
  path and unioned into the bore wall.
- The turn count is forced to a **half-integer** (`floor(n)+0.5`); a whole-integer
  count degenerates the OCCT helical sweep into a null body.
- **Each socket has a closed base.** An open-ended threaded socket terminates the
  helical rib at a free rim and tessellates non-watertight; the two sockets are
  stacked base-to-base (their bases forming the central web) and the flow channel /
  vortex orifice is cut through afterward. Modeled turns are capped so the sweep
  stays watertight at every setting.

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. No cross-file imports.
