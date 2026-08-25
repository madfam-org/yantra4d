# Pill Organizer Insert

A configurable pill-organiser grid: a compartment tray (weekly 7×1, daily 4-column, or any rows×columns), a friction lid, and a single removable dose cup. A new daily-living family/cluster.

> A medication **organising** aid, not a certified dosing device. It does not dispense or track doses — follow your pharmacist's and physician's guidance.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `tray` | Compartment Tray | A rows×columns grid of open-top pill compartments. |
| `lid` | Friction Lid | A capping shell that slips over the tray rim and holds by friction. |
| `single_cup` | Dose Cup | A single removable compartment cup with a finger tab to carry one dose. |

## Standards & dimensions

- **Weekly organiser:** a 7 × 1 grid of ~20 mm compartments.
- **Daily organiser:** 4 columns (morning / noon / evening / night).
- **Interface (internal):** the compartment pitch (`cell + wall`) is the grid the lid and dose cup mate to.

## Parameters

- `cols` (1–14) — compartments across (7 for weekly).
- `rows` (1–6) — compartments deep (e.g. 4 for morning/noon/eve/night).
- `cell` (12–40 mm) — square inner size of each compartment.
- `depth` (8–40 mm) — pocket depth.
- `wall` (1.2–5 mm) — divider and outer wall thickness.
- `clearance` (0.1–1.0 mm/side) — lid-over-tray and cup-in-cell fit.

## Printing notes / Notas de impresión

**EN:** Print open-top (no supports). Bigger cells + fewer columns suit arthritic hands; more columns suit complex regimens. Print in food-safe-handled PLA / PETG and wash before use. Tune `clearance` so the lid holds but lifts off easily.

**ES:** Imprime con la parte superior abierta (sin soportes). Celdas más grandes + menos columnas convienen a manos con artritis; más columnas para regímenes complejos. Imprime en PLA / PETG de manejo apto para alimentos y lava antes de usar. Ajusta `clearance` para que la tapa sujete pero salga con facilidad.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Compartment Grid** (`grid`, `internal`) — defined by `cols`, `rows`, `cell`, `wall`. The lid and dose cup mate to the tray's compartment pitch.
- **Material awareness:** `tolerance_by_material` declared — lid / cup clearance tunes to the print material.
- **Societal benefit:** an organiser sized to the exact schedule and compartment size a person needs, printed at home instead of a fixed store layout — supporting adherence and independence.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`; final solid assigned to `result`; dispatch on `target_part`.
- Compartments are blind pockets over a solid floor; the lid cavity opens down; the dose-cup tab opens to air — so every output is **watertight, single-body**.
