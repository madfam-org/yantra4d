# Rugged Box

Parametric hinged rugged case with latches, gasket seals, dividers, and feet

*Caja resistente paramétrica con bisagras, pestillos, juntas, divisores y pies*

**Version**: 0.1.0  
**Slug**: `rugged-box`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `` | Complete | `rugged_complete.scad` | bottom, top, latches, gasket, feet, tpu-bottom-insert, tpu-top-insert |
| `` | Bottom | `rugged_bottom.scad` | bottom |
| `` | Top | `rugged_top.scad` | top |
| `` | Latches | `rugged_latches.scad` | latches |
| `` | Gasket | `rugged_gasket.scad` | gasket |
| `` | Feet | `rugged_feet.scad` | feet |
| `` | Closed View | `rugged_closed.scad` | bottom, top, latches |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `` | slider | 100 | 20–300 | Internal width of the box in mm |
| `` | slider | 60 | 20–200 | Internal length of the box in mm |
| `` | slider | 20 | 5–100 | Internal height of the lid |
| `` | slider | 20 | 5–100 | Internal height of the base |
| `` | slider | 3.0 | 1–10 (step 0.1) | Wall and floor thickness in mm |
| `` | slider | 4 | 0.5–20 (step 0.1) | Corner chamfer radius in mm |
| `` | select | 1 |  | 1 = Non-Gasket (circular), 2 = Gasket (TPU, water-resistant) |
| `` | slider | 2.2 | 1–5 (step 0.1) | Width of the gasket slot (gasket seal type only) |
| `` | slider | 2.2 | 1–5 (step 0.1) | Depth of the gasket slot (gasket seal type only) |
| `` | slider | 2 | 1–5 (step 0.1) | Width of the rim around the opening |
| `` | slider | 3 | 1–8 (step 0.1) | Height of the rim around the opening |
| `` | slider | 2 | 0–6 | Number of reinforcement ribs on each side |
| `` | slider | 2 | 1–5 | Thickness of each rib from the wall |
| `` | slider | 4 | 1–8 | Width of each rib along the wall |
| `` | slider | 1 | 1–20 | Number of horizontal sections (dividers = sections - 1) |
| `` | slider | 1 | 1–20 | Number of vertical sections (dividers = sections - 1) |
| `` | slider | 0 | 0–10 | Number of X dividers to skip (creates larger first section) |
| `` | slider | 0 | 0–10 | Number of Y dividers to skip (creates larger first section) |
| `` | slider | 2 | 1–5 | Number of hinges |
| `` | slider | 25 | 10–40 | Total hinge width (= screw length needed) |
| `` | slider | 4 | 2–6 (step 0.1) | Radius of the hinge pivot |
| `` | slider | 5 | 0–30 | Offset each hinge from center |
| `` | slider | 2 | 1–5 | Number of latches |
| `` | slider | 25 | 10–40 | Total latch width (= screw length needed) |
| `` | slider | 5 | 0–30 | Offset each latch from center |
| `` | slider | 25 | 10–50 | Latch clip angle (10=tight, 50=loose) |
| `` | slider | 1.4 | 0.5–3 (step 0.1) | Latch opener tab length multiplier (1=short, 2=long) |
| `` | checkbox | No |  | Enable stackable feet and cutouts |
| `` | slider | 4 | 2–10 | Width of each foot in mm |
| `` | slider | 10 | 5–20 | Length of each foot in mm |
| `` | slider | 1.5 | 0.5–5 (step 0.1) | Gap between stacked boxes in mm |
| `` | select | 2 |  | Polygon quality level |

## Presets

