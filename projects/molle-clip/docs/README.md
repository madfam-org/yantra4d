# MOLLE / Webbing Clip

Attachment hardware for the **MOLLE / PALS** webbing grid, generated with
**CadQuery** (B-Rep). PALS is the open military webbing standard
(**MIL-W-17337 / A-A-55301**): horizontal rows of **1 in (25.4 mm)** webbing,
spaced **1 in (25.4 mm)** row-to-row, bartacked to the backing at **1.5 in
(38.1 mm)** column intervals. One PALS-pitch interface builds a serpentine MOLLE
clip that weaves the grid, a rigid printable PALS field to attach onto, and a
MALICE-style single-column clip.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **MOLLE Weave Clip** | `molle_clip` | A serpentine attachment strap the width of one row that weaves front-behind-front through `weave_rows` PALS rows and snaps back with a grip tab. |
| **PALS Field Panel** | `pals_panel` | A rigid PALS field: a backing plate with solid webbing bars on a 1 in vertical pitch, bridged by bartack posts on a 1.5 in horizontal pitch — the channels between are the loops you thread through. |
| **MALICE-Style Clip** | `malice_clip` | A long stiff single-column clip that threads two rows and locks with a hooked foot, with a lanyard hole and a flex/weep slot. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| PALS Grid | `row_h` | 25.4 mm | Row height / webbing width. Standard is 1 in. |
| PALS Grid | `row_pitch` | 25.4 mm | Row-to-row vertical spacing. Standard is 1 in. |
| PALS Grid | `col_pitch` | 38.1 mm | Bartack column spacing (`pals_panel`). Standard is 1.5 in. |
| Clip | `strap_t` | 2.4 mm | Clip / strap / bar material thickness. |
| Clip | `clearance` | 0.4 mm | Clearance for threading through webbing rows. |
| Clip | `weave_rows` | 2 | PALS rows the weave clip spans (`molle_clip`). |
| Panel | `panel_rows` / `panel_cols` | 3 / 3 | PALS field size (`pals_panel`). |

## The PALS grid (why the pitches matter)

MOLLE gear cross-attaches because every maker follows the same PALS geometry:
1-inch webbing rows spaced 1 inch apart, stitched down every 1.5 inches. The
`molle_clip` weave and the `pals_panel` bar/post pitches are driven by
`row_pitch` (1 in) and `col_pitch` (1.5 in), so a clip printed at spec threads
genuine MOLLE webbing and a printed field accepts genuine MOLLE clips. The
`clearance` opens the weave fold just enough to pass over the webbing thickness.

## Presets

- **2-Row Weave Clip** — the everyday MOLLE clip spanning two rows.
- **3x3 PALS Field** — a rigid field to add MOLLE to a flat surface.
- **2-Row MALICE Clip** — a stiff single-column clip for heavy pouches.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **PALS / MOLLE Grid** (`snap`, *MIL-W-17337 / A-A-55301 (1in rows, 1.5in
    columns)*) — the attachment grid, defined by `row_h`, `row_pitch`,
    `col_pitch`. Any clip and field built to the same pitch interoperate with the
    MOLLE ecosystem.
  - **Weave Strap Profile** (`profile`, *25mm webbing*) — the clip's serpentine
    strap, defined by `row_h`, `strap_t`, `weave_rows`.
- **Material awareness:** `tolerance_by_material` is declared — `clearance` and
  the thickness are exposed so the weave/thread fit tunes per material and printer.
- **Societal benefit:** MOLLE / PALS is the open interoperable attachment grid
  every pack and pouch maker shares, but one lost clip strands a pouch. Printable
  clips and a rigid PALS field sized to the 1 in / 1.5 in standard let anyone
  attach, repair or extend a load-out from printed parts, and add MOLLE to gear
  that never had it.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The weave is **manifold by construction**: the clip is a single serpentine
  profile extruded across the row width (never a self-intersecting textile
  weave); the PALS field is solid bars + solid bartack posts **unioned** to a
  solid backing, so the loops are simply the empty space between them and no
  sealed cavity forms. Snap tabs and the hooked foot are solid unions; grip,
  lanyard and mounting holes and the weep slot are through-cuts (vented). Fillets
  are applied to clean blanks before feature cuts and wrapped in try/except. All
  shipped modes and presets — and the parameter extremes — render **watertight**
  (`body_count == 1`) in well under 20 s.
