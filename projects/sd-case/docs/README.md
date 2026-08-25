# SD / MicroSD Card Case

A parametric memory-card organizer. Slots are cut to real card footprints in a grid, with a thumb notch per slot so cards pull out easily.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `sd_tray` | SD Tray | A rows×columns grid of full-size card slots (SD, microSD, or CF, per `card_type`). |
| `micro_tray` | MicroSD Tray | A denser fixed-microSD grid (one extra row and column). |
| `combo_case` | Combo Case | One block with an SD slot bank beside a microSD bank, sharing a central wall. |

## Standards & dimensions

- **SD card:** 24.0 × 32.0 × 2.1 mm.
- **microSD card:** 11.0 × 15.0 × 1.0 mm.
- **CompactFlash:** 43.0 × 36.0 × 3.3 mm.
- **Slot clearance:** ~0.4 mm per side (adjustable) so cards drop in and pull out.

## Hyperobject Profile

- **Domain:** commercial.
- **CDG interface:** `card_slot_grid` (grid) — the memory-card slot grid, sharing the card-footprint pocket convention with `card-holder` and `deck-box` (the `card-format` family). Driven by `card_type`, `cols`, `rows`, `clearance`.
- **License:** CERN-OHL-W-2.0.

## Parameters

- `card_type` — `SD`, `microSD`, or `CF` (SD Tray mode; the other modes are fixed-format).
- `cols` (1–8), `rows` (1–6) — grid size.
- `wall` (1.2–5 mm) — wall between and around slots.
- `floor` (1–5 mm) — base thickness under the slots.
- `clearance` (0.15–1 mm) — per-side slot gap.

## Printing notes / Notas de impresión

**EN:** Prints flat with no supports. Drop `clearance` to ~0.25 mm for a snug hold in dimensionally stable filament; open it toward 0.6 mm for recycled PLA that prints slightly oversize.

**ES:** Se imprime plano sin soportes. Baja `clearance` a ~0.25 mm para un ajuste firme en filamento estable; ábrelo hacia 0.6 mm para PLA reciclado que imprime ligeramente sobredimensionado.

## License

CERN-OHL-W-2.0
