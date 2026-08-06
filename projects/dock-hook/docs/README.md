# Monitor / Laptop Dock Hook

A **screwless** hook that snaps onto a desk or shelf edge (a printed C-profile
that springs over the edge), in three distinct forms. CadQuery-first parametric
hyperobject cartridge.

## Modes

| Mode | Part id | What it is |
|------|---------|------------|
| Dock Shelf Hook | `dock_hook` | C-clamp over the edge, a forward arm, and an up-turned retaining lip for a dock / tablet / phone stand. |
| Cable Drop Comb | `cable_drop` | C-clamp with a comb of upward-open obround slots so cables drop in and do not fall behind the desk. |
| Headset Cradle Hanger | `headset_hanger` | C-clamp with a forward arm ending in a broad rounded band cradle. |

## Key parameters

- **Edge Thickness** (`edge_t`, default 25 mm) — the desk / shelf edge the clamp
  grips. A common desktop is ~25 mm; measure yours.
- **Grip Depth** (`grip_depth`, default 40 mm) — how far the C reaches back onto
  the edge; more is more stable.
- **Hook Width** (`width`), **Wall Thickness** (`thick`).
- Dock: **Arm Reach** (`reach`), **Retaining Lip** (`lip`).
- Cable: **Cable Slot Width** (`slot_w`), **Cable Slot Count** (`slots`).
- Headset: **Cradle Width** (`cradle_w`).

## Design / printing notes

- The clamp is a solid block with the edge slot cut from the front face, so the
  inside is open to the desk — never a sealed cavity.
- The mouth lead-in is two **boolean wedge cuts** (not fillets); a fillet on the
  C + arm topology goes non-manifold.
- Cable slots are **obround** and open out of the top face, so each slot is a
  through-open notch with no trapped void.
- Print with the clamp mouth facing up (bridging the jaw gap) or on its side.
  The C relies on the filament's spring, so PETG or recycled PLA suits it.

## CDG interface

- `desk_edge_snap` — `geometry_type: snap`, driven by `edge_t`, `grip_depth`,
  `thick`, `width`. Parts that expose a matching desk-edge snap interoperate.

## License

CERN-OHL-W-2.0 (CERN Open Hardware Licence, Weakly Reciprocal).

---

# Gancho para Monitor / Laptop

Un gancho **sin tornillos** que se ajusta al borde de un escritorio o estante (un
perfil en C impreso que se sujeta sobre el borde), en tres formas distintas.

## Modos

| Modo | Id de pieza | Qué es |
|------|-------------|--------|
| Gancho de Repisa | `dock_hook` | Abrazadera en C, brazo hacia adelante y labio de retención para dock / tableta / soporte de teléfono. |
| Peine para Cables | `cable_drop` | Abrazadera en C con un peine de ranuras obredondas abiertas hacia arriba para que los cables no caigan tras el escritorio. |
| Colgador de Auriculares | `headset_hanger` | Abrazadera en C con brazo que termina en una cuna ancha para la diadema. |

## Parámetros clave

- **Grosor del Borde** (`edge_t`, predet. 25 mm) — el borde que sujeta la
  abrazadera. Un escritorio común es ~25 mm.
- **Profundidad de Agarre** (`grip_depth`, predet. 40 mm).
- **Ancho** (`width`), **Grosor de Pared** (`thick`).

## Notas de diseño / impresión

- La abrazadera es un bloque sólido con la ranura del borde cortada desde la cara
  frontal: el interior está abierto al escritorio, nunca una cavidad sellada.
- La entrada de la boca son dos **cortes en cuña** (no redondeos).
- Las ranuras de cable son **obredondas** y se abren por la cara superior.
- Se imprime con la boca de la C hacia arriba o de lado. Usa PETG o PLA reciclado.

## Interfaz CDG

- `desk_edge_snap` — `geometry_type: snap`, gobernado por `edge_t`, `grip_depth`,
  `thick`, `width`.

## Licencia

CERN-OHL-W-2.0 (Licencia de Hardware Abierto del CERN, Débilmente Recíproca).