- **Golden Benchy Case**
  `internalBoxWidthXMm`=114, `internalboxLengthYMm`=74, `internalBoxTopHeightZMm`=17, `internalboxBottomHeightZMm`=17, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=30, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=5, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=5, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=No, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Tiny (20x20)**
  `internalBoxWidthXMm`=20, `internalboxLengthYMm`=20, `internalBoxTopHeightZMm`=5, `internalboxBottomHeightZMm`=15, `boxWallWidthMm`=1, `boxChamferRadiusMm`=0.5, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=1, `rimHeightMm`=2, `numSideSupportRibs`=2, `supportRibThickness`=1, `supportRibWidth`=1, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=1, `hingeTotalWidthMm`=12, `hingeRadiusMm`=2.2, `hingeCenterOffsetMm`=0, `numberOfLatches`=1, `latchSupportTotalWidth`=12, `latchCenterOffsetMm`=0, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.6, `isFeetAdded`=No, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Small Rounded (50x30)**
  `internalBoxWidthXMm`=50, `internalboxLengthYMm`=30, `internalBoxTopHeightZMm`=20, `internalboxBottomHeightZMm`=30, `boxWallWidthMm`=3, `boxChamferRadiusMm`=15, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=1, `rimHeightMm`=3, `numSideSupportRibs`=1, `supportRibThickness`=1, `supportRibWidth`=3, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=1, `hingeTotalWidthMm`=30, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=5, `numberOfLatches`=1, `latchSupportTotalWidth`=30, `latchCenterOffsetMm`=5, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=No, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Medium Square (100x100)**
  `internalBoxWidthXMm`=100, `internalboxLengthYMm`=100, `internalBoxTopHeightZMm`=20, `internalboxBottomHeightZMm`=20, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=5, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=5, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Medium Square Shallow Lid**
  `internalBoxWidthXMm`=100, `internalboxLengthYMm`=100, `internalBoxTopHeightZMm`=8, `internalboxBottomHeightZMm`=24, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=5, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=5, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Medium Square Deep**
  `internalBoxWidthXMm`=100, `internalboxLengthYMm`=100, `internalBoxTopHeightZMm`=10, `internalboxBottomHeightZMm`=60, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=5, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=5, `latchClipCutoutAngle`=40, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Medium (100x60)**
  `internalBoxWidthXMm`=100, `internalboxLengthYMm`=60, `internalBoxTopHeightZMm`=20, `internalboxBottomHeightZMm`=20, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=5, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=5, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Medium Shallow Lid**
  `internalBoxWidthXMm`=100, `internalboxLengthYMm`=60, `internalBoxTopHeightZMm`=8, `internalboxBottomHeightZMm`=24, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=5, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=5, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Medium Deep**
  `internalBoxWidthXMm`=100, `internalboxLengthYMm`=60, `internalBoxTopHeightZMm`=10, `internalboxBottomHeightZMm`=60, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=5, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=5, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Large (150x100)**
  `internalBoxWidthXMm`=150, `internalboxLengthYMm`=100, `internalBoxTopHeightZMm`=20, `internalboxBottomHeightZMm`=20, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=5, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=5, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Large Shallow Lid**
  `internalBoxWidthXMm`=150, `internalboxLengthYMm`=100, `internalBoxTopHeightZMm`=8, `internalboxBottomHeightZMm`=24, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=15, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=15, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Large Deep**
  `internalBoxWidthXMm`=150, `internalboxLengthYMm`=100, `internalBoxTopHeightZMm`=10, `internalboxBottomHeightZMm`=60, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=15, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=15, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **XL (200x130)**
  `internalBoxWidthXMm`=150, `internalboxLengthYMm`=100, `internalBoxTopHeightZMm`=8, `internalboxBottomHeightZMm`=24, `boxWallWidthMm`=3, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=2, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=15, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=15, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Organizer (216x116)**
  `internalBoxWidthXMm`=216, `internalboxLengthYMm`=116, `internalBoxTopHeightZMm`=7, `internalboxBottomHeightZMm`=23, `boxWallWidthMm`=2, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=3, `supportRibThickness`=2, `supportRibWidth`=6, `countainerWidthXSections`=8, `boxLengthYSections`=4, `numCountainerWidthXSectionsToSkip`=1, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=3, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=15, `numberOfLatches`=3, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=15, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.6, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Screw Box (216x116)**
  `internalBoxWidthXMm`=216, `internalboxLengthYMm`=116, `internalBoxTopHeightZMm`=7, `internalboxBottomHeightZMm`=23, `boxWallWidthMm`=2, `boxChamferRadiusMm`=4, `boxSealType`=1, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=3, `supportRibThickness`=2, `supportRibWidth`=6, `countainerWidthXSections`=8, `boxLengthYSections`=3, `numCountainerWidthXSectionsToSkip`=1, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=3, `hingeTotalWidthMm`=30, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=15, `numberOfLatches`=3, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=15, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.6, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1.5, `BoxPolygonStyle`=2
- **Tool Case (Gasket)**
  `internalBoxWidthXMm`=140, `internalboxLengthYMm`=75.5, `internalBoxTopHeightZMm`=26, `internalboxBottomHeightZMm`=26, `boxWallWidthMm`=3, `boxChamferRadiusMm`=6, `boxSealType`=2, `gasketSlotWidth`=2.2, `gasketSlotDepth`=2.2, `rimWidthMm`=2, `rimHeightMm`=3, `numSideSupportRibs`=3, `supportRibThickness`=2, `supportRibWidth`=4, `countainerWidthXSections`=1, `boxLengthYSections`=1, `numCountainerWidthXSectionsToSkip`=0, `numBoxLengthYSectionsToSkip`=0, `numberOfHinges`=2, `hingeTotalWidthMm`=25, `hingeRadiusMm`=4, `hingeCenterOffsetMm`=10, `numberOfLatches`=2, `latchSupportTotalWidth`=25, `latchCenterOffsetMm`=10, `latchClipCutoutAngle`=25, `latchOpenerLengthMultiplier`=1.4, `isFeetAdded`=Yes, `feetwidthMm`=4, `feetLengthMm`=10, `boxGapMm`=1, `BoxPolygonStyle`=1

## Parts

| ID | Label | Default Color |
|---|---|---|
| `bottom` | Bottom | `` |
| `top` | Top | `` |
| `latches` | Latches | `` |
| `gasket` | Gasket | `` |
| `feet` | Feet | `` |
| `tpu-bottom-insert` | TPU Bottom Insert | `` |
| `tpu-top-insert` | TPU Top Insert | `` |

## Assembly Steps

. ****
. ****
. ****
. ****
. ****

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
|  | numberOfHinges |  |
|  | numberOfLatches |  |
|  | 1 |  |

## Render Estimates

- **base_time**: 8
- **per_unit**: 1
- **per_part**: 4

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
