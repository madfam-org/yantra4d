# Whiteboard / Marker Tray

A whiteboard marker tray / eraser holder **parametric on the dry-erase marker
body diameter**, with optional disc-magnet pockets for mounting to a steel board.
Three distinct forms. CadQuery-first parametric hyperobject cartridge.

## Modes

| Mode | Part id | What it is |
|------|---------|------------|
| Rail Marker Trough | `marker_tray` | A horizontal trough holding markers lying down, with half-round cradles so they don't roll; magnet pockets on the back. |
| Eraser + Marker Block | `eraser_holder` | A block with a rectangular eraser pocket plus a couple of upright marker bores; magnet pockets on the back. |
| Upright Marker Cup | `marker_cup` | An upright cup with a row of vertical marker bores on a back plate carrying magnet pockets. |

## Key parameters

- **Marker Body Ø** (`marker_dia`, default **16 mm**) — a chisel-tip dry-erase
  marker (e.g. Expo) is ~16 mm; fine-tip ~12 mm, jumbo ~22 mm. The bore is
  `marker_dia + clearance`.
- **Marker Positions** (`markers`), **Marker Clearance** (`clearance`),
  **Height** (`tray_h`), **Wall Thickness** (`wall`).
- Magnet mount: **Magnet Pockets** (`magnets`, 0 = none), **Magnet Ø**
  (`magnet_dia`, default 10 mm), **Magnet Pocket Depth** (`magnet_t`, default 2 mm).
- Eraser: **Eraser Pocket Width** (`eraser_w`, default 58 mm — a standard eraser
  is ~55–60 mm), **Eraser Pocket Depth** (`eraser_d`).

## Design / printing notes

- Every pocket and bore **opens to a face** — the trough channel and marker bores
  open upward; the magnet pockets open out of the **back** face. Because each
  cavity is open to a surface, the model is a single watertight solid with no
  trapped void.
- Block edges are **filleted before** any pocket is cut.
- The anti-roll cradles are half-round troughs **cut** into the channel floor
  (cut into a solid → always watertight).
- Keep `magnet_t < wall` so the magnet pocket does not break through to the front
  (a warning constraint flags this). Prints flat with the openings facing up; the
  back face (with magnet pockets) prints against the bed for a clean magnet seat.
- Glue disc magnets into the back pockets to mount on a steel whiteboard frame.

## CDG interfaces

- `marker_pocket` — `geometry_type: pocket`, `standard: "dry-erase marker"`.
- `disc_magnet_mount` — `geometry_type: socket`, disc-magnet seats on the back.

## License

CERN-OHL-W-2.0 (CERN Open Hardware Licence, Weakly Reciprocal).

---

# Bandeja para Pizarra / Marcadores

Una bandeja para marcadores de pizarra / soporte de borrador **parametrizado según
el diámetro del cuerpo del marcador**, con bolsillos opcionales para imanes de
disco para montarse en una pizarra de acero. Tres formas distintas.

## Modos

| Modo | Id de pieza | Qué es |
|------|-------------|--------|
| Canal de Riel | `marker_tray` | Un canal horizontal que sostiene marcadores acostados, con cunas semicirculares antideslizantes; bolsillos para imanes atrás. |
| Bloque de Borrador | `eraser_holder` | Un bloque con un bolsillo rectangular para borrador más orificios verticales para marcadores; bolsillos para imanes atrás. |
| Vaso Vertical | `marker_cup` | Un vaso vertical con una fila de orificios para marcadores sobre una placa trasera con bolsillos para imanes. |

## Parámetros clave

- **Ø del Cuerpo del Marcador** (`marker_dia`, predet. **16 mm**) — un marcador de
  punta biselada (Expo) es ~16 mm; punta fina ~12 mm, jumbo ~22 mm.
- **Posiciones** (`markers`), **Holgura** (`clearance`), **Altura** (`tray_h`),
  **Grosor** (`wall`).
- Imanes: **Bolsillos** (`magnets`), **Ø del Imán** (`magnet_dia`), **Profundidad**
  (`magnet_t`).

## Notas de diseño / impresión

- Cada bolsillo y orificio **se abre a una cara** — el canal y los orificios hacia
  arriba; los bolsillos de imán hacia la cara **trasera**. Al estar abierta cada
  cavidad, el modelo es un único sólido estanco sin vacíos atrapados.
- Los bordes se **redondean antes** de cortar cualquier bolsillo.
- Las cunas antideslizantes son surcos semicirculares **cortados** en el piso.
- Mantén `magnet_t < wall` para que el bolsillo del imán no atraviese el frente.

## Interfaces CDG

- `marker_pocket` — `geometry_type: pocket`, `standard: "dry-erase marker"`.
- `disc_magnet_mount` — `geometry_type: socket`, asiento de imán de disco atrás.

## Licencia

CERN-OHL-W-2.0 (Licencia de Hardware Abierto del CERN, Débilmente Recíproca).
