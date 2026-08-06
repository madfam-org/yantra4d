# Feeler / Drill Gauge Organizer / Organizador de Galgas y Brocas

Parametric organizers for feeler gauges, drill / tap sets and gauge leaves —
built CadQuery-first for Yantra4D. A blade you can see and grab is a blade you
actually use.

---

## English

### Modes

| Mode | Part | What it is |
|------|------|-----------|
| **Upright Feeler-Blade Rack** | `feeler_rack` | Stands blades upright in thin obround slots open to the top, matched to the 12.7 mm blade width. |
| **Graduated Drill Index** | `drill_index` | A grid of blind holes stepping from small to the set maximum, each open to the top — a numbered drill / wire-gauge stand. |
| **Flat Blade Tray** | `blade_tray` | Parallel channels that store loose leaves flat, with a front finger cut-out to pick one out. |

### Real dimensions

- **Feeler blade width = 12.7 mm (1/2 in)** — the standard leaf width; a standard
  **metric feeler set is 13 blades from 0.05 to 1.00 mm**, which is the default
  `blade_count`.
- The drill index grid graduates across `index_cols × index_rows` holes up to
  `max_bit_dia`. A **#1–#60 wire-gauge set** tops out at **5.79 mm (#1)**; a
  1–13 mm metric index needs `max_bit_dia = 13`.

### Parameters

- `blade_width`, `blade_count`, `slot_pitch` — the feeler rack / tray.
- `index_cols`, `index_rows`, `max_bit_dia` — the graduated drill grid.
- `wall`, `body_height` — border material and how deep tools are held.

### Printing notes

Blade slots are 1.6–1.8 mm — wide enough to swallow a stack of leaves without
splitting a wall. If your printer over-extrudes, **widen `slot_pitch`**, not the
slot. Graduated holes come out a touch undersize from nozzle rounding; **chase
them with the actual drills** to seat the set. Recycled PETG is fine — this is a
non-precision fixture. All three modes are watertight and single-body across the
parameter range; every slot and hole opens to the top face, so there are no
trapped voids.

---

## Español

### Modos

| Modo | Pieza | Qué es |
|------|-------|--------|
| **Soporte Vertical de Láminas** | `feeler_rack` | Sostiene láminas verticales en ranuras finas abiertas arriba, al ancho de 12.7 mm. |
| **Índice de Brocas Graduado** | `drill_index` | Una rejilla de agujeros ciegos que van de pequeño al máximo del juego, cada uno abierto arriba. |
| **Bandeja Plana de Láminas** | `blade_tray` | Canales paralelos que guardan láminas planas, con un rebaje frontal para tomar una. |

### Dimensiones reales

- **Ancho de lámina = 12.7 mm (1/2 in)** — el ancho estándar; un **juego métrico
  estándar tiene 13 láminas de 0.05 a 1.00 mm**, que es el `blade_count` por
  defecto.
- La rejilla del índice gradúa `index_cols × index_rows` agujeros hasta
  `max_bit_dia`. Un **juego #1–#60** llega a **5.79 mm (#1)**.

### Parámetros

- `blade_width`, `blade_count`, `slot_pitch` — el soporte / bandeja de láminas.
- `index_cols`, `index_rows`, `max_bit_dia` — la rejilla graduada de brocas.
- `wall`, `body_height` — material de borde y profundidad de sujeción.

### Notas de impresión

Las ranuras de 1.6–1.8 mm tragan una pila de láminas sin partir la pared. Si tu
impresora sobre-extruye, **aumenta `slot_pitch`**. Persigue los agujeros
graduados con las brocas reales. El PETG reciclado sirve. Los tres modos son
estancos y de cuerpo único; cada ranura y agujero abre a la cara superior, sin
huecos atrapados.

---

**License / Licencia:** CERN-OHL-W-2.0
