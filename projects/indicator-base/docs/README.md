# Dial Indicator Base / Base para Comparador

Parametric bench bases and holders for dial indicators, test indicators and
gauges — sized to the 8 mm indicator stem, built CadQuery-first for Yantra4D.

---

## English

Hold a gauge exactly where the measurement is. Bolt one of these to a surface
plate, a magnetic base or a machine table.

### Modes

| Mode | Part | What it is |
|------|------|-----------|
| **Stem Clamp Column Base** | `stem_base` | A column with a horizontal cross-bore that grips the 8 mm stem, closed by a saw-cut clamp slot and a cross clamp screw. |
| **Lug-Back Mount Base** | `lug_base` | A flat-faced post with a lug pad; the indicator's lug back bolts flat through a manifold hole. |
| **Dovetail Test-Indicator Holder** | `dovetail_holder` | A tower carrying a 60° dovetail through-slot for lever/finger test indicators, pinched by a cross clamp. |

### Real dimensions

- **Indicator stem = 8 mm** — the industry standard used by Mitutoyo Series 2
  and most metric dial indicators. The bore is cut at nominal + **0.1 mm**
  clearance.
- The `stem_dia` range reaches **9.525 mm (3/8 in)** for imperial-stem
  indicators.
- The dovetail is a **60°** trapezoidal groove (≈8 mm top / 11 mm base), the
  common lever-indicator mount.

### Parameters

- `stem_dia` — the gauge stem. Set this first for the stem base.
- `post_height`, `column_dia` — the column / post.
- `base_width`, `base_depth`, `base_thick` — the footprint. More mass and a wider
  footprint = steadier readings and less tip-over.

### Printing notes

The clamp relies on print stiffness: use **PETG or PLA at ≥40% infill** so the
saw-cut clamp actually pinches the stem — a flexible column will drift. Ream the
stem bore to a true 8 mm if your printer runs tight. All three modes are
watertight and single-body across the full parameter range; the base fixing holes
and the stem/clamp bores all open to a face, so there are no trapped voids.

---

## Español

Sujeta una galga exactamente donde está la medición. Atorníllala a un mármol, una
base magnética o una mesa de máquina.

### Modos

| Modo | Pieza | Qué es |
|------|-------|--------|
| **Base de Columna con Tija** | `stem_base` | Una columna con barreno transversal que sujeta la tija de 8 mm, cerrado por una ranura de apriete y un tornillo transversal. |
| **Base de Montaje por Lengüeta** | `lug_base` | Un poste de cara plana con almohadilla; la lengüeta trasera se atornilla plana. |
| **Soporte de Cola de Milano** | `dovetail_holder` | Una torre con ranura pasante de cola de milano a 60° para palpadores de palanca. |

### Dimensiones reales

- **Tija = 8 mm** — el estándar de Mitutoyo Serie 2 y la mayoría de comparadores
  métricos. El barreno se corta a nominal + **0.1 mm** de holgura.
- El rango de `stem_dia` alcanza **9.525 mm (3/8 in)** para comparadores
  imperiales.
- La cola de milano es una ranura trapezoidal a **60°** (≈8 mm arriba / 11 mm
  base).

### Parámetros

- `stem_dia` — la tija de la galga. Configúralo primero para la base de tija.
- `post_height`, `column_dia` — la columna / poste.
- `base_width`, `base_depth`, `base_thick` — la huella.

### Notas de impresión

El apriete depende de la rigidez: usa **PETG o PLA con ≥40% de relleno**. Los tres
modos son estancos y de cuerpo único en todo el rango; todos los barrenos abren a
una cara, sin huecos atrapados.

---

**License / Licencia:** CERN-OHL-W-2.0
