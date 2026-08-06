# Business Card / Note Stand

A desk stand that holds cards or notes upright at a viewing angle, **parametric on
the card width and slot width**, in three distinct forms. CadQuery-first
parametric hyperobject cartridge.

## Modes

| Mode | Part id | What it is |
|------|---------|------------|
| Angled Card Easel | `card_stand` | A wedge easel with a single raked slot for a stack of cards leaning back. |
| Note / Memo Clip | `note_clip` | A low, heavy base with a thin near-vertical slot gripping one note / memo / photo. |
| Terraced Display Rack | `multi_slot` | A stepped block with several parallel slots so cards fan out for display. |

## Key parameters

- **Card Width** (`card_w`, default **88.9 mm = 3.5 in**) — the card along the
  slot. A standard business card is 88.9 × 50.8 mm.
- **Slot Width** (`slot_w`, default 4 mm) — a single card is ~0.4 mm; 4 mm holds a
  small stack. Drop to 1–2 mm for a single card.
- **Card Lean** (`lean_deg`, default 18°) — backward lean from vertical.
- **Base Depth** (`depth`), **Height** (`height`), **Slot Depth** (`slot_depth`),
  **Wall Thickness** (`wall`).
- Multi: **Slot Count** (`slots`), **Terrace Step** (`step`).

## Design / printing notes

- Every card slot is an **upward-open rectangular groove** cut into a solid block
  (a raked box cutter that pokes above the top face). Cutting into a solid keeps
  the model a single watertight body with no trapped voids — the specific pitfall
  the brief calls out for card-stand slots.
- The block's vertical edges are **filleted before** the slot is cut (filleting a
  slotted body is what crashes the kernel).
- The easel's front wedge is a boolean cut, not a fillet, so it stays manifold.
- Prints flat on the base with no supports; the slot opening faces up.

## CDG interface

- `card_slot_profile` — `geometry_type: profile`, `standard: "business card"`,
  driven by `card_w`, `slot_w`, `lean_deg`, `slot_depth`.

## License

CERN-OHL-W-2.0 (CERN Open Hardware Licence, Weakly Reciprocal).

---

# Soporte para Tarjetas / Notas

Un soporte de escritorio que sostiene tarjetas o notas en vertical a un ángulo de
visión, **parametrizado según el ancho de la tarjeta y de la ranura**, en tres
formas distintas.

## Modos

| Modo | Id de pieza | Qué es |
|------|-------------|--------|
| Caballete Inclinado | `card_stand` | Un caballete en cuña con una ranura inclinada para una pila de tarjetas. |
| Pinza para Notas | `note_clip` | Una base baja y pesada con una ranura casi vertical que sostiene una nota / memo / foto. |
| Estante Escalonado | `multi_slot` | Un bloque escalonado con varias ranuras paralelas para desplegar tarjetas. |

## Parámetros clave

- **Ancho de Tarjeta** (`card_w`, predet. **88.9 mm = 3.5 pulg**) — una tarjeta de
  presentación estándar mide 88.9 × 50.8 mm.
- **Ancho de Ranura** (`slot_w`, predet. 4 mm) — una sola tarjeta es ~0.4 mm; 4 mm
  sostiene una pequeña pila.
- **Inclinación** (`lean_deg`, predet. 18°).
- **Profundidad** (`depth`), **Altura** (`height`), **Profundidad de Ranura**
  (`slot_depth`), **Grosor** (`wall`).

## Notas de diseño / impresión

- Cada ranura es un **surco rectangular abierto hacia arriba** cortado en un bloque
  sólido. Cortar en un sólido mantiene el modelo como un único cuerpo estanco sin
  vacíos atrapados.
- Los bordes verticales del bloque se **redondean antes** de cortar la ranura.
- La cuña frontal del caballete es un corte booleano, no un redondeo.
- Se imprime plano sobre la base sin soportes; la abertura de la ranura mira hacia arriba.

## Interfaz CDG

- `card_slot_profile` — `geometry_type: profile`, `standard: "business card"`,
  gobernado por `card_w`, `slot_w`, `lean_deg`, `slot_depth`.

## Licencia

CERN-OHL-W-2.0 (Licencia de Hardware Abierto del CERN, Débilmente Recíproca).
