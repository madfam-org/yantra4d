# Padlock Hasp & Shackle Guard / Hasp y Guardián de Arco

The hardware that turns a padlock into a door or lid latch, generated with
**CadQuery** (B-Rep): a hinged **hasp strap**, the **staple loop** its slot drops
over, and a **shackle guard** shroud that shields the padlock shackle from
bolt-cutters. Modelled on the **4 in (100 mm) safety-pattern hasp** family.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

---

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Safety Hasp Strap** | `safety_hasp` | The swinging strap: a hinge barrel at one end, a staple slot at the other, and two countersunk screws behind the hinge — covered by the leaf when closed (the *safety* pattern). |
| **Staple Loop** | `staple` | The loop the hasp slot drops over: a raised loop bar on a bolt-down base with a window the padlock shackle passes through, and two fixing screws. |
| **Shackle Guard Shroud** | `shackle_guard` | A U-shaped shroud walling three sides of the padlock so bolt-cutters cannot reach the shackle, with a shackle-Ø slot in the front lip and a four-screw base. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Strap / Base | `strap_len` | 100.0 mm | Strap length (4 in safety hasp). |
| Strap / Base | `strap_w` | 38.0 mm | Strap and base width. |
| Strap / Base | `plate_t` | 4.0 mm | Plate thickness. |
| Shackle & Staple | `shackle_d` | 9.0 mm | Padlock shackle Ø (40–50 mm padlock). |
| Shackle & Staple | `staple_bar` | 8.0 mm | Staple loop bar thickness. |
| Fixing Screws | `screw_d` / `screw_head_d` | 4.2 / 8.4 mm | No.8/M4 shank and countersink. |
| Hinge | `hinge_d` / `pin_d` | 8.0 / 3.2 mm | Hinge barrel Ø and pin bore (`safety_hasp`). |

## Why these dimensions

The **4 in (100 mm) safety-pattern hasp** is the family this cartridge tracks: a
~100 × 38 mm strap in ~4 mm plate, No.8/M4 fixing screws, and a staple loop whose
bar is ~8 mm. The shackle opening is sized to a typical **8–10 mm** padlock shackle.
Because there is no dimensional standard body for these (unlike a strike bore), the
shackle/staple interface is declared **`standard: "internal"`** while the screw
pattern cites the 4 in safety-pattern family.

## Watertightness

Straps and bases are **filleted flat blanks** (fillets applied to the clean blank
before any cut). The hinge barrel and staple loop are **unioned** from overlapping
solids into shared material — never tangent, so no zero-volume seams. Every hole —
screw bores with countersinks, the hinge pin bore, the staple window, the shackle
slot — is a **through- or open-to-a-face** cut that vents to outside, so no sealed
cavity forms. The staple loop is built torus-free: a bar bridged over the base with
an **obround window cut through it** (the window opens to two faces). Validated
watertight with `body_count == 1` across all modes plus an extreme oversize case;
the negative Euler numbers confirm the through-features are real handles, not
surface dimples.

## Presets

- **4 in Safety Hasp** — the reference safety-pattern strap at spec.
- **Standard Staple Loop** — the matching staple at spec.
- **Heavy Shackle Guard** — a wider, thicker guard for a larger padlock.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Shackle Ø + Staple** (`bolt_pattern`, *internal*) — the shackle opening and
    staple bar, defined by `shackle_d`, `staple_bar`.
  - **Hasp Fixing Pattern** (`bolt_pattern`, *4 in safety-pattern hasp*) — the
    screw footprint, defined by `strap_w`, `screw_d`.
- **Material awareness:** `tolerance_by_material` and `recycled_material_toggle`
  are declared — the staple window and shackle slot should grow slightly for stiff
  filaments so the printed hasp still clears the real shackle.
- **License:** CERN-OHL-W-2.0.

---

## Español

El herraje que convierte un candado en un pestillo, generado con **CadQuery**
(B-Rep): una **portezuela** con bisagra, el **grillete** por donde cae su ranura, y
un **guardián de arco** que protege el arco del candado de las cizallas. Basado en la
familia de hasp de patrón de seguridad de **4 in (100 mm)**.

### Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Portezuela de Seguridad** | `safety_hasp` | La portezuela batiente: barril de bisagra en un extremo, ranura para el grillete en el otro, y dos tornillos ocultos tras la bisagra al cerrar. |
| **Grillete (Staple)** | `staple` | El grillete por donde cae la ranura: barra elevada sobre una base atornillable con ventana para el arco del candado. |
| **Guardián de Arco** | `shackle_guard` | Un guardián en U que rodea tres lados del candado para que las cizallas no alcancen el arco, con ranura para el arco y base de cuatro tornillos. |

### Por qué estas dimensiones

El **hasp de patrón de seguridad de 4 in (100 mm)** es la familia de referencia:
portezuela de ~100 × 38 mm en placa de ~4 mm, tornillos No.8/M4, y grillete de barra
de ~8 mm. La apertura del arco se dimensiona a un candado típico de **8–10 mm**. Como
no hay un cuerpo estándar dimensional, la interfaz arco/grillete se declara
**`standard: "internal"`**.

### Estanqueidad

Portezuelas y bases son **bloques planos con filetes** aplicados antes de cortar. El
barril y el grillete se **unen** de sólidos superpuestos. Todo agujero ventila a una
cara — sin cavidad sellada. El grillete es libre de toroide: una barra puenteada con
una **ventana obround cortada a través**. Validado estanco con `body_count == 1` en
todos los modos más un caso extremo.

- **Dominio:** infrastructure
- **Licencia:** CERN-OHL-W-2.0.
