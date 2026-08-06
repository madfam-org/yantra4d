# Window / Sash Lock Insert / Inserto de Seguro de Ventana

Small window-security inserts that live in the **sash channel** of a sliding or
double-hung window, generated with **CadQuery** (B-Rep): a **cantilever snap catch**
that clips into the channel, a **sash stop / vent limiter** that blocks the window
past a set opening, and a **friction wedge lock** that jams the sash shut.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

---

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cantilever Snap Catch** | `snap_catch` | A seating block with a cantilever snap arm: the arm protrudes into free air (so its flex clearance is the surrounding void — no trapped cavity) and a barb hooks over the channel lip. |
| **Sash Stop / Vent Limiter** | `sash_stop` | A channel-width block with a through pin/screw bore and a raised stop shoulder that blocks the sash from sliding past a set opening — a child-safety vent stop. |
| **Friction Wedge Lock** | `wedge_lock` | A tapered wedge that slides into the sash gap and jams the window shut, with a thumb tab and a lanyard hole. Thin at the tip, rising to full height at the tab. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Channel Fit | `channel_w` | 14.0 mm | Insert width to fit the sash channel — measure yours. |
| Channel Fit | `body_len` | 40.0 mm | Overall insert length. |
| Channel Fit | `body_h` | 12.0 mm | Insert height / channel depth. |
| Cantilever Snap | `arm_len` / `arm_t` | 22.0 / 2.4 mm | Cantilever arm length and thickness. |
| Cantilever Snap | `snap_clear` | 0.5 mm | Flex clearance each side of the arm vs the channel. |
| Cantilever Snap | `barb` | 1.2 mm | Hook engagement behind the channel lip. |
| Mounting | `pin_d` | 4.2 mm | Through pin/screw bore (stop + snap seat + wedge lanyard). |
| Wedge | `wedge_rise` | 6.0 mm | Taper rise from tip to full height. |

## Why these dimensions

Sash channels are **not standardized** — vinyl, aluminium and wood sliding windows
each differ — so the channel-fit dimensions are declared **`standard: "internal"`**
and left fully parametric to retune against your window. The nominal ~14 mm insert
width suits common sliding-window channels. The cantilever geometry follows
snap-fit practice: a thin arm (`arm_t`) so it flexes, a **lead-in ramp** on the
insertion (+Y) side, and a **square retention face** on the locking side, with
`snap_clear` of air each side so the beam does not bind on the channel.

## Watertightness — the snap-fit case

The delicate part is the cantilever. Rather than a slot cut into a block (which
risks a trapped void), the snap arm **cantilevers past the seating block's face
into open air** — so its flex clearance is the surrounding void itself, and there is
no enclosed pocket to seal. The arm overlaps into the seat (welds) and the barb hook
overlaps into the arm top (welds), so the whole part is **one manifold solid**. The
sash stop's shoulder is a block **unioned** into shared material with through-bores
only; the wedge is an extruded right-trapezoid profile (guaranteeing a single solid)
with a thumb tab unioned onto its tall end. Every hole is a **through-bore** that
vents to outside. Validated watertight with `body_count == 1` across all modes plus
extreme MAX and MIN parameter cases — the historical trap here (a severed hook or a
sealed flex slot) is avoided by construction.

## Presets

- **Standard Snap Catch** — the reference cantilever snap insert.
- **Child-Safety Vent Stop** — a sash stop that limits the opening.
- **Friction Wedge Lock** — a tapered jamming wedge.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Sash Channel + Catch** (`snap`, *internal*) — the cantilever snap fit, defined
    by `channel_w`, `arm_t`, `barb`.
  - **Sash Stop Pin** (`socket`, *internal*) — the stop's pin/screw bore, defined by
    `pin_d`.
- **Material awareness:** `tolerance_by_material` is declared — the cantilever's
  arm thickness and clearances should be tuned per filament, since flexural
  behaviour (and safe snap strain) differs sharply between PLA, PETG and TPU.
- **License:** CERN-OHL-W-2.0.

---

## Español

Pequeños insertos de seguridad para ventanas que viven en el **canal de la hoja** de
una ventana corrediza o de guillotina, generados con **CadQuery** (B-Rep): un
**enganche de resorte en voladizo**, un **tope / limitador de ventilación**, y una
**cuña de fricción**.

### Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Enganche de Resorte (Voladizo)** | `snap_catch` | Bloque de asiento con brazo de resorte en voladizo: el brazo sobresale al aire (su holgura de flexión es el vacío circundante — sin cavidad atrapada) y un diente engancha el labio del canal. |
| **Tope / Limitador de Ventilación** | `sash_stop` | Bloque del ancho del canal con perforación pasante y hombro de tope que impide que la hoja pase de una abertura fija — tope de seguridad infantil. |
| **Cuña de Fricción** | `wedge_lock` | Cuña ahusada que entra en el hueco de la hoja y traba la ventana, con pestaña y agujero para cordón. |

### Por qué estas dimensiones

Los canales de las hojas **no están estandarizados**, por lo que las dimensiones de
ajuste se declaran **`standard: "internal"`** y quedan paramétricas para reajustar a
su ventana. La geometría del voladizo sigue la práctica de encaje a presión: brazo
delgado (`arm_t`) para que flexione, **rampa de entrada** en el lado de inserción y
**cara recta de retención** en el de traba, con `snap_clear` de aire a cada lado.

### Estanqueidad — el caso del encaje a presión

En vez de una ranura cortada en un bloque (que arriesga un vacío atrapado), el brazo
**sobresale al aire libre** — su holgura de flexión es el propio vacío, sin bolsillo
sellado. El brazo se **une** al asiento y el diente al brazo, dando **un solo cuerpo
manifold**. Validado estanco con `body_count == 1` en todos los modos más casos
extremos MAX y MIN.

- **Dominio:** household
- **Licencia:** CERN-OHL-W-2.0.
