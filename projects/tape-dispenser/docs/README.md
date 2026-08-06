# Label / Tape Dispenser

A tape / label-roll dispenser **parametric on the roll's core inner diameter**,
in three distinct forms. CadQuery-first parametric hyperobject cartridge.

## Modes

| Mode | Part id | What it is |
|------|---------|------------|
| Free-Spin Roll Holder | `roll_holder` | Weighted base with two side walls and a horizontal spindle the roll spins on. |
| Desk Tear Dispenser | `desk_dispenser` | The holder plus a forward ramp ending in a saw-tooth tear edge for clean one-handed tearing. |
| Wall Spindle Bracket | `wall_spindle` | A screw plate with a single cantilevered spindle the roll slides onto from the open end. |

## Key parameters

- **Roll Core Inner Ø** (`core_dia`, default **25.4 mm = 1 inch**) — the roll
  core. Office / desktop tape is a 1-inch core; big packing tape and many label
  rolls use a **3-inch = 76.2 mm** core. The spindle is `core_dia − clearance`.
- **Spindle Clearance** (`clearance`, default 0.8 mm) — free-spin gap.
- **Roll Width** (`roll_w`), **Roll Outer Ø** (`roll_od`, sets wall height so a
  full roll clears the base), **Wall Thickness** (`wall`).
- Desk: **Tear Ramp Length** (`blade_ramp`), **Tear Teeth** (`teeth`).
- Wall: **Screw Clearance Ø** (`screw_dia`).

## Design / printing notes

- The roll rides on the **outside** of a solid spindle (the socket is the
  spindle's outer surface), so there is no bore to trap a void.
- The spindle is buried into both side walls with a full-wall overlap on each
  end — never a tangent seam that would leave two bodies.
- The tear teeth are **cut** as upward-open V-notches into a solid lip (the teeth
  are the ridges left between the notches). Cutting into a solid can never leave a
  floating tooth body, which unioning many small tangent prisms can.
- The desk dispenser prints flat on the base. The wall bracket prints plate-down.

## CDG interface

- `roll_core_socket` — `geometry_type: socket`, `standard: "tape core"`, driven
  by `core_dia`, `clearance`, `roll_w`. Any roll matching the core standard fits.

## License

CERN-OHL-W-2.0 (CERN Open Hardware Licence, Weakly Reciprocal).

---

# Dispensador de Cinta / Etiquetas

Un dispensador de cinta / rollos de etiquetas **parametrizado según el diámetro
interior del núcleo del rollo**, en tres formas distintas.

## Modos

| Modo | Id de pieza | Qué es |
|------|-------------|--------|
| Soporte Giratorio | `roll_holder` | Base con dos paredes laterales y un eje horizontal sobre el que gira el rollo. |
| Dispensador de Escritorio | `desk_dispenser` | El soporte más una rampa que termina en un borde dentado para cortar con una mano. |
| Soporte de Eje de Pared | `wall_spindle` | Una placa con tornillos y un solo eje en voladizo donde el rollo se desliza. |

## Parámetros clave

- **Ø Interior del Núcleo** (`core_dia`, predet. **25.4 mm = 1 pulgada**) — el
  núcleo del rollo. La cinta de oficina es de 1 pulgada; la cinta de embalar
  grande y muchos rollos de etiquetas usan un núcleo de **3 pulgadas = 76.2 mm**.
  El eje es `core_dia − clearance`.
- **Holgura del Eje** (`clearance`, predet. 0.8 mm).
- **Ancho del Rollo** (`roll_w`), **Ø Exterior** (`roll_od`), **Grosor** (`wall`).

## Notas de diseño / impresión

- El rollo gira sobre la **parte exterior** de un eje sólido (el alojamiento es la
  superficie exterior del eje): no hay perforación que atrape un vacío.
- El eje se hunde en ambas paredes laterales con solapamiento completo.
- Los dientes de corte se **cortan** como muescas en V abiertas hacia arriba en un
  labio sólido (los dientes son las crestas entre las muescas).
- El dispensador se imprime plano sobre la base; el soporte de pared con la placa
  hacia abajo.

## Interfaz CDG

- `roll_core_socket` — `geometry_type: socket`, `standard: "tape core"`,
  gobernado por `core_dia`, `clearance`, `roll_w`.

## Licencia

CERN-OHL-W-2.0 (Licencia de Hardware Abierto del CERN, Débilmente Recíproca).
