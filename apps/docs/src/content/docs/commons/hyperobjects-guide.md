---
title: Hyperobjects Guide
description: Understanding CDG Hyperobjects — interoperable parametric designs with standardized interfaces for the open-source hardware commons.
---

A **Hyperobject** in Yantra4D is a parametric 3D model that declares standardized mechanical interfaces, enabling different projects to connect, stack, or interoperate with each other. The Hyperobjects Commons is a registry of these interoperable designs.

## The core idea

Most parametric models exist in isolation. You can adjust their dimensions, but they have no formal relationship with other models. A storage bin does not know about the shelf it sits on. A lab tray does not know about the staining rack it feeds into.

Hyperobjects solve this by declaring **Common Denominator Geometry (CDG) interfaces** -- the standardized mechanical contact surfaces that define how objects physically connect. When two hyperobjects share a CDG interface, they are guaranteed to fit together, regardless of how their other parameters change.

## What makes a project a Hyperobject

A project becomes a hyperobject by adding a `hyperobject` block to its `project.json` manifest. This block declares:

1. **Domain** -- the application category
2. **CDG interfaces** -- the standardized geometry contact surfaces
3. **Material awareness** -- how the geometry adapts to physical materials
4. **Societal benefit** -- the commons value statement
5. **License** -- the open-source hardware license

### Example: Microscope Slide Holder

```json
{
  "hyperobject": {
    "domain": "medical",
    "cdg_interfaces": [
      {
        "id": "iso_8037_standard",
        "label": { "en": "ISO 8037 Microscope Slide Standard" },
        "geometry_type": "pocket",
        "standard": "ISO 8037-1:2003",
        "parameters": ["slide_standard", "custom_slide_length", "custom_slide_width"]
      },
      {
        "id": "stacking_interface",
        "label": { "en": "Stacking Lip/Groove Interface" },
        "geometry_type": "snap",
        "standard": "internal",
        "parameters": ["stackable"]
      }
    ],
    "material_awareness": {
      "shrinkage_compensation": false,
      "recycled_material_toggle": false,
      "tolerance_by_material": true
    },
    "societal_benefit": {
      "en": "Enables laboratories to fabricate precision slide retention systems independent of commercial supply chains."
    },
    "commons_license": "CERN-OHL-W-2.0"
  }
}
```

This declares that the Microscope Slide Holder:
- Has a pocket geometry conforming to the ISO 8037-1:2003 standard for microscope slides
- Has a snap-fit stacking interface defined by the project itself
- Adjusts tolerances based on the printing material
- Is licensed under CERN Open Hardware License v2 (weakly reciprocal)

## CDG interface types

Each interface declares a `geometry_type` that describes the kind of mechanical contact surface:

| Geometry type | Description | Example |
|---|---|---|
| `grid` | Regular 2D pattern of features | Gridfinity baseplate grid |
| `rail` | Linear guide or sliding interface | Drawer slides, retention pitch |
| `thread` | Helical screw interface | Threaded caps, bolt holes |
| `socket` | Cylindrical or shaped receptacle | Bearing seats, shaft mounts |
| `pocket` | Recessed cavity for an inserted object | Microscope slide slots |
| `snap` | Press-fit or clip engagement | Stacking lips, lid latches |
| `bolt_pattern` | Hole pattern for fasteners | Mounting flanges |
| `profile` | 2D cross-section used for extrusion | Rail profiles, channel shapes |
| `spline` | Keyed rotational coupling | Motor shaft adapters |
| `surface` | Mating flat or curved surface | Alignment faces |
| `custom` | Project-specific interface | Anything not covered above |

### Standards

Each interface references a `standard`:

- **ISO/ANSI/DIN standards** (e.g., `ISO 8037-1:2003`) -- the interface conforms to a published specification. Any hyperobject implementing the same standard is guaranteed to interoperate.
- **`internal`** -- the interface is defined by the project itself. Other projects can match it by implementing the same geometry, but there is no external specification.

### Parameters

The `parameters` array references parameter IDs from the same manifest. These are the parameters that control the interface geometry. When two hyperobjects share an interface standard, their interface parameters must produce compatible geometry at their default values.

## Domains

The `domain` field categorizes the hyperobject:

| Domain | Examples |
|---|---|
| `household` | Storage organizers, kitchen tools, furniture fittings |
| `industrial` | Jigs, fixtures, machine components |
| `medical` | Lab equipment, surgical guides, prosthetic components |
| `commercial` | Retail displays, POS fixtures, signage |
| `infrastructure` | Pipe fittings, cable management, structural connectors |
| `hybrid` | Cross-domain designs |

## Material awareness

The `material_awareness` block declares how the geometry adapts to the physical properties of additive manufacturing materials:

| Field | Purpose |
|---|---|
| `shrinkage_compensation` | Whether the geometry compensates for material shrinkage during cooling |
| `recycled_material_toggle` | Whether tolerances loosen for less dimensionally stable recycled filament |
| `tolerance_by_material` | Whether tolerance profiles vary by material (PLA vs PETG vs ABS) |

When material awareness is enabled, the platform can adjust interface geometries to maintain correct fit across different printing materials. A pocket designed for PLA may need slightly different clearances when printed in PETG.

## Societal benefit

Every hyperobject includes a human-readable `societal_benefit` statement explaining why the design matters as a commons resource. This is not marketing copy -- it describes the concrete capability the design provides to people who cannot otherwise access it commercially.

## Licensing

Hyperobjects use SPDX license identifiers in the `commons_license` field. Recommended licenses for open-source hardware:

| License | Type | Recommended for |
|---|---|---|
| `CERN-OHL-W-2.0` | Weakly reciprocal | Most projects (allows commercial use, requires sharing modifications to the design) |
| `CERN-OHL-S-2.0` | Strongly reciprocal | Projects where all derivative hardware must remain open |
| `CERN-OHL-P-2.0` | Permissive | Maximum freedom for commercial adoption |

## How interoperability works

Consider two hypothetical hyperobjects:

1. **Lab Tray** -- a horizontal tray with `pocket` interfaces conforming to ISO 8037
2. **Staining Rack** -- a vertical rack with `pocket` interfaces conforming to ISO 8037

Because both declare the same CDG interface (`pocket` + `ISO 8037-1:2003`), slides that fit in the Lab Tray are guaranteed to fit in the Staining Rack. Users can configure either project independently, and the interface geometry remains compatible.

The CDG registry tracks which interfaces exist across the commons, making it possible to search for "all hyperobjects that accept ISO 8037 microscope slides" or "all projects with Gridfinity-compatible grid interfaces".

## Creating a Hyperobject

To classify an existing Yantra4D project as a hyperobject:

1. Identify the mechanical interfaces in your design (where does it contact other objects or standards?).
2. Add the `hyperobject` block to your `project.json` with the appropriate domain, interfaces, and license.
3. Add `"hyperobject"` and `"commons"` to your project's `tags` array.
4. Document the interfaces in your project's `docs/README.md`.

For a complete reference implementation, see `projects/microscope-slide-holder/project.json`.
