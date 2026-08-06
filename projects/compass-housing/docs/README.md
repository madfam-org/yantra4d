# Compass / Whistle Housing

Housings and EDC bodies for **button compasses** and **emergency whistles**,
generated with **CadQuery** (B-Rep). Button compass capsules are sold as sealed
liquid-filled buttons in two common diameters — **20 mm** and **25 mm** — that
need a bezel to carry them. One capsule-diameter interface sockets that button
into a clip-on bezel, a pealess emergency whistle body, or a pocket EDC storage
pod.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Compass Bezel + Clip** | `compass_housing` | A round bezel that press-fits the capsule (blind bore from the top face), with a lanyard hole and a flat spring belt-clip built from solid bars. |
| **Emergency Whistle** | `whistle_body` | A flat pealess whistle: a mouthpiece air inlet that vents across a sound window (open air passages) plus a lanyard hole. |
| **EDC Storage Pod** | `edc_capsule` | A pocket pod with the compass socket in the top and a deep storage bore opening to the bottom face (tinder, matches, pills). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Compass Capsule & Fit | `cap_d` | 25.0 mm | Button compass capsule diameter. Common sizes are 20 mm and 25 mm. |
| Compass Capsule & Fit | `cap_depth` | 9.0 mm | How deep the capsule seats into the socket. |
| Compass Capsule & Fit | `fit` | 0.3 mm | Added to the capsule diameter for a press fit. |
| Body | `wall` | 3.0 mm | Wall and floor thickness. |
| Body | `store_depth` | 26.0 mm | Depth of the storage cavity (`edc_capsule`). |
| Clip & Holes | `clip_w` | 26.0 mm | Opening the spring clip grips (belt, strap, pack edge). |
| Clip & Holes | `lanyard_d` | 5.0 mm | Through hole for a lanyard or cord. |

## Why the capsule diameter is the interface

The socket is bored `cap_d + fit`, so a single capsule-diameter value fits a
genuine 20 mm or 25 mm sealed button compass across the bezel and the EDC pod.
The capsule press-fits into a blind bore drilled from an exterior **face**, so it
opens to that face (it vents — no trapped void) while a solid floor seals the
back. The whistle shares the family's proportions but its function is acoustic:
the mouthpiece air inlet and sound window are open air passages that exit to
exterior faces, so the model stays watertight while the split airstream over the
window edge makes the tone.

## Presets

- **25 mm Compass Bezel** — the reference bezel + spring clip.
- **Pealess Whistle** — a flat emergency whistle with a lanyard loop.
- **Compass EDC Pod (20 mm)** — a pocket pod carrying the smaller capsule plus storage.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Button Compass Socket** (`socket`, *20/25mm compass*) — the capsule seat,
    defined by `cap_d`, `cap_depth`, `fit`. Any part built to the same capsule
    diameter shares button compasses across the kit.
  - **Lanyard Bore** (`socket`, *internal*) — the cord bore, defined by
    `lanyard_d`, for a lanyard or split ring.
- **Material awareness:** `tolerance_by_material` is declared — `fit` and the
  socket dimensions are exposed so the capsule fit tunes per material and printer.
- **Societal benefit:** a button compass and a whistle are the two lightest, most
  reliable navigation and signalling tools in a kit; a printable housing sized to
  the 20 mm / 25 mm capsule standard carries the compass, adds a loud pealess
  whistle, and turns a lost bezel into a five-minute reprint anywhere.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Each part is **one solid**: the capsule and storage bores are blind bores from
  exterior faces (open to a face → vented); the spring clip is a solid spine +
  return lip (no thin annulus, so it stays manifold); the whistle's air passages
  vent to exterior faces; lanyard holes are through-bores. Fillets are applied to
  clean blanks before feature cuts and wrapped in try/except (no fillet runs on a
  feature-laden or freshly-unioned solid). All shipped modes and presets — and
  the parameter extremes — render **watertight** (`body_count == 1`) in well
  under 20 s.
