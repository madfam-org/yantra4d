# Dial Indicator Holder / Soporte de Comparador

An articulated holder for a dial or test indicator — stem clamp, reach arm and
base post — sized to the 8 mm indicator stem, built CadQuery-first for Yantra4D.

Shares the 8 mm stem socket with the **`indicator-base`** cartridge, so one gauge
fits either holder.

---

## English

Put a gauge exactly where the measurement is. Grip the stem, reach out on the
arm, and clamp to the post.

### Modes

| Mode | Part | What it is |
|------|------|-----------|
| **Stem Clamp** | `stem_clamp` | A saw-cut split clamp gripping the 8 mm stem in a cross-bore, closed by a cross screw, on a short mount tab. |
| **Reach Arm** | `snug_arm` | A stem clamp at one end and a post clamp at the other, joined by a solid bar — swing the gauge over the work. |
| **Base + Post** | `base_post` | A heavy filleted base plate with a vertical post and four mount holes; the arm's post clamp slips over the post. |

### Real dimensions

- **Indicator stem = 8 mm** — the industry standard (Mitutoyo Series 2 / AGD
  Group 2). The bore is cut at nominal + **0.1 mm** clearance.
- The `stem_dia` range reaches **9.525 mm (3/8 in)** for imperial-stem
  indicators.
- The post clamp bore is nominal + **0.25 mm** for a slip fit over the post.
- Both the stem and post are held by **saw-cut split clamps** closed by a cross
  screw — print stiffness does the gripping.

### Parameters

- `stem_dia` — the gauge stem. Set this first.
- `post_dia`, `arm_len` — the post and the reach arm.
- `post_height`, `base_width` — the base stand.
- `wall`, `clamp_screw_d` — body wall and the clamp/mount screws.

### Printing notes

The clamps grip by stiffness: use **PETG or PLA at ≥40% infill** so the split
rings actually pinch — a flexible clamp drifts. Ream the stem bore to a true
8 mm if your printer runs tight. All three modes are watertight and single-body
across the parameter range: the clamp bores, saw slits and screw holes all open
to a face, so there are no trapped voids.

---

## Español

Coloca la galga exactamente donde está la medición. Sujeta la tija, alcanza con
el brazo y aprieta al poste.

### Modos

| Modo | Pieza | Qué es |
|------|-------|--------|
| **Mordaza de Tija** | `stem_clamp` | Una mordaza partida con corte de sierra que sujeta la tija de 8 mm en un barreno transversal, cerrada por un tornillo, sobre una pestaña de montaje. |
| **Brazo de Alcance** | `snug_arm` | Mordaza de tija en un extremo y mordaza de poste en el otro, unidos por una barra sólida — lleva la galga sobre la pieza. |
| **Base + Poste** | `base_post` | Una placa base pesada y redondeada con poste vertical y cuatro agujeros; la mordaza de poste del brazo se desliza sobre el poste. |

### Dimensiones reales

- **Tija = 8 mm** — el estándar de la industria (Mitutoyo Serie 2 / AGD Grupo
  2). El barreno se corta a nominal + **0.1 mm**.
- El rango de `stem_dia` alcanza **9.525 mm (3/8 in)** para tijas imperiales.
- El barreno de la mordaza de poste es nominal + **0.25 mm** para ajuste
  deslizante.
- La tija y el poste se sujetan con **mordazas partidas de corte de sierra**
  cerradas por un tornillo — la rigidez de impresión agarra.

### Parámetros

- `stem_dia` — la tija de la galga. Configúralo primero.
- `post_dia`, `arm_len` — el poste y el brazo de alcance.
- `post_height`, `base_width` — el soporte base.
- `wall`, `clamp_screw_d` — pared del cuerpo y tornillos.

### Notas de impresión

Las mordazas agarran por rigidez: usa **PETG o PLA con ≥40% de relleno**.
Escaria el barreno a 8 mm reales si va apretado. Los tres modos son estancos y
de cuerpo único en todo el rango; los barrenos, ranuras de sierra y agujeros de
tornillo abren a una cara, sin huecos atrapados.

---

**License / Licencia:** CERN-OHL-W-2.0
