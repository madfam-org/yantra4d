# PC Fan Filter Frame · Marco de Filtro para Ventilador PC

A parametric dust-filter frame for standard PC / printer fans, built CadQuery-first
(B-Rep) for the Yantra4D Hyperobjects Commons.

Marco de filtro antipolvo paramétrico para ventiladores estándar de PC / impresora,
construido con CadQuery (B-Rep) para el Commons de Hiperobjetos de Yantra4D.

---

## English

The frame drops onto a fan's intake face on the same corner-hole square the fan
uses (40 / 60 / 80 / 120 / 140 mm), holding a cut disc of nylon/steel mesh or open-
cell foam over the airflow bore behind a printed retaining grille. No glue: the
grille captures the media; you replace it when it clogs.

### Modes

| Mode | What it is |
|------|------------|
| **Screw-Mount Frame** (`filter_frame`) | Square flange with the four fan corner holes, a media pocket and a retaining grille. Bolts on with the fan's own screws. |
| **Magnetic Frame** (`magnet_frame`) | The same media pocket + grille, but the corners carry blind magnet pockets instead of screw holes, so the frame clicks onto a steel fan grill or a magnet ring — no tools. |
| **Two-Stage Cartridge** (`stacked_filter`) | A taller frame with a coarse pre-filter grille at the base and a fine grille partway up, separated by a ledge, capturing two media layers in one printed part. |

### Key parameters

- **Fan Size** — selects the corner-hole spacing and airflow bore from the PC-fan table.
- **Frame Height** — body height along the airflow axis.
- **Media Pocket Depth** — recess that holds the filter disc.
- **Grille Bar Width / Grille Rings** — density of the retaining grille.
- **Magnet Diameter / Depth** — corner magnet pockets (magnetic frame only).

### Printing

Print flat, grille-side down, no supports. PLA or PETG. Cut a disc of mesh or foam
to the bore diameter and seat it in the pocket before snapping the fan on.

---

## Español

El marco se coloca en la cara de admisión del ventilador sobre el mismo cuadro de
orificios de esquina que usa el ventilador (40 / 60 / 80 / 120 / 140 mm), sujetando
un disco recortado de malla de nylon/acero o espuma de célula abierta sobre el
orificio de flujo tras una rejilla de retención impresa. Sin pegamento: la rejilla
sujeta el medio; lo reemplazas cuando se obstruye.

### Modos

| Modo | Qué es |
|------|--------|
| **Marco Atornillado** (`filter_frame`) | Brida cuadrada con los cuatro orificios de esquina del ventilador, un bolsillo de medio y una rejilla de retención. Se atornilla con los tornillos del propio ventilador. |
| **Marco Magnético** (`magnet_frame`) | El mismo bolsillo + rejilla, pero las esquinas llevan bolsillos ciegos de imán en vez de orificios de tornillo, así el marco encaja en una rejilla de acero o un anillo magnético — sin herramientas. |
| **Cartucho de Dos Etapas** (`stacked_filter`) | Un marco más alto con una rejilla de prefiltro gruesa en la base y una rejilla fina más arriba, separadas por una repisa, capturando dos capas de medio en una sola pieza impresa. |

### Parámetros clave

- **Tamaño de Ventilador** — selecciona el espaciado de orificios y el orificio de flujo de la tabla de ventiladores PC.
- **Altura de Marco** — altura del cuerpo a lo largo del eje de flujo.
- **Profundidad de Bolsillo** — hueco que sujeta el disco filtrante.
- **Ancho de Barra / Anillos de Rejilla** — densidad de la rejilla de retención.
- **Diámetro / Profundidad de Imán** — bolsillos de imán de esquina (solo marco magnético).

### Impresión

Imprime plano, con la rejilla hacia abajo, sin soportes. PLA o PETG. Recorta un
disco de malla o espuma al diámetro del orificio y asiéntalo en el bolsillo antes
de colocar el ventilador.

---

## Hyperobject Profile

- **Domain**: industrial
- **CDG interfaces**:
  - `fan_screw_pattern` — `grid`, standard **PC fan 40-140mm** — shares the fan
    corner-hole square with `fan-adapter` and `dust-shroud`.
  - `media_pocket` — `pocket` (internal) — the replaceable filter-media recess.
  - `magnet_pocket` — `socket` (internal) — the corner magnet pockets.
- **License**: CERN-OHL-W-2.0
- **Material awareness**: tolerance varies by material (pocket/grille clearances).

The PC-fan corner-hole square is a de-facto open interface shared by dozens of
makers. Because this frame mounts on that same square, one printed part fits the
fan a `fan-adapter` or `dust-shroud` already bolts to — growing the `pc-fan` family.
