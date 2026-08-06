# Nameplate

A personalized nameplate or sign with embossed or debossed text. Type a name, pick a
form — a standing desk wedge, a wall plate, or a hanging door sign — and print. The plate
auto-sizes to the text and always exports watertight.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Desk Nameplate | `desk_nameplate` | A name slab on a triangular prop that stands and leans on a desk. |
| Wall Plate | `wall_plate` | A flat plate with the name and two keyhole mounting slots. |
| Door Sign | `door_sign` | A rounded plate with the name and a top hang slot for a hook. |

## Key Parameters

- **Name / Text** — the label to show (the plate scales to fit it).
- **Text Height** — cap height of the letters.
- **Text Style** — embossed (raised) or debossed (recessed).
- **Text Depth** — emboss height / deboss cut depth.
- **Plate Thickness / Border** — plate body and border around the text.
- **Style** — presentation style select (matches the mode).

## Text Robustness (always watertight)

Text is applied with CadQuery's `text()` and the boolean result is validated with
`.val().isValid()` — the keytag pattern. If the requested mode (emboss/deboss) yields an
invalid solid (some accented glyphs break a debossed cut), the code falls back to the other
mode, and finally to a blank but watertight plate. Accented and non-Latin names degrade to
a plain plate rather than crashing, so **every render is watertight** regardless of the
characters typed.

## Printing Notes

Print flat, text-up. For a two-colour name, print an embossed plate and swap filament at
the text layer (or paint the raised letters). The desk wedge stands on its own; the wall
plate takes two screws; the door sign hangs from the top slot on a hook or ribbon.

## Hyperobject Profile

- **Domain:** household (personalization / wayfinding).
- **CDG interface:** `text_plate` (`profile`) — the auto-sized text plate outline, standard
  `internal`, driven by `text`, `size`, `text_mode`, `text_depth`, `margin`.
- **Material awareness:** tolerance-by-material (emboss height tuned per filament).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** a named plate anyone can make in seconds for a desk, door, or room —
  personalization and wayfinding without ordering engraved signage.
