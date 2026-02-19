# Text Relief Generator

Generator for plaques, tags, and signs with embossed text

*Generador de placas, etiquetas y letreros con texto en relieve*

**Version**: 0.1.0  
**Slug**: `relief`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `plaque` | Plaque | `plaque.scad` | plaque |
| `tag` | Tag | `tag.scad` | tag |
| `sign` | Sign | `sign.scad` | sign |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `message` | text | Hello |  | Text to emboss |
| `font_size` | slider | 12 | 5–30 | Size of the text |
| `text_depth` | slider | 1.5 | 0.5–5 (step 0.5) | Extrusion height of text |
| `base_width` | slider | 80 | 40–200 (step 5) | Width of the base |
| `base_height` | slider | 40 | 20–100 (step 5) | Height of the base |
| `base_thickness` | slider | 3 | 2–8 (step 0.5) | Thickness of the base plate |
| `raised` | checkbox | Yes |  | Raised (true) or inset (false) text |
| `border_width` | slider | 2 | 0–5 (step 0.5) | Width of the decorative border frame |
| `hole_diameter` | slider | 4 | 3–8 (step 0.5) | Diameter of the hanging hole |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto; higher = more detail but slower |

## Presets

- **Name Plaque**
  `message`=Your Name, `font_size`=12, `base_width`=80, `base_height`=40, `raised`=Yes, `text_depth`=1.5
- **Gift Tag**
  `message`=With Love, `font_size`=8, `base_width`=60, `base_height`=30, `hole_diameter`=4, `text_depth`=1
- **Door Sign**
  `message`=Welcome, `font_size`=20, `base_width`=150, `base_height`=60, `border_width`=2, `text_depth`=2
- **Desk Nameplate**
  `message`=J. Smith, `font_size`=14, `base_width`=120, `base_height`=35, `base_thickness`=5, `raised`=Yes, `text_depth`=2
- **Pet Tag**
  `message`=Max, `font_size`=10, `base_width`=40, `base_height`=40, `hole_diameter`=5, `base_thickness`=3, `text_depth`=1.5
- **Room Sign**
  `message`=Office, `font_size`=16, `base_width`=120, `base_height`=50, `border_width`=3, `raised`=Yes, `text_depth`=1.5
- **Keychain**
  `message`=HOME, `font_size`=6, `base_width`=45, `base_height`=25, `hole_diameter`=3, `base_thickness`=2.5, `text_depth`=0.8

## Parts

| ID | Label | Default Color |
|---|---|---|
| `plaque` | Plaque | `#8e44ad` |
| `tag` | Tag | `#e67e22` |
| `sign` | Sign | `#2c3e50` |

## Constraints

- `base_thickness >= 2` — Minimum 2mm thickness for stability (error)
- `text_depth <= base_thickness` — Text depth cannot exceed base thickness (error)
- `font_size <= base_height * 0.8` — Text too large for the base (warning)
- `base_width >= 40` — Minimum 40mm width for readable text (warning)

## Assembly Steps

1. **Print the piece**
   Text facing up, 0.12mm layers for text detail, 20% infill
2. **Sand and paint (optional)**
   Sand with 220 grit, paint text with contrasting color
3. **Mount or hang**
   Use mounting tape for plaques/signs, key ring for tags
   Hardware: keyring, mounting_tape

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
| Key ring (for tag) | 1 | pcs |
| Mounting tape (for plaque/sign) | 1 | pcs |

## Render Estimates

- **base_time**: 3
- **per_unit**: 0.5
- **per_part**: 5
- **fn_factor**: 32
- **wasm_multiplier**: 2
- **warning_threshold_seconds**: 30

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
