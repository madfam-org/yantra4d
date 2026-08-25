# Fan-to-Duct Adapter · Adaptador de Ventilador a Ducto

Ducts a standard PC / printer fan into round tubing, a hose, or around a corner —
built CadQuery-first (B-Rep) for the Yantra4D Hyperobjects Commons.

Conecta un ventilador estándar de PC / impresora a tubería redonda, una manguera,
o alrededor de una esquina — construido con CadQuery (B-Rep) para el Commons de
Hiperobjetos de Yantra4D.

---

## English

A square fan flange on the real PC-fan corner-hole square (40 / 60 / 80 / 120 /
140 mm) transitions to a round outlet, so any surplus fan becomes a targeted air
mover for a printer enclosure, a fume line, a dust pickup or a cooling nook. The
flange bolts to the same fan a `fan-adapter`, `dust-shroud` or `fan-filter` mounts on.

### Modes

| Mode | What it is |
|------|------------|
| **Straight Round Duct** (`fan_to_round`) | A tapered transition from the fan bore down to a round duct spigot. The classic "put the fan on a duct" adapter. |
| **Hose Barb Nozzle** (`fan_to_hose`) | The same transition ending in a barbed nozzle that a push-on vacuum or garden hose grips, so a fan drives a hose directly. |
| **90-Degree Elbow** (`elbow_duct`) | The fan flange turns the airflow through a swept quarter-bend to a round outlet facing sideways, for tight enclosures where a straight duct will not fit. |

### Key parameters

- **Fan Size** — selects the corner-hole spacing and inlet bore.
- **Duct Length** — length of the straight transition (also the elbow stub reach).
- **Outlet Diameter** — inner diameter of the round outlet (clamped to the fan bore).
- **Duct Wall** — wall thickness of the duct tube.
- **Hose Barb OD / Ridges** — the push-on barb (hose mode only).

### Printing

Print flange-down. The straight and hose variants need no supports; the elbow
benefits from light supports under the bend, or print it bend-up on the outlet
face. PETG resists warm exhaust air better than PLA.

---

## Español

Una brida cuadrada de ventilador sobre el cuadro real de orificios de esquina de
ventilador PC (40 / 60 / 80 / 120 / 140 mm) transiciona a una salida redonda, así
cualquier ventilador sobrante se vuelve un movedor de aire dirigido para un
gabinete de impresora, una línea de humos, una recolección de polvo o un rincón de
enfriamiento. La brida se atornilla al mismo ventilador que un `fan-adapter`,
`dust-shroud` o `fan-filter` monta.

### Modos

| Modo | Qué es |
|------|--------|
| **Ducto Redondo Recto** (`fan_to_round`) | Una transición cónica del orificio del ventilador a una boquilla de ducto redonda. El adaptador clásico "pon el ventilador en un ducto". |
| **Boquilla de Manguera** (`fan_to_hose`) | La misma transición terminando en una boquilla con púas que una manguera de aspiradora o jardín a presión agarra, así el ventilador impulsa una manguera directamente. |
| **Codo de 90 Grados** (`elbow_duct`) | La brida del ventilador gira el flujo por un codo barrido a una salida redonda que apunta de lado, para gabinetes estrechos donde un ducto recto no cabe. |

### Parámetros clave

- **Tamaño de Ventilador** — selecciona el espaciado de orificios y el orificio de entrada.
- **Longitud de Ducto** — longitud de la transición recta (también el alcance del codo).
- **Diámetro de Salida** — diámetro interior de la salida redonda (limitado al orificio del ventilador).
- **Pared de Ducto** — grosor de pared del tubo de ducto.
- **Diámetro / Anillos de Púa** — la púa a presión (solo modo manguera).

### Impresión

Imprime con la brida hacia abajo. Las variantes recta y de manguera no necesitan
soportes; el codo se beneficia de soportes ligeros bajo la curva, o imprímelo con
la curva hacia arriba sobre la cara de salida. El PETG resiste el aire de escape
tibio mejor que el PLA.

---

## Hyperobject Profile

- **Domain**: industrial
- **CDG interfaces**:
  - `fan_screw_pattern` — `bolt_pattern`, standard **PC fan 40-140mm** — shares the
    fan corner-hole square with `fan-adapter` and `dust-shroud`.
  - `round_outlet` — `socket` (internal) — the round duct spigot.
  - `hose_barb` — `profile` (internal) — the push-on hose barb.
- **License**: CERN-OHL-W-2.0
- **Material awareness**: tolerance varies by material.

Because the flange mounts on the open PC-fan corner-hole square, this adapter fits
the same fan a `fan-adapter` or `dust-shroud` already bolts to — growing the
`pc-fan` family.
