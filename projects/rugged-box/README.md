# Rugged Box V1

Fully parametric, hinged rugged case with snap-fit latches, optional gasket seals, internal dividers, and stackable feet. Pure OpenSCAD — zero external dependencies.

## Features

- Hinged lid with configurable hinge count, radius, and screw sizing
- Snap-fit latches with adjustable clip angle and opener tab
- Optional gasket seal (TPU) for water resistance
- Internal grid dividers (X and Y sections, with skip support)
- Stackable feet with glue-in inserts
- Three polygon quality levels (extra low poly, low poly, curved)
- Chamfered corners with configurable radius

## Parameters

### Box Dimensions
| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `internalBoxWidthXMm` | 100 | 20–300 | Internal width (X axis) |
| `internalboxLengthYMm` | 60 | 20–200 | Internal length (Y axis) |
| `internalBoxTopHeightZMm` | 20 | 5–100 | Internal height of lid |
| `internalboxBottomHeightZMm` | 20 | 5–100 | Internal height of base |

### Wall & Chamfer
| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `boxWallWidthMm` | 3.0 | 1–10 | Wall and floor thickness |
| `boxChamferRadiusMm` | 4 | 0.5–20 | Corner chamfer radius |

### Seal
| Parameter | Default | Description |
|-----------|---------|-------------|
| `boxSealType` | 1 | 1=Non-Gasket (circular), 2=Gasket (TPU) |
| `gasketSlotWidth` | 2.2 | Width of gasket slot (type 2 only) |
| `gasketSlotDepth` | 2.2 | Depth of gasket slot (type 2 only) |

### Hinges
| Parameter | Default | Description |
|-----------|---------|-------------|
| `numberOfHinges` | 2 | Number of hinges (1–5) |
| `hingeTotalWidthMm` | 25 | Hinge width = screw length needed |
| `hingeRadiusMm` | 4 | Hinge pivot radius |
| `hingeCenterOffsetMm` | 5 | Offset hinges from center |

### Latches
| Parameter | Default | Description |
|-----------|---------|-------------|
| `numberOfLatches` | 2 | Number of latches (1–5) |
| `latchSupportTotalWidth` | 25 | Latch width = screw length needed |
| `latchClipCutoutAngle` | 25 | Clip angle (10=tight, 50=loose) |
| `latchOpenerLengthMultiplier` | 1.4 | Opener tab length (1=short, 2=long) |

### Dividers
| Parameter | Default | Description |
|-----------|---------|-------------|
| `countainerWidthXSections` | 1 | X sections (dividers = sections - 1) |
| `boxLengthYSections` | 1 | Y sections (dividers = sections - 1) |

### Feet
| Parameter | Default | Description |
|-----------|---------|-------------|
| `isFeetAdded` | false | Enable stackable feet |
| `feetwidthMm` | 4 | Foot width |
| `feetLengthMm` | 10 | Foot length |
| `boxGapMm` | 1.5 | Gap between stacked boxes |

## Presets

| Name | Dimensions (WxLxTopxBot) | Notes |
|------|--------------------------|-------|
| Golden Benchy Case | 114x74x17x17 | Fits a golden benchy |
| Tiny | 20x20x5x15 | Smallest possible box |
| Small Rounded | 50x30x20x30 | 15mm chamfer radius |
| Medium (100x60) | 100x60x20x20 | Default preset, with feet |
| Medium Square | 100x100x20x20 | Square, with feet |
| Large (150x100) | 150x100x20x20 | Large, with feet |
| XL (200x130) | 200x130x8x24 | Extra large |
| Organizer (216x116) | 216x116x7x23 | 8x4 grid, 3 hinges |
| Screw Box (216x116) | 216x116x7x23 | 8x3 grid, 3 hinges |
| Tool Case (Gasket) | 140x75.5x26x26 | Gasket seal, extra low poly |

## Print Instructions

### Materials
- **Box body**: PLA, PETG, or ABS (0.2mm layer height recommended)
- **Gasket** (if using seal type 2): TPU 95A
- **Feet inserts** (if using feet): Same as box body

### Hardware
- **Hinge screws**: M3 x `hingeTotalWidthMm` mm (e.g., M3x25mm for default)
- **Latch screws**: M3 x `latchSupportTotalWidth` mm (e.g., M3x25mm for default)
- **Glue**: CA glue for feet attachment (no snap-fit connector)

### Assembly
1. Print all parts on the build plate (use "open" view layout)
2. Insert hinge screws through the hinge barrels — the outer barrels have smaller holes that self-thread
3. Insert latch screws through the latch pivots
4. If using gasket seal, print the gasket in TPU and press-fit into the slot on the box bottom rim
5. If using feet, glue feet into the cutouts on the top and bottom shells
6. Use the gasket test objects to verify TPU tolerances before printing a full gasket

## License

Original design by the Rugged Box author. Parametric OpenSCAD source.
