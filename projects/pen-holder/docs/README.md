# Pen / Stylus Holder & Grip

A desk pen station sized around a **real writing-instrument barrel diameter**, in
three distinct forms. CadQuery-first parametric hyperobject cartridge.

## Modes

| Mode | Part id | What it is |
|------|---------|------------|
| Round Pen Cup | `pen_cup` | Upright round cup for a fistful of pens, open top, optional single internal divider. |
| Angled Desk Block | `pen_block` | Rounded block with an array of blind bores drilled from the top; front row can be raked toward the user. |
| Ergonomic Grip Sleeve | `grip_enlarger` | A through-tube that slides over a thin pen barrel to fatten the grip (assistive aid), with unioned finger ridges. |

## Key parameters

- **Barrel Diameter** (`pen_dia`, default 9 mm) — the pen / pencil / stylus barrel.
  Ballpoint ≈ 8 mm, gel/marker ≈ 10–11 mm, #2 pencil ≈ 7 mm across the flats.
- **Slip-Fit Clearance** (`clearance`, default 1.2 mm) — added to each bore so the
  pen drops in and out; the drilled hole is `pen_dia + clearance`.
- **Wall Thickness** (`wall`, default 3 mm) — wall and floor.
- Cup: **Cup Diameter** (`cup_dia`), **Height** (`height`), **Internal Divider** (0/1).
- Block: **Bore Columns/Rows** (`cols`/`rows`), **Front-Row Rake** (`rake_deg`).
- Grip: **Sleeve Length** (`grip_len`), **Grip Diameter** (`grip_dia`).

## Design / printing notes

- The cup cavity and every block bore **open upward** — there are no sealed
  internal voids, so the mesh is a single watertight solid.
- The base rim is filleted **before** the cavity is cut (filleting a finished
  shell is what crashes the kernel).
- The grip sleeve is a through-tube (open at both ends), which is why adding a
  wider grip diameter never traps a cavity.
- Prints upright with no supports. PETG or recycled PLA both work; the grip
  sleeve is comfortable in a slightly flexible filament.

## CDG interface

- `pen_barrel_socket` — `geometry_type: socket`, `standard: "standard pen"`,
  driven by `pen_dia`, `clearance`, `wall`. Any object exposing a matching pen
  socket interoperates with this holder family.

## License

CERN-OHL-W-2.0 (CERN Open Hardware Licence, Weakly Reciprocal).

---

# Portabolígrafos / Lápiz Óptico y Agarre

Una estación de bolígrafos de escritorio dimensionada según el **diámetro real
del barril** de un instrumento de escritura, en tres formas distintas.

## Modos

| Modo | Id de pieza | Qué es |
|------|-------------|--------|
| Vaso Redondo | `pen_cup` | Vaso redondo vertical para un puñado de bolígrafos, tapa abierta, divisor interno opcional. |
| Bloque Inclinado | `pen_block` | Bloque redondeado con una matriz de orificios ciegos perforados desde arriba; la fila delantera puede inclinarse hacia el usuario. |
| Funda de Agarre | `grip_enlarger` | Un tubo pasante que se desliza sobre un bolígrafo delgado para engrosar el agarre (ayuda asistiva), con nervios para los dedos. |

## Parámetros clave

- **Diámetro del Barril** (`pen_dia`, predet. 9 mm) — el barril del bolígrafo /
  lápiz / lápiz óptico. Bolígrafo ≈ 8 mm, gel/marcador ≈ 10–11 mm, lápiz #2 ≈ 7 mm.
- **Holgura de Ajuste** (`clearance`, predet. 1.2 mm) — añadida a cada orificio.
- **Grosor de Pared** (`wall`, predet. 3 mm).

## Notas de diseño / impresión

- La cavidad del vaso y cada orificio del bloque **se abren hacia arriba**: no hay
  vacíos sellados, por lo que la malla es un único sólido estanco.
- El borde de la base se redondea **antes** de cortar la cavidad.
- La funda es un tubo pasante (abierto en ambos extremos).
- Se imprime en vertical sin soportes.

## Interfaz CDG

- `pen_barrel_socket` — `geometry_type: socket`, `standard: "standard pen"`,
  gobernado por `pen_dia`, `clearance`, `wall`.

## Licencia

CERN-OHL-W-2.0 (Licencia de Hardware Abierto del CERN, Débilmente Recíproca).
