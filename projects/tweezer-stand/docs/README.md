# Tweezers / Probe Stand / Soporte para Pinzas y Sondas

Parametric stands that hold tweezers, probes, fine screwdrivers and dental picks
tip-up and findable — built CadQuery-first for Yantra4D.

---

## English

A tweezer point that touches the bench or its neighbour goes blunt. These stands
keep delicate points up and apart.

### Modes

| Mode | Part | What it is |
|------|------|-----------|
| **Raked Wedge Stand** | `angled_stand` | A wedge with a back-raked top face and a row of obround slots, so tools rest tip-up. |
| **Radial Carousel** | `carousel` | A round base with slots arranged radially and a central finger well to lift it. |
| **Probe Rail** | `probe_rail` | A vertical rail on a foot with a row of upright bores, plus two foot mounting holes. |

### Real dimensions

- Slots are sized to **fine-tool girth**: `slot_width` spans **1.5–8 mm**, covering
  a typical watchmaker/electronics tweezer body (~2–4 mm) and larger probes.
- `slot_length` (default **10 mm**, up to 20 mm) steadies a standard **~130 mm
  watchmaker tweezer** without tipping.
- `rake_angle` tilts the wedge top **5–40°** (default 20°) so points face up.

### Parameters

- `slot_count`, `slot_length`, `slot_width`, `slot_pitch` — the tool slot array.
- `body_height`, `wall`, `rake_angle` — the body.

### Printing notes

Print `slot_width` **0.3–0.5 mm over the tool girth** so tools drop in without
forcing — a forced fit dulls the point you are protecting. Any material works;
recycled PLA/PETG is ideal for a bench organizer. All three modes are watertight
and single-body across the parameter range; every slot and bore opens to a face,
so there are no trapped voids.

---

## Español

Una punta de pinza que toca el banco o a su vecina se despunta. Estos soportes
mantienen las puntas delicadas arriba y separadas.

### Modos

| Modo | Pieza | Qué es |
|------|-------|--------|
| **Soporte en Cuña Inclinada** | `angled_stand` | Una cuña con cara superior inclinada hacia atrás y una fila de ranuras. |
| **Carrusel Radial** | `carousel` | Una base redonda con ranuras radiales y un hueco central para levantarla. |
| **Riel de Sondas** | `probe_rail` | Un riel vertical sobre un pie con una fila de barrenos verticales y dos agujeros de montaje. |

### Dimensiones reales

- Las ranuras se dimensionan al **grosor de herramienta fina**: `slot_width` va de
  **1.5–8 mm**, cubriendo el cuerpo de una pinza típica (~2–4 mm) y sondas más
  grandes.
- `slot_length` (por defecto **10 mm**, hasta 20 mm) estabiliza una **pinza de
  relojero de ~130 mm** sin volcarse.
- `rake_angle` inclina la cara de la cuña **5–40°** (por defecto 20°).

### Parámetros

- `slot_count`, `slot_length`, `slot_width`, `slot_pitch` — el arreglo de ranuras.
- `body_height`, `wall`, `rake_angle` — el cuerpo.

### Notas de impresión

Imprime `slot_width` **0.3–0.5 mm sobre el grosor** de la herramienta para que
entre sin forzar — un ajuste forzado despunta la herramienta. Cualquier material
sirve. Los tres modos son estancos y de cuerpo único; cada ranura y barreno abre a
una cara, sin huecos atrapados.

---

**License / Licencia:** CERN-OHL-W-2.0
