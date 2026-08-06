# Reed / Mouthpiece Cap

Reed cases and mouthpiece caps for woodwinds, generated with **CadQuery**
(B-Rep). The functional interface is the mouthpiece **socket** — the cup that
slides over the mouthpiece tip (reed and ligature on) to protect the fragile
reed.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Mouthpiece Cap** | `cap` | A cup that slides over the mouthpiece tip; a rim notch clears the ligature screws and a vent hole lets the reed dry. |
| **Reed Case** | `reed_case` | A flat case with parallel reed slots that hold spare reeds flat so they don't chip or warp, plus finger holes to lift them out. |
| **Ligature Band** | `lig_band` | A split ring that wraps the mouthpiece and presses the reed to the table, with two screw bosses to tighten. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Mouthpiece | `mp_type` | `clarinet` | Clarinet (~30 mm), alto (~33 mm) or tenor (~36 mm). |
| Cap | `cap_clear` | 1.2 mm | Per-side gap over the mouthpiece so the cap slides on. |
| Cap | `cap_len` | 55.0 mm | How far the cap covers down the mouthpiece. |
| Cap | `wall` | 2.4 mm | Cap / case / band wall thickness. |
| Reed | `reed_ct` | 4 | Reeds the case holds. |
| Reed | `reed_len` | 70.0 mm | Reed slot length. |

## The mouthpiece socket (real sizes)

Woodwind mouthpieces cluster into a few real diameters at the cap seat — a Bb
**clarinet** mouthpiece is ~30 mm across the beak end (bore ~14.6 mm), an **alto
sax** mouthpiece ~33 mm, a **tenor** ~36 mm. The cap's internal diameter is the
mouthpiece OD plus `cap_clear` per side (to clear the reed and ligature), so the
cap slides on without touching the reed tip. Reeds are ~13 mm wide (clarinet) to
~14.5 mm (tenor); the reed case slots are sized to hold them flat.

## Presets

- **Clarinet Mouthpiece Cap** — the protective cap for a Bb clarinet.
- **4-Reed Case** — a flat case for four spare reeds.
- **Alto Sax Ligature** — a split ligature band for an alto mouthpiece.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interface:** **Mouthpiece Socket** (`socket`, *clarinet / alto / tenor
  mouthpiece ~30-36 mm*) — the cap cup, defined by `mp_type`, `cap_clear`,
  `cap_len`.
- **Material awareness:** `tolerance_by_material` is declared — `cap_clear` is
  exposed so the cap slip fit tunes per material/printer.
- **Societal benefit:** a chipped reed tip is unplayable; mouthpieces cluster into
  a few real sizes, so a printed cap protects the reed, a case keeps spares flat,
  and a ligature holds the reed — from parts a student makes, not a bought set.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The cap is a **cup** with a blind bore from the open mouth (vented); the
  ligature notch is a **through box** at the rim (a flat obround grazing the
  curved wall leaves tangent slivers, so a box is used); reed slots are **obround
  pockets** from the open top with finger holes clear of the slot span; the
  ligature band is a **split ring** (open gap). All modes render **watertight**,
  single-body.
