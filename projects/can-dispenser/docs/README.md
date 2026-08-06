# Can Storage Dispenser

A printable rack that stores standard beverage cans on their sides and gravity-feeds
them one at a time. Everything is driven by the **can diameter**, so one model adapts to
soda, seltzer, slim and tallboy cans.

## Modes

| Mode | What it makes |
|------|---------------|
| **Shelf Rack (FIFO)** | A compact two-level rack. Load cans on the top deck; they roll to the rear, drop to the bottom deck and roll forward to a front stop — first-in, first-out. |
| **Stack Column** | A vertical loading column. Cans stack on their sides between two end walls; take the lowest can from the front cutout and the column drops by one. |
| **Counter Tray** | A single angled lane for a countertop or pantry shelf, with a raised rear foot so cans roll forward. |

## Key parameters

- **Can Diameter (mm)** — 66 mm is a standard 12 oz / 355 ml can; 53 mm is a slim can.
- **Can Length (mm)** — the length of the can lying across the lane (122 mm typical).
- **Can Capacity** — how many cans queue per lane (the counter tray caps at 6).
- **Front Stop Lip (mm)** — the curb height that retains the lead can until it is taken.
- **Roll Clearance / Wall Thickness** — print-fit and structural tuning.

## Printing notes

Print with the lane opening facing up. No supports are needed for the shelf rack or the
counter tray; the stack column prints cleanly on its back. PETG or PLA both work.

**Food contact:** cans are sealed containers, so the rack does not touch the beverage.
If you repurpose this for open produce, choose a food-safe filament and finish — the
responsibility for food-safe material selection is the maker's.

---

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** `can_socket` — geometry type **socket**, standard **standard 12oz can** (Ø 66 mm).
- **Compatible with:** [`fridge-dispenser`](../../fridge-dispenser/) — shares the same standard-can socket, so a can that seats in one seats in the other.
- **License:** CERN-OHL-W-2.0

This cartridge grows the **beverage-can** family of the Yantra4D Hyperobjects Commons.
The socket is defined by the can diameter and length, the de-facto standard that lids,
racks and dispensers across the commons share.

---

# Dispensador de Latas (Español)

Un organizador imprimible que guarda latas de bebida estándar acostadas y las alimenta
por gravedad una a una. Todo se controla con el **diámetro de la lata**, así un solo
modelo se adapta a latas de refresco, agua mineral, delgadas y altas.

## Modos

| Modo | Qué genera |
|------|------------|
| **Rack de Estante (FIFO)** | Un rack compacto de dos niveles. Carga latas arriba; ruedan al fondo, caen al nivel inferior y ruedan al frente hasta un tope — primero en entrar, primero en salir. |
| **Columna Apilada** | Una columna vertical de carga. Las latas se apilan acostadas entre dos paredes; toma la más baja por el recorte frontal y la columna baja una posición. |
| **Bandeja de Mostrador** | Un carril inclinado para mostrador o despensa, con un pie trasero elevado para que las latas rueden al frente. |

## Parámetros clave

- **Diámetro de Lata (mm)** — 66 mm es una lata estándar de 355 ml; 53 mm es una lata delgada.
- **Largo de Lata (mm)** — el largo de la lata a lo ancho del carril (122 mm típico).
- **Capacidad de Latas** — cuántas latas hacen fila por carril (la bandeja limita a 6).
- **Labio de Tope Frontal (mm)** — la altura que retiene la lata delantera hasta tomarla.
- **Holgura de Rodado / Grosor de Pared** — ajuste de impresión y estructura.

## Notas de impresión

Imprime con la abertura del carril hacia arriba. No requiere soportes para el rack de
estante ni la bandeja; la columna imprime limpio sobre su espalda. PETG o PLA sirven.

**Contacto con alimentos:** las latas son envases sellados, así que el rack no toca la
bebida. Si lo reutilizas para producto abierto, elige un filamento y acabado aptos para
alimentos — la responsabilidad de elegir material apto para alimentos es del fabricante.

## Perfil de Hiperobjeto

- **Dominio:** hogar
- **Interfaz CDG:** `can_socket` — tipo **socket**, estándar **lata estándar de 355 ml** (Ø 66 mm).
- **Compatible con:** [`fridge-dispenser`](../../fridge-dispenser/) — comparte el mismo zócalo de lata estándar.
- **Licencia:** CERN-OHL-W-2.0
