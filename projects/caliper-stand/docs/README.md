# Caliper Base Stand / Soporte de Calibre

A bench stand that holds a caliper for repeated gauging — hands-free cradle,
locking beam clamp and height-gauge depth base, built CadQuery-first for
Yantra4D.

---

## English

Turn any bench caliper into a fixture. Read it hands-free, lock it against a
reference, or stand it up as a rough height gauge.

### Modes

| Mode | Part | What it is |
|------|------|-----------|
| **Hands-Free Cradle** | `jaw_cradle` | A base block with a beam-shaped pocket in the top; the caliper beam drops in and rests upright for reading. |
| **Locking Beam Clamp** | `beam_clamp` | Like the cradle, plus a saw slit and a cross clamp screw; tighten to pinch the beam and lock the caliper against a reference. |
| **Height-Gauge Depth Base** | `depth_base` | A wide flat reference plate with a vertical beam slot; the caliper stands beam-up (jaws down) with the flat face as the datum. |

### Real dimensions

- **Caliper beam ≈ 16 mm wide × 11 mm thick** — a standard 150 mm digital
  caliper (≈237 × 76 × 11 mm overall) has an ~11 mm-thick beam. **Measure your
  own** with the caliper itself and set `beam_w` / `beam_t`; beams vary between
  makers.
- The pocket is cut at beam nominal + a per-side `fit_clear` (default 0.4 mm) so
  the beam drops in; the clamp takes up the slack.

### Parameters

- `beam_w`, `beam_t` — the caliper beam cross-section. Set these to your caliper.
- `fit_clear` — the pocket fit.
- `base_len`, `base_thick`, `wall` — the stand size and rigidity.
- `clamp_screw_d` — the clamp and corner mount screws.

### Printing notes

Print in **PETG or PLA at ≥30% infill** so the pocket walls stay rigid — the
clamp variant needs stiffness to pinch. Open the pocket 0.1 mm with a file if
your printer runs tight. All three modes are watertight and single-body across
the parameter range: the beam pocket opens to the top face, the depth slot goes
clean through, and all screw and mount holes vent to a face — no trapped voids.

---

## Español

Convierte cualquier calibre de banco en un utillaje. Léelo sin manos, bloquéalo
contra una referencia, o ponlo de pie como calibre de altura básico.

### Modos

| Modo | Pieza | Qué es |
|------|-------|--------|
| **Cuna sin Manos** | `jaw_cradle` | Un bloque base con un bolsillo con forma de cuerpo arriba; el calibre entra y descansa vertical para leer. |
| **Mordaza de Bloqueo** | `beam_clamp` | Como la cuna, más una ranura de sierra y un tornillo transversal; apriétalo para bloquear el calibre contra una referencia. |
| **Base de Altura** | `depth_base` | Una placa de referencia plana y ancha con ranura vertical; el calibre se pone de pie (mordazas abajo) con la cara plana como datum. |

### Dimensiones reales

- **Cuerpo del calibre ≈ 16 mm de ancho × 11 mm de espesor** — un calibre
  digital estándar de 150 mm (≈237 × 76 × 11 mm) tiene un cuerpo de ~11 mm.
  **Mide el tuyo** con el propio calibre y ajusta `beam_w` / `beam_t`; los
  cuerpos varían entre fabricantes.
- El bolsillo se corta a nominal + una holgura por lado `fit_clear` (0.4 mm por
  defecto); la mordaza recoge la holgura.

### Parámetros

- `beam_w`, `beam_t` — la sección del cuerpo del calibre. Ajústalos a tu calibre.
- `fit_clear` — el ajuste del bolsillo.
- `base_len`, `base_thick`, `wall` — tamaño y rigidez del soporte.
- `clamp_screw_d` — los tornillos de apriete y montaje.

### Notas de impresión

Imprime en **PETG o PLA con ≥30% de relleno** para que las paredes del bolsillo
sean rígidas — la variante de mordaza necesita rigidez. Abre el bolsillo 0.1 mm
con una lima si va apretado. Los tres modos son estancos y de cuerpo único en
todo el rango; el bolsillo abre a la cara superior, la ranura de profundidad
pasa de lado a lado y todos los agujeros ventilan a una cara — sin huecos
atrapados.

---

**License / Licencia:** CERN-OHL-W-2.0
