# Parametric Vase

A generative vase whose silhouette is a polar radius function extruded, optionally
twisting as it rises. Pick a profile family — round, faceted N-gon, lobed/twisted, or
superformula — and dial base diameter, height, wall, twist, and lobe count.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Vase | `vase` | The chosen profile family, twisting only if the profile is "twisted". |
| Twisted Vase | `twisted_vase` | The lobed/superformula profile spun about Z as it rises (a spiral). |
| Faceted Vase | `faceted_vase` | A crisp N-gon prism vessel with flat panels. |

## Key Parameters

- **Profile Family** — round/lobed, faceted (N-gon), twisted, or superformula.
- **Base Diameter / Height** — overall size.
- **Wall / Floor Thickness** — vessel walls (1.6–2 mm spiralizes) and closed floor.
- **Twist** — total spin from base to rim.
- **Lobes / Facets** — lobe count (round) or side count (faceted).
- **Lobe Amplitude** — how pronounced the lobes are.

## How It Builds (and stays watertight & fast)

The silhouette is a polar function `r(θ)` sampled to a closed polyline. The wall is an
**annular cross-section** (outer wire + inward-offset inner wire on one workplane) so a
single extrude produces the shell with no boolean between two lofted prisms. A twisted
vessel **lofts** through a few rotated annular sections — OCC's `twistExtrude` is far too
slow, so it is deliberately avoided. A short full-profile floor disk is fused on to close
the bottom (holds water). Every profile family and the extreme preset export watertight in
under 10 s. Print vase-mode (single-wall spiralize) for the smoothest surface.

## Hyperobject Profile

- **Domain:** household (décor).
- **CDG interface:** `parametric_profile` (`surface`) — the generative polar silhouette,
  standard `internal`, driven by `profile`, `base_dia`, `lobes`, `lobe_amp`, `twist`.
- **Material awareness:** tolerance-by-material (wall/floor tuned per filament; spiralize on TPU/PLA).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** on-demand décor made to fit a space and taste, spiralize-printable
  in one wall with no supports — endless unique vessels from one generative model.
