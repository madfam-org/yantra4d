# Guy Wire Marker

High-visibility markers that make the guy wire of a utility pole visible, sized to real EHS guy strand.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

A guy wire is the least visible hazard on a pole line: a taut steel strand crossing head height at a shallow angle, often over a sidewalk or a driveway approach, with nothing to catch the eye. Pedestrians and cyclists walk into them; mower operators cut them.

The standard remedy is a moulded yellow guy guard, but it is a proprietary per-utility part that goes missing after roadworks and that a rural co-op, a farm, an amateur-radio mast owner or a private pole owner frequently cannot source at all — so the wire simply stays bare.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `shell_pin` | Clamshell Half — Pin | CadQuery B-Rep | `main.py` |
| `shell_socket` | Clamshell Half — Socket | CadQuery B-Rep | `main.py` |
| `snap_shell` | Snap-On C-Section | CadQuery B-Rep | `main.py` |
| `flag_disc` | Disc Flag Marker | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

The clamshell is **two modes, not one**: each half is its own printable piece. That follows the repo's `folding-board` convention — one printable piece per part — and it is also what keeps each result a single closed solid, since two separated halves in one body would fail the `body_count == 1` contract.

## Parameters

`strand` selects the guy strand and `clearance` sets the bore slop — open it up for a served or taped wire. `mouth` sets how far the snap section closes over the wire (lower grips harder). `wall`, `outer_dia` and `length` size the marker body; `disc_dia` and `disc_t` size the flag. `pin_dia` keys the clamshell halves together. All labels and tooltips are bilingual (en/es).

## Shares the pv-cable-clip snap convention

The snap mouth here is **not** a new invention. It uses the same convention the published `pv-cable-clip` established — mouth width expressed as a *fraction of bore diameter*, so the grip scales with the wire rather than being a fixed gap that is too tight on 1/2 in strand and too loose on 3/16 in. A commons that agrees on how snap fits are parameterised is more useful than one where every cartridge picks its own.

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| EHS guy strand 3/16 in | 4.76 mm |
| EHS guy strand 1/4 in | 6.35 mm |
| EHS guy strand 5/16 in | 7.94 mm |
| EHS guy strand 3/8 in | 9.53 mm |
| EHS guy strand 1/2 in | 12.70 mm |
| Bore radius | strand Ø/2 + `clearance` |
| Snap mouth width | `mouth` × bore Ø |

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Guy Strand Bore** (`socket`, EHS galvanised guy strand series) — compatible with `pv-cable-clip`, `conduit-clip`.
  - **Snap Mouth** (`snap`, mouth as a fraction of bore Ø) — the shared snap convention; compatible with `pv-cable-clip`.
  - **Clamshell Pin Keying** (`snap`, internal) — pin/socket keying between the two halves.
- **Material awareness:** tolerance-by-material (snap fit tuned per filament).
- **Societal benefit:** restores marking on an unguarded guy wire without a lineman, proprietary parts, or disturbing guy tension.
- **License:** CERN-OHL-W-2.0

## Printing and material notes

Print the shells standing on end (wire axis vertical) so the C-section springs across layer lines rather than splitting along them — a snap section printed flat will delaminate at the mouth the first time it is sprung on.

Use **yellow ASA**, which is what the commercial guards are made of and for good reason: it holds pigment under UV and stays tough in cold. Pigmented PETG is an acceptable second choice. PLA is not suitable outdoors here at all — it embrittles within a season and a shattered guard leaves sharp fragments on a wire at head height, which is worse than the bare wire it replaced. Retroreflective tape wrapped over the shell adds night visibility.

**Safety scope.** These are passive visual markers. They carry no load, are not electrical insulation, and are not a substitute for a guy guard where one is required by the utility's own standards or by local code. Do not install on a wire you do not own; on a utility-owned pole, marking is the utility's responsibility and its line crew's call. Fitting the snap section does not require slackening the guy, but nothing here should be attempted near energised conductors.

## Verification

All four modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode plus all five strand options — 66/66 cases, each `is_watertight == True` with `body_count == 1`.

Derived dimensions are clamped in `main.py` rather than trusted from the UI. The outer radius is forced to `max(outer_dia/2, bore_r + wall)`, so dialling a 1/2 in strand into a 16 mm marker yields a thicker marker rather than a shell with negative wall thickness that would disintegrate into fragments. Clamshell pins are seated at mid-wall — `(bore_r + out_r)/2` — so they are fully inside material at every bore/outer ratio, and each boss overlaps back into its half volumetrically rather than sitting tangent. The disc's snap mouth is cut through the hub **and** the plate in one pass, which is what keeps the flag a single connected solid.
