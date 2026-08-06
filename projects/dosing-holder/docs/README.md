# Drip / Dosing Line Holder

Tidies the thin silicone and vinyl lines from a reef dosing pump, RODI top-off
or CO2/drip system, generated with **CadQuery** (B-Rep): a snap C-clip that
grips a single tube, a rim clip that hangs a line over the tank edge, and a
multi-line routing rail. Sized for 3/16"–1/4" (4.76–6.35 mm) aquarium tubing.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print in **aquarium-safe filament** (uncoloured PETG is a common choice).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Line Clip** | `line_clip` | A snap C-clip around a single dosing/airline tube, with a peg to press into a hole or foam. |
| **Rim Clip** | `rim_clip` | A hook over the tank rim with a tube C-cradle, so a line drops into the tank from the edge. |
| **Routing Rail** | `multi_clip` | A flat rail carrying several tube C-clips in a row to route multiple lines together. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tube & Clip | `tube_od` | 6.35 mm | Tube outer diameter (airline & 1/4" RODI = 6.35; rigid 3/16" = 4.76; 3/8" = 9.53). |
| Tube & Clip | `wall` | 2.2 mm | Wall of the clip C-section. |
| Tube & Clip | `clip_w` | 8.0 mm | Clip width along the tube. |
| Tube & Clip | `mouth` | 0.78 | Mouth opening as a fraction of tube OD (smaller grips harder). |
| Tube & Clip | `clearance` | 0.3 mm | Per-side gap on the tube bore and rim slot. |
| Rim Hook | `rim_th` | 8.0 mm | Rim / glass edge thickness the hook straddles (5–12 mm typical). |
| Rim Hook | `hook_drop` | 18.0 mm | How far the hook reaches down the inside. |
| Routing Rail | `n_clips` | 3 | Clips on the routing rail. |
| Routing Rail | `clip_pitch` | 14.0 mm | Center-to-center clip spacing. |

## Presets

- **Airline / RODI Clip (6.35 mm)**.
- **Dosing-Line Rim Clip** — 4.76 mm line over the rim.
- **4-Line Routing Rail**.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Tube Snap Clip** (`snap`, "3/16-1/4in tube") — the C-section that snaps
    around the tube, defined by `tube_od`, `wall`, `mouth`, `clearance`. One clip
    fits both airline and 1/4" RODI (both 6.35 mm OD).
- **Material awareness:** `tolerance_by_material` is declared — a slightly
  flexible material snaps over the tube and retains it with a tighter mouth.
- **Societal benefit:** routes dosing/RODI/drip lines cleanly, prevents
  siphon-break accidents and salt creep, printed for pennies instead of bought
  as a proprietary accessory.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Watertight strategy: every clip is a full ring minus a mouth slot narrower than
  the bore — one manifold C-section, never a tangent kiss. The rim hook is an
  extruded closed J-profile; pegs and rails are solid and overlap into the clip
  body.
- All shipped presets and defaults render **watertight**, single-body.
