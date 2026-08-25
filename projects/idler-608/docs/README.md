# 608 Bearing Idler Pulley

A parametric idler generated with **CadQuery** (B-Rep) that presses onto a
standard **608** skate bearing (22 mm OD × 8 mm ID × 7 mm) and rides on an M8
shoulder bolt. The bearing carries the load; the printed part is only the running
surface and the guide flanges. The interface is the 22 mm press-fit seat and the
8 mm bore.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Bearing table

| Bearing | ID | OD | Width |
| :--- | :--- | :--- | :--- |
| 608 | 8 | 22 | 7 |
| 623 | 3 | 10 | 4 |
| 625 | 5 | 16 | 5 |
| 6900 | 10 | 22 | 6 |

The seat pocket bore = bearing OD (± `press_fit`); the axle bore = bearing ID
+ clearance and runs all the way through so nothing is trapped.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Flat-Belt Idler** | `flat_idler` | Smooth barrel with two guide flanges; 608 seat bored through. |
| **Round-Groove Idler** | `round_idler` | Central round/V groove for a round belt or cord. |
| **Shoulder Washer Stack** | `washer_stack` | Shoulder spacer + retaining flange washer that sandwich the 608 on the bolt. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bearing & Seat | `bearing` | 608 | Bearing designation → seat + bore. |
| Pulley | `od` | 30 mm | Running-surface diameter. |
| Pulley | `width` | 10 mm | Axial width (≥ bearing width + wall). |
| Pulley | `flange_h` | 2.5 mm | Guide-flange rim height. |
| Pulley | `flange_t` | 2.0 mm | Flange / washer thickness. |
| Pulley | `groove_dia` | 5.0 mm | Round-groove belt/cord diameter. |
| Bearing & Seat | `press_fit` | 0.0 mm | Seat fit adjust (−tightens / +loosens). |

## Presets

- **Standard 608 Idler** — the classic flat-belt idler on a 608.
- **Round-Cord Idler** — a round-groove idler for a drive cord or bungee.
- **608 Shoulder Washers** — the mounting hardware that captures the bearing.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **608 Press-Fit Seat** (`socket`, 608 bearing ISO 15 — 8×22×7) — defined by
    `bearing`, `press_fit`, `width`. Shares the 22 mm bearing seat with
    `linear-wheel` and `bearing-housing`.
- **Material awareness:** `tolerance_by_material` plus `press_fit` let the seat
  be tuned to the filament for a firm, rattle-free press.
- **Commons license:** CERN-OHL-W-2.0

---

# Polea Guía de Rodamiento 608

Una polea guía paramétrica generada con **CadQuery** (B-Rep) que se ajusta a
presión sobre un rodamiento **608** estándar (22 mm DE × 8 mm DI × 7 mm) y gira
sobre un tornillo hombro M8. El rodamiento soporta la carga; la pieza impresa es
solo la superficie de rodadura y las pestañas guía. La interfaz es el asiento a
presión de 22 mm y el barreno de 8 mm.

Parte del **Commons de Hiperobjetos de Yantra4D**. Visualizador y configurador
oficial: [Yantra4D](https://app.yantra4d.com).

## Tabla de rodamientos

| Rodamiento | DI | DE | Ancho |
| :--- | :--- | :--- | :--- |
| 608 | 8 | 22 | 7 |
| 623 | 3 | 10 | 4 |
| 625 | 5 | 16 | 5 |
| 6900 | 10 | 22 | 6 |

El asiento = DE del rodamiento (± `press_fit`); el barreno del eje = DI del
rodamiento + holgura y atraviesa todo para no atrapar vacíos.

## Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Polea de Correa Plana** | `flat_idler` | Barril liso con dos pestañas guía; asiento 608 barrenado. |
| **Polea de Ranura Redonda** | `round_idler` | Ranura redonda/V central para correa redonda o cuerda. |
| **Juego de Arandelas Hombro** | `washer_stack` | Espaciador hombro + arandela de retención que sujetan el 608 en el tornillo. |

## Parámetros

| Grupo | Parámetro | Predeterminado | Notas |
| :--- | :--- | :--- | :--- |
| Rodamiento y Asiento | `bearing` | 608 | Designación → asiento + barreno. |
| Polea | `od` | 30 mm | Diámetro de la superficie de rodadura. |
| Polea | `width` | 10 mm | Ancho axial (≥ ancho del rodamiento + pared). |
| Polea | `flange_h` | 2.5 mm | Altura del borde de la pestaña guía. |
| Polea | `flange_t` | 2.0 mm | Grosor de pestaña / arandela. |
| Polea | `groove_dia` | 5.0 mm | Diámetro de correa/cuerda redonda. |
| Rodamiento y Asiento | `press_fit` | 0.0 mm | Ajuste de asiento (−aprieta / +afloja). |

## Presets

- **Polea 608 Estándar** — la polea de correa plana clásica sobre un 608.
- **Polea de Cuerda Redonda** — una polea de ranura redonda para cuerda o
  elástico.
- **Arandelas Hombro 608** — la ferretería de montaje que captura el rodamiento.

## Perfil de Hiperobjeto

- **Dominio:** industrial
- **Interfaces CDG:**
  - **Asiento a Presión 608** (`socket`, rodamiento 608 ISO 15 — 8×22×7) —
    definido por `bearing`, `press_fit`, `width`. Comparte el asiento de 22 mm
    con `linear-wheel` y `bearing-housing`.
- **Conciencia de material:** `tolerance_by_material` y `press_fit` permiten
  ajustar el asiento al filamento para un ajuste firme y sin holgura.
- **Licencia commons:** CERN-OHL-W-2.0
