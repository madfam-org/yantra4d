# Business Card Holder

A parametric business-card holder for desk or wall. Three modes share one card groove so a stack sized for any of them — or for the wider `card-format` family — seats cleanly.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `desk_tray` | Angled Desk Tray | Shallow tray that leans back so a stack of cards fans forward, with a front retaining lip. |
| `wall_holder` | Wall Pocket | Flat-backed pocket with two screw holes and a front thumb window for wall mounting. |
| `stack_box` | Upright Divider Box | Upright box holding a full brick of cards on edge, with a scalloped front finger notch. |

## Standards & dimensions

- **Business card:** 88.9 × 50.8 mm (US / ISO 7810 ID-1). The EU 85 × 55 mm card fits the same groove width via `card_wid`.
- **Card thickness:** ~0.35 mm per card, so a 12 mm stack is roughly 34 cards.
- **Slip clearance:** 0.6 mm per side in the groove so a real stack drops in.

## Hyperobject Profile

- **Domain:** commercial.
- **CDG interface:** `card_groove` (profile) — the business-card footprint groove, shared with `card-holder` and `deck-box` (the `card-format` family). Driven by `card_len`, `card_wid`, `stack_mm`.
- **License:** CERN-OHL-W-2.0.

## Parameters

- `card_len` (60–120 mm) — long edge of the card.
- `card_wid` (40–70 mm) — short edge of the card.
- `stack_mm` (3–40 mm) — thickness of the card brick.
- `wall` (1.6–6 mm) — wall / floor thickness.
- `lean_ang` (0–30°) — how far the desk tray leans back.

## Printing notes / Notas de impresión

**EN:** All three modes print flat with no supports. Print the desk tray as oriented — the leaned block already sits flat on its base. Increase `wall` for a heavier, more stable holder.

**ES:** Los tres modos se imprimen planos sin soportes. Imprime la bandeja tal como está orientada — el bloque inclinado ya se apoya plano sobre su base. Aumenta `wall` para un soporte más pesado y estable.

## License

CERN-OHL-W-2.0
