# Precision Pin Vise / Berbiquí de Precisión

A parametric precision pin vise and small workholding family — built CadQuery-first
for Yantra4D.

---

## English

Hold micro-drills, taps, broaches, wire and small stock. The collet bore covers
the classic **0–3 mm** pin-vise capacity, and the family scales up toward ER-collet
sizes.

### Modes

| Mode | Part | What it is |
|------|------|-----------|
| **Pin Vise Body** | `pin_vise_body` | A fluted grip cylinder with a collet bore open to the top and a hollow handle open to the bottom that clears long stock. |
| **Split Draw-In Collet** | `collet` | A truncated-cone collet with a through bore (manifold tube) and three relief slots so the jaws close on the tool. |
| **V-Groove Bench Block** | `bench_block_vise` | A precision block with a through V-groove to cradle round or square work, a cross clamp screw and two base holes. |

### Real dimensions

- **Collet capacity 0–3 mm** — the classic watchmaker pin-vise range for
  micro-drills, broaches and wire. `collet_bore` reaches **6 mm**, overlapping the
  **ER11** collet range (1–7 mm) for larger shanks.
- The V-groove bench block is a **60°** vee sized by `jaw_opening` (nominal stock
  size, 3–20 mm).

### Parameters

- `collet_bore` — the tool shank you hold most. Set this first.
- `body_dia`, `body_length`, `flute_count`, `handle_bore` — the vise body.
- `jaw_opening` — the bench block V capacity.

### Printing notes

The collet slots need a **stiff, slightly springy** print — PETG or nylon close
cleanly; brittle PLA can snap a jaw. Print the bore at the nominal shank and ream
to a light slip fit. The fluted grip is a **print-safe stand-in for a knurl** — it
stays fully manifold at every flute count. A printed pin vise is a light-duty
holder, not a substitute for a hardened-steel lathe collet. All three modes are
watertight and single-body across the full parameter range; the collet and handle
bores are through / open-to-face, so there are no trapped voids.

---

## Español

Sujeta micro-brocas, machos, escariadores, alambre y piezas pequeñas. El
alojamiento de la pinza cubre la capacidad clásica de **0–3 mm**, y la familia
escala hacia tamaños de pinza ER.

### Modos

| Modo | Pieza | Qué es |
|------|-------|--------|
| **Cuerpo del Berbiquí** | `pin_vise_body` | Un cilindro estriado con alojamiento de pinza abierto arriba y mango hueco abierto abajo. |
| **Pinza Partida** | `collet` | Una pinza cónica truncada con barreno pasante y tres ranuras de alivio para cerrar sobre la herramienta. |
| **Bloque de Banco con Ranura en V** | `bench_block_vise` | Un bloque de precisión con ranura en V pasante, tornillo de apriete transversal y dos agujeros de base. |

### Dimensiones reales

- **Capacidad de pinza 0–3 mm** — el rango clásico del berbiquí de relojero.
  `collet_bore` llega a **6 mm**, solapando el rango **ER11** (1–7 mm).
- El bloque en V es una vee a **60°** dimensionada por `jaw_opening` (3–20 mm).

### Parámetros

- `collet_bore` — el vástago que más sujetas. Configúralo primero.
- `body_dia`, `body_length`, `flute_count`, `handle_bore` — el cuerpo.
- `jaw_opening` — la capacidad de la V del bloque.

### Notas de impresión

Las ranuras de la pinza necesitan una impresión **rígida y algo elástica** — PETG
o nylon cierran limpiamente; el PLA frágil puede romper una mordaza. El agarre
estriado es un **moleteado apto para impresión** — permanece totalmente manifold
en cualquier número de estrías. Los tres modos son estancos y de cuerpo único; los
barrenos son pasantes o abiertos a una cara, sin huecos atrapados.

---

**License / Licencia:** CERN-OHL-W-2.0
