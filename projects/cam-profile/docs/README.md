# Cam / Eccentric

A rotating **cam** generated with **CadQuery** (B-Rep) that converts rotation into
linear follower motion — the heart of timers, automatons, indexers, engines, and
clamping fixtures. The profile is a polar radius function **r(θ)** sampled into a
closed polyline and extruded, so the follower's displacement curve *is* the printed
cam edge.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Motion law |
| :--- | :--- | :--- |
| **Eccentric** | `eccentric` | A circle whose center is offset from the bore — the simplest cam, a smooth once-per-rev rise. |
| **Snail Cam** | `snail_cam` | Archimedean spiral: radius rises linearly over ~85 % of the turn, then a sharp return. |
| **Harmonic Cam** | `harmonic_cam` | Smooth rise–dwell–fall via (1−cos) segments and an adjustable low dwell. |

The mode selects the law; the `cam_type` select mirrors it for direct control.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cam Profile | `cam_type` | eccentric | eccentric / snail / harmonic. |
| Cam Profile | `base_radius` | 15 mm | Low/dwell radius. |
| Cam Profile | `lift` | 10 mm | Peak rise above base (clamped to 2.5·base). |
| Cam Profile | `dwell_angle` | 90° | Low-dwell span before the rise (harmonic only). |
| Body | `thickness` | 8.0 mm | Cam thickness (Z). |
| Body | `bore` | 6.0 mm | Shaft bore, with a set-screw flat. |
| Body | `hub` | on | Raised hub around the bore. |

## Presets

- **Timer Eccentric** — a smooth timer/knob cam.
- **Escapement Snail** — a snail cam for an escapement or indexer.
- **Valve Harmonic** — a low-shock rise-dwell-fall valve lifter.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Cam Rise Profile** (`spline`, internal) — the working surface, defined by
    `base_radius`, `lift`, `cam_type`, `dwell_angle`. A follower tuned to that base
    + lift tracks the cam; changing `cam_type` swaps the timing law without changing
    the interface envelope.
- **Material awareness:** printed clearances are declared via
  `tolerance_by_material` so the follower contact can be tuned per material.
- **Societal benefit:** custom motion profiles are locked inside proprietary
  machinery and impossible to source as spares — a parametric cam reproduces an
  exact rise law on demand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The profile is 240 polar samples closed into one wire and extruded — fast and
  watertight. **All shipped presets, all three cam types, and both extremes render
  watertight.**
