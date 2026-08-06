# Faucet Aerator Adapter

Adapters that bridge a standard faucet-aerator thread to something else — a hose barb or
the opposite aerator gender. Built on the real **M22 x 1** (male, 22.0 mm) and **M24 x 1**
(female, 24.0 mm) aerator standards, so every part mates the companion
[`aerator-cache`](../../aerator-cache/) cartridge and any real tap aerator.

## Modes

| Mode | What it makes |
|------|---------------|
| **Hose Barb Adapter** | A female aerator collar that screws onto a male tap spout, reducing to a barbed spout you push vinyl hose onto. Water runs straight through. |
| **Gender Changer** | A double-ended coupler: female aerator thread at one end, male aerator spigot at the other — convert an M24 female tap to an M22 male fitting (or vice-versa). |
| **Aerator Cap** | A knurled cap with an internal aerator thread and a drilled screen grid — a printable aerator / flow-straightener cap. |

## Key parameters

- **Tap-Side Aerator Thread** — M24 x 1 (female) or M22 x 1 (male).
- **Far-Side Aerator Thread** — the opposite end of the gender changer.
- **Hose Inner Diameter (mm)** — the vinyl tubing the barb pushes into (13 mm = 1/2").
- **Thread Fit Clearance (mm)** — per-side slop so printed threads mate without a tap; 0.3–0.4 mm suits most FDM printers.
- **Thread Collar Height (mm)** — taller gives more thread engagement (turn count is capped for print reliability).

## How the threads print

Threads are modelled as helical ribs fused into the wall as positive material — not cut
grooves — so each part leaves the bed as a single watertight body. Turn counts are capped
at a half-integer ceiling (integer turn counts degenerate the swept helix and very tall
threads tessellate poorly), which costs nothing physically because a real aerator only
engages a couple of turns.

Print collar-up with no supports. Test the fit on a scrap first and nudge **Thread Fit
Clearance** if it binds or leaks.

**Food / potable water contact:** if the adapter carries drinking water, choose a filament
rated for potable contact and be aware that FDM layer lines can harbour biofilm — the
responsibility for food-safe / potable material selection and maintenance is the maker's.

---

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** `aerator_thread` — geometry type **thread**, standard **M22x1 / M24x1 aerator**.
- **Compatible with:** [`aerator-cache`](../../aerator-cache/) — shares the M22/M24 aerator threads, so housings, caches and adapters interchange.
- **License:** CERN-OHL-W-2.0

This cartridge grows the **aerator-m22-m24** family of the Yantra4D Hyperobjects Commons.

---

# Adaptador de Aireador de Grifo (Español)

Adaptadores que unen una rosca estándar de aireador de grifo con otra cosa — una espiga
para manguera o el género de aireador opuesto. Construidos sobre los estándares reales
**M22 x 1** (macho, 22.0 mm) y **M24 x 1** (hembra, 24.0 mm), así cada pieza encaja con el
cartucho complementario [`aerator-cache`](../../aerator-cache/) y cualquier aireador real.

## Modos

| Modo | Qué genera |
|------|------------|
| **Adaptador de Espiga** | Un collar hembra que se enrosca en un caño macho, reduciendo a una espiga para empujar manguera de vinilo. El agua pasa directo. |
| **Cambia-Género** | Un acople de doble extremo: rosca hembra en un extremo, espiga macho en el otro — convierte un grifo M24 hembra a un accesorio M22 macho (o viceversa). |
| **Tapa de Aireador** | Una tapa moleteada con rosca interna y una rejilla de orificios — una tapa aireadora / rectificadora de flujo imprimible. |

## Parámetros clave

- **Rosca de Aireador del Grifo** — M24 x 1 (hembra) o M22 x 1 (macho).
- **Rosca del Otro Extremo** — el extremo opuesto del cambia-género.
- **Diámetro Interior de Manguera (mm)** — el tubo de vinilo donde entra la espiga (13 mm = 1/2").
- **Holgura de Ajuste de Rosca (mm)** — holgura por lado para que las roscas encajen sin macho de roscar; 0.3–0.4 mm sirve para la mayoría de impresoras FDM.
- **Altura del Collar Roscado (mm)** — más alto da más agarre (las vueltas se limitan por fiabilidad de impresión).

## Notas de impresión

Las roscas son nervaduras helicoidales fusionadas a la pared como material positivo — no
ranuras cortadas — así cada pieza sale como un solo cuerpo hermético. Imprime con el
collar hacia arriba sin soportes. Prueba el ajuste en un descarte y ajusta la holgura si
se traba o gotea.

**Contacto con agua potable:** si el adaptador conduce agua potable, elige un filamento
apto para contacto potable y ten en cuenta que las líneas de capa FDM pueden albergar
biopelícula — la responsabilidad de elegir material apto y su mantenimiento es del fabricante.

## Perfil de Hiperobjeto

- **Dominio:** hogar
- **Interfaz CDG:** `aerator_thread` — tipo **thread**, estándar **M22x1 / M24x1 aerator**.
- **Compatible con:** [`aerator-cache`](../../aerator-cache/).
- **Licencia:** CERN-OHL-W-2.0
