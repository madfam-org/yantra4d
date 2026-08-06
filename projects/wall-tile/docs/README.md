# Wall Tile

Interlocking decorative wall and acoustic tiles. Each square panel has a tongue-and-groove
interlock on its edges so tiles snap together edge-to-edge into a seamless field. Pick a
flat tile, a raised relief-pattern tile, or an acoustic diffuser tile.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Flat Tile | `flat_tile` | A plain interlocking panel (base for paint / wallpaper). |
| Relief Tile | `relief_tile` | A panel with a raised geometric relief pattern on its face. |
| Acoustic Tile | `acoustic_tile` | A panel carrying a varying-height diffuser field that scatters sound. |

## Key Parameters

- **Tile Size** — square edge length.
- **Base Thickness** — panel body behind the pattern.
- **Interlock Size / Fit** — tongue/groove dimension and snap clearance.
- **Relief Pattern** — grid, diagonal (checker), or concentric (relief tile).
- **Relief Height / Cells per Side** — pattern depth and subdivision.

## How It Builds (watertight & fast)

The panel is prismatic: a solid box with a **tongue** on the +X/+Y edges and a matching
**groove** cut into the -X/-Y edges, so any two tiles mate. Relief and acoustic fields are
built as a **single compound boolean** (all prisms fused/added in one operation) rather
than block-by-block, so even a 10×10 field renders fast and exports watertight. The
acoustic field uses a quadratic-residue-style height sequence for broadband diffusion.

## Printing Notes

Print flat, pattern-up. Tiles interlock dry; add a dab of adhesive or mount on a cleat for
walls. For acoustic use, a field of PLA diffusers scatters mid/high frequencies — pair
with soft backing for absorption. Tune the interlock fit to your printer for a firm snap.

## Hyperobject Profile

- **Domain:** household (décor / acoustics).
- **CDG interface:** `tile_interlock` (`profile`) — the tongue-and-groove edge that mates
  neighbouring tiles, standard `internal`, driven by `tile_size`, `interlock`, `fit`, `base_t`.
- **Material awareness:** tolerance-by-material (interlock fit tuned per filament).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** a tileable wall surface anyone can print in any quantity —
  decorative or sound-absorbing — turning bare walls into custom finishes and treated rooms.
