# Key Organizer / Bit Holder / Organizador de Llaves

A Swiss-army-style **key organizer**, generated with **CadQuery** (B-Rep): two side
plates and a pivot bolt clamp a stack of house keys so they fan out like a pocket
knife. Build the **side plate** (key-bow pocket + counterbored pivot), the **spacer**
that sets the fan gap, or a **1/4 in hex-bit-holder** variant. Pockets sized to
standard house-key blanks (**Kwikset KW1 / Schlage SC1**).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

---

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Organizer Side Plate** | `organizer_body` | A side plate: counterbored pivot bolt hole at one end, a recessed key-bow pocket that captures the fanned keys, and a slotted tension tail for a thumb grip or lanyard. |
| **Inter-Key Spacer** | `spacer` | A thinner, shorter plate with the pivot hole and a raised rib that sets the fan gap between stacked keys. |
| **Hex-Bit Holder** | `bit_holder` | The same footprint carrying a row of **1/4 in (6.35 mm A/F)** hex sockets opening to the top face, plus the pivot bore so it stacks in the same organizer. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Plate Body | `body_len` | 62.0 mm | Length along the keys (~57 mm house key + bow). |
| Plate Body | `body_w` | 22.0 mm | Width across the stack. |
| Plate Body | `plate_t` | 4.0 mm | Thickness (deeper = deeper hex sockets). |
| Pivot Bolt | `pivot_d` / `pivot_head_d` | 5.2 / 9.5 mm | M5 bolt clearance and head counterbore. |
| Key Stack | `key_blade_w` | 8.5 mm | KW1 blade width (0.335 in). |
| Key Stack | `key_blade_t` | 2.2 mm | SC1 blade thickness (clears KW1 too). |
| Key Stack | `key_count` | 4 | Keys the bow pocket fans (lengthens pocket). |
| Hex Bits | `hex_af` / `bit_count` | 6.35 mm / 4 | 1/4 in socket across-flats and count. |

## Why these dimensions

The pockets track real house-key blanks: **Kwikset KW1** has a **0.335 in (8.5 mm)**
blade at ~2.0 mm thick, and **Schlage SC1** is ~2.2 mm — the bow pocket is cut to
the thicker SC1 so both blanks clear. Key organizers commonly pivot on an **M5**
bolt, so the pivot bore defaults to 5.2 mm with a head counterbore. The bit holder
uses **6.35 mm (1/4 in) across-flats** hex sockets — the universal driver-bit size.
`polygon(6, D)` takes the across-corners diameter, so the socket diameter is
`hex_af / cos(30°)` to hit the target across-flats.

## Watertightness

Every part is a **filleted flat blank** (fillets applied to the clean blank before
any cut). The pivot bore, tension-tail slot, key-bow pocket and hex sockets are all
**through- or open-to-a-face** cuts that vent to outside — no sealed cavity. The
pivot counterbore is a stepped bore open to the top face; the spacer's gap-setting
rib is a bar **unioned** into shared material (overlap, not tangent). Hex sockets
are polygon prisms cut down from the top face. Validated watertight with
`body_count == 1` across all modes plus an extreme thick-plate / many-socket case.

## Presets

- **4-Key EDC Organizer** — the reference side plate for a four-key fan.
- **Standard Spacer** — the matching inter-key spacer.
- **1/4 in Bit Holder** — a thick plate with four hex-bit sockets.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Key Blade Stack + Pivot** (`pocket`, *standard key (Kwikset KW1 / Schlage
    SC1)*) — the key-bow pocket and pivot, defined by `key_blade_w`, `key_blade_t`,
    `pivot_d`.
  - **1/4 in Hex Bit Socket** (`socket`, *1/4 in hex driver bit, 6.35 mm A/F*) — the
    bit sockets, defined by `hex_af`.
- **Material awareness:** `tolerance_by_material` and `recycled_material_toggle`
  are declared — the key pocket and hex sockets should grow slightly for stiff
  filaments so blades and bits still seat.
- **License:** CERN-OHL-W-2.0.

---

## Español

Un **organizador de llaves** estilo navaja suiza, generado con **CadQuery** (B-Rep):
dos placas laterales y un perno pivote sujetan una pila de llaves para que se abran
en abanico. Bolsillos dimensionados a llaves de casa estándar (**Kwikset KW1 /
Schlage SC1**).

### Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Placa Lateral** | `organizer_body` | Placa con avellanado del pivote, bolsillo para el paletón y cola ranurada para asir o cordón. |
| **Separador** | `spacer` | Placa más fina y corta con el agujero del pivote y una nervadura que fija el espacio del abanico. |
| **Portabrocas** | `bit_holder` | El mismo perfil con una fila de alojamientos hexagonales de **1/4 in (6.35 mm)** abiertos a la cara superior. |

### Por qué estas dimensiones

Los bolsillos siguen llaves reales: **Kwikset KW1** tiene paletón de **0.335 in
(8.5 mm)** a ~2.0 mm; **Schlage SC1** es ~2.2 mm — el bolsillo libera el SC1 más
grueso. El pivote usa un perno **M5**. El portabrocas usa alojamientos de **6.35 mm
(1/4 in) entre caras**.

### Estanqueidad

Cada pieza es un **bloque plano con filetes** aplicados antes de cortar. El pivote,
la cola, el bolsillo y los alojamientos hexagonales ventilan a una cara — sin
cavidad sellada. La nervadura del separador se **une** en material compartido.
Validado estanco con `body_count == 1` en todos los modos más un caso extremo.

- **Dominio:** household
- **Licencia:** CERN-OHL-W-2.0.
