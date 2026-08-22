# Button Hook Aid

A printable **one-hand buttoning aid** — a generous built-up handle and a flat rigid hook
loop. Generated with **CadQuery** (B-Rep).

The loop goes through the buttonhole from the far side, hooks the button, and is pulled
back; the button follows through the hole. It is the standard occupational-therapy answer
for arthritis, hemiparesis, tremor, limited fine motor control, or one usable hand, and
shirt cuffs are the reason most people meet one.

Two sizing facts drive the design.

**The handle wants to be big, not small.** Grip strength lost to arthritis is recovered by
*increasing* grip circumference — a built-up handle runs 28–38 mm across, against the 8–10 mm
pen-thin freebie that nobody with a painful hand can actually hold. `grip_w` and `grip_t`
together set that circumference, and `finger_scallops` gives fingers with limited motion
something to find without having to close on it.

**The loop is thin one way and deep the other.** `loop_t` is what has to pass a buttonhole
alongside the button, so it stays near 1.8 mm; `loop_depth` runs in the pull direction,
where the load is, so the loop does not fold. `loop_dia` is the button it must encircle:
shirt 11 mm (18 ligne), jacket 20 mm (32 ligne), coat 25 mm.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Buttoning Aid** | `aid` | One aid, printed flat as a single piece. |
| **Aid Pair** | `pair` | Two aids laid head-to-toe on the plate — the usual issue is a pair, one for the shirt and one for the coat. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Grip | `grip_len` | 105.0 mm | 50–200 | Handle length; 100–120 mm lets all four fingers wrap. |
| Grip | `grip_w` | 32.0 mm | 18–60 | Width across the palm. Built-up handles run 28–38 mm. |
| Grip | `grip_t` | 18.0 mm | 8–40 | Handle thickness; with the width this sets grip circumference. |
| Grip | `finger_scallops` | 3 | 0–6 | Scallops on both long sides. Zero gives a plain handle. |
| Hook Loop | `loop_dia` | 13.0 mm | 6–40 | Button the loop must encircle; the loop is cut 1.2 mm larger all round. |
| Hook Loop | `loop_t` | 1.8 mm | 1.0–4.0 | Loop thickness in the buttonhole plane — keep thin. |
| Hook Loop | `loop_depth` | 6.0 mm | 3–14 | Loop and neck depth in the pull direction — the load-bearing dimension. |
| Hook Loop | `neck_len` | 26.0 mm | 8–80 | Blade between handle and loop. Long necks reach a collar button. |

## Print notes

Print **flat on the plate, handle face down** — the entire aid is one plane of material with
flat top and bottom faces, so nothing overhangs and no supports are needed anywhere. That is
deliberate: an assistive device that requires support removal is one a person with limited
hand function cannot finish making.

The **loop is the failure point**. Print it with the loop's long axis in the build plane so
the layer lines run around the loop rather than across the wire; a loop whose layers run
across the wire delaminates the first time a coat button resists.

**PETG** at 0.2 mm layers, 4 perimeters, 40 % infill for the loop's strength. Nylon or
PA-CF is better if the aid will be used daily for years. PLA is acceptable for a trial fit
but will snap at the neck. The handle can be printed at 15 % infill without weakening
anything — the load path never enters it.

If the loop will not pass the buttonhole, reduce `loop_t` before reducing `loop_dia`: the
loop must still clear the button.

Every mode exports watertight; the `pair` mode returns an assembly of two separate aids, not
a fused body.

## Hyperobject Profile

Domain `wearable`. Two CDG interfaces:

- **`button_capture`** (`custom`, parameters `loop_dia`, `loop_t`, `loop_depth`) — the open
  loop that captures a button and passes a buttonhole. It is a transient, point-fixed
  engagement with a garment feature, not a sewn edge or a fastener socket, so `custom`.
- **`hand_grip`** (`profile`, parameters `grip_w`, `grip_t`, `grip_len`,
  `finger_scallops`) — the grip section, the dimension an occupational-therapy fitting
  speaks in.

## Fashion Cabinet bridge

Expected FC consumers: any FC garment carrying a **button placket** — the **dress shirt**,
**cardigan**, **coat** and **blouse** — plus the **button** and **buttonhole** notions,
and any FC garment flagged as adaptive dressing.

The handshake is on the button, not on the garment: FC's button notion knows the button
diameter (ligne size) and the buttonhole notion knows the finished hole length. Those two
numbers size the loop — the loop must clear the button and still pass the hole.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "button-hook-aid",
  "linked": true,
  "params_map": {
    "loop_dia": "button_diameter_mm",
    "loop_t": "min(1.8, buttonhole_length_mm * 0.12)",
    "loop_depth": "6.0",
    "neck_len": "26.0",
    "grip_w": "wearer_grip_width_mm",
    "grip_t": "wearer_grip_thickness_mm",
    "grip_len": "105.0",
    "finger_scallops": "3"
  }
}
```

The **`button_capture`** interface is what FC reads: a change to the garment's button ligne
resizes the loop, so an FC coat with 32-ligne buttons and an FC shirt with 18-ligne buttons
each get an aid that actually works on them. The sibling **`zipper-loop-aid`** cartridge
covers the zipper-pull equivalent of the same accessibility problem.

`CERN-OHL-W-2.0`.
