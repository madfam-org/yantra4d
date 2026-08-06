# FPV Antenna Mount

**Holds a VTX antenna clear of the propellers** and routes it up or back,
generated with **CadQuery** (B-Rep). Sized to the antenna connector standard —
the **SMA** bulkhead or the tiny **U.FL** coax — so the exit hole and coax route
match the hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Tube Mount** | `tube_mount` | Foot + leaning stalk with a top socket that captures a rigid tube / pagoda antenna. |
| **SMA Bulkhead Bracket** | `sma_bracket` | Foot + stalk capped by a bulkhead face with the SMA through-hole; an SMA nut clamps the antenna there. |
| **Frame Clip** | `clip` | A bolt-free C-clip that snaps onto a frame plate and carries a short routing stalk. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Connector | `connector` | SMA | `SMA` (6.5 mm exit) or `U.FL` (2.6 mm exit). |
| Stalk | `stalk_h` / `stalk_d` | 35 / 8 mm | Stalk height (prop clearance) and diameter. |
| Stalk | `back_angle` | 25° | Rearward lean (tube / SMA modes). |
| Base | `base_w` / `base_l` | 18 / 18 mm | Foot footprint. |
| Base | `bolt_d` / `bolt_span` | 2.2 / 12 mm | Base bolt holes (M2). |
| Tube / Clip | `tube_d` / `tube_len` | 4 / 28 mm | Tube socket size and depth (tube mode). |
| Tube / Clip | `clip_gap` | 4 mm | Frame-plate thickness the clip grips (clip mode). |

## Interfaces

The **antenna exit** hole is sized from `connector`: an SMA bulkhead barrel needs
a ~6.5 mm through-hole, U.FL just routes a ~2 mm coax. The coax runs down the
axial bore of the stalk. The stalk is built upright with its top feature (tube
socket or bulkhead cap), then the whole assembly is leaned back by `back_angle`
so the exit stays coaxial with the leaned stalk.

## Presets

- **SMA Stalk 25°** — the standard rear-leaning SMA bracket.
- **Pagoda Tube Mount** — captures a rigid pagoda/tube antenna.
- **U.FL Frame Clip** — bolt-free clip for a light micro build.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Antenna Exit** (`socket`, *SMA / U.FL*) — the connector through-hole and
    coax route, defined by `connector` and `tube_d`. Matches the two dominant
    FPV antenna connector standards.
  - **Frame Fixing** (`bolt_pattern`, *internal*) — the base bolt holes or the
    snap clip, defined by `bolt_span`, `bolt_d`, `clip_gap`.
- **Material awareness:** `tolerance_by_material` is declared — the exit-hole and
  socket sizes are exposed so push-fit tightness can be tuned per material.
- **Societal benefit:** a VTX antenna that dips into the prop wash tears itself
  apart and kills the video link; on-demand mounts sized to the exact connector
  lift and lean the antenna clear.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Fillets are clamped and guarded. All modes render
  **watertight** in well under 20 s.
