# Lithophane Frame

Frames and lamp bodies that hold a printed lithophane panel — a thin relief that reveals
an image when backlit. The frame has a slot the panel drops into and a light provision
behind it. Sized by the panel width and height so any lithophane fits.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Desk Frame | `desk_frame` | A standing frame with a rear slot and a fold-back kick foot. |
| Tea-Light Lamp | `lamp_body` | A lamp box: lit face, side wings, and a vented base for a light. |
| Hanging Frame | `hanging_frame` | A slim frame with a slot and a top hang hole for a window. |

## Key Parameters

- **Panel Width / Height / Thickness** — the lithophane the frame is built around.
- **Slot Fit** — slot oversize so the panel drops in.
- **Frame Border / Depth** — border width and front-to-back body depth.
- **Front Reveal** — lip that overlaps the panel edge to retain it.
- **Style** — presentation style select (matches the mode).

## Printing Notes

Print the frame in an opaque filament so light only comes through the lithophane. The
panel drops into the rear slot behind the front reveal; add a dab of glue or a printed
back clip if you want it captive. For the lamp, use a cool LED tea-light — never a real
flame near PLA. Print flat, aperture-face down, for a clean front.

## Hyperobject Profile

- **Domain:** household (décor / lighting).
- **CDG interface:** `lithophane_panel_slot` (`pocket`) — the rear slot + front reveal that
  holds the panel, standard `internal`, driven by `panel_w`, `panel_h`, `panel_t`, `slot_fit`, `reveal`.
- **Material awareness:** tolerance-by-material (slot fit tuned per filament; opaque for contrast).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** turns a printed photo into a lit keepsake, lamp, or suncatcher — a
  frame anyone can size to their own lithophane, keeping memories tangible without a photo lab.
