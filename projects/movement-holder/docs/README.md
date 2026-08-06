# Watchmaker Movement Holder / Soporte de Movimiento de Relojero

Parametric holders and casing rings for servicing mechanical watch movements —
ligne-honest, built CadQuery-first for Yantra4D.

---

## English

Seat, protect and organize watch movements on the bench during disassembly,
oiling and hand-fitting. The movement pocket and stem relief are dimensioned in
real calibre units, so a printed holder actually fits the movement it is named
for.

### Modes

| Mode | Part | What it is |
|------|------|-----------|
| **Single-Calibre Movement Cup** | `movement_cup` | A puck with a top movement pocket and a bottom stem/crown relief. Both bores open to a face — no trapped void. |
| **Multi-Station Servicing Tray** | `multi_station` | A bar of identical pockets with a lengthwise finger-scoop, for batching several movements of one size. |
| **Movement Casing Ring** | `case_ring` | An annulus that seats over the movement band during hand-fitting, with three caseback-tool grip notches. Manifold through-bore. |

### Real dimensions

- **1 ligne = 2.2558 mm** (the Swiss watchmaking unit).
- Defaults match the **ETA 2824-2**: Ø **25.6 mm** (11.5 ligne), height **4.6 mm** —
  the most common Swiss automatic.
- The `movement_dia` range covers **15.3 mm** (≈6¾ ligne lady's calibre) to
  **40 mm**, so it also reaches the **ETA 6497** pocket-watch movement
  (Ø 36.6 mm / 16.5 ligne, 4.5 mm thick) and the **ETA 2892** (Ø 25.6 mm, 3.6 mm).

### Parameters

- `movement_dia` / `movement_height` — the calibre. Set these first.
- `wall` — radial material around the pocket.
- `base_height` — solid stock below the seat (cup).
- `stem_relief_dia` — bottom bore that clears the winding stem / setting lever.
- `station_count` — pockets in the tray (2–8).

### Printing notes

Print the pocket **0.2–0.3 mm oversize**; a movement that rubs the print can mark
its own band. PLA or PETG holds tolerance well; avoid brittle resins that chip at
the pocket lip. All three modes are watertight and single-body at every parameter
setting.

---

## Español

Asienta, protege y organiza movimientos de reloj en el banco durante el desarme,
el aceitado y la colocación de agujas. El alojamiento del movimiento y el alivio
de la tija están dimensionados en unidades reales de calibre, de modo que un
soporte impreso encaja de verdad con el movimiento al que da nombre.

### Modos

| Modo | Pieza | Qué es |
|------|-------|--------|
| **Copa de Movimiento (Un Calibre)** | `movement_cup` | Un disco con alojamiento superior y alivio inferior de tija. Ambos abren a una cara. |
| **Bandeja de Servicio Multi-Estación** | `multi_station` | Una barra de alojamientos idénticos con rebaje longitudinal, para lotes del mismo tamaño. |
| **Anillo de Encaje del Movimiento** | `case_ring` | Un anillo sobre la banda del movimiento durante la colocación de agujas, con tres muescas de agarre. |

### Dimensiones reales

- **1 línea = 2.2558 mm** (la unidad relojera suiza).
- Los valores por defecto coinciden con el **ETA 2824-2**: Ø **25.6 mm**
  (11.5 líneas), altura **4.6 mm**.
- El rango de `movement_dia` va de **15.3 mm** a **40 mm**, alcanzando también el
  **ETA 6497** de reloj de bolsillo (Ø 36.6 mm / 16.5 líneas).

### Parámetros

- `movement_dia` / `movement_height` — el calibre. Configúralos primero.
- `wall` — material radial alrededor del alojamiento.
- `base_height` — material sólido bajo el asiento (copa).
- `stem_relief_dia` — perforación inferior que libera la tija de cuerda.
- `station_count` — alojamientos en la bandeja (2–8).

### Notas de impresión

Imprime el alojamiento **0.2–0.3 mm sobredimensionado**. PLA o PETG mantiene bien
la tolerancia. Los tres modos son estancos (watertight) y de cuerpo único en
cualquier configuración de parámetros.

---

**License / Licencia:** CERN-OHL-W-2.0
