/*
 * ============================================================================
 * YANTRA4D HYPEROBJECT TEMPLATE
 *
 * Copyright (c) 2026 madfam-org
 *
 * This hardware, design, and accompanying software are released under the
 * CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).
 *
 * You may redistribute and modify this documentation and make products using
 * it under the terms of the CERN-OHL-W-2.0.
 *
 * This design is distributed WITHOUT ANY WARRANTY; without even the implied
 * warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the CERN-OHL-W-2.0 for more details.
 *
 * ============================================================================
 * ARCHITECTURE REQUIREMENTS (MANIFESTO COMPLIANT):
 * 1. Must use BOSL2 for all Common Denominator Geometry (CDG).
 * 2. Must leverage OEP8 geometry-as-data constructs where applicable.
 * 3. Must clearly demarcate "External Interfaces" vs "Internal Logic".
 * ============================================================================
 */

include <BOSL2/std.scad>

// ============================================================================
// [1] INPUT PARAMETERS (Mapped to project.json)
// ============================================================================
width = 50; // [10:1:100]
depth = 50; // [10:1:100]
height = 20; // [5:1:50]
wall_thickness = 2; // [1.0:0.1:5.0]

// ============================================================================
// [2] OEP8 DATA STRUCTURES (Geometry Logic)
// ============================================================================
// Define the parametric bounds and material properties as data
_cfg = [
  ["dimensions", [width, depth, height]],
  [
    "constraints",
    [
      ["min_wall", 1.2],
      ["default_tolerance", 0.2],
    ],
  ],
  [
    "interfaces",
    [
      ["bottom_mount", "gridfinity_42mm"],
      ["top_lid", "snap_fit_v1"],
    ],
  ],
];

function get_prop(dict, key) = dict[search([key], dict)[0]][1];

// ============================================================================
// [3] EXTERNAL INTERFACES (The "Bounder" - Freedom of Assembly)
// ============================================================================
// These modules define the immutable points of connection to the outside world.

module external_interface_bottom_mount() {
  // Example: A standardized gridfinity base or DIN rail clip
  // This is the boundary. Proprietary things connect HERE.
  color("blue") cuboid([get_prop(_cfg, "dimensions")[0], get_prop(_cfg, "dimensions")[1], 5], anchor=TOP);
}

// ============================================================================
// [4] INTERNAL CORE GEOMETRY (The Commons Engine - Forced Reciprocity)
// ============================================================================
// These modules define the core workings of the object. Modifications here
// must be contributed back to the commons under CERN-OHL-W-2.0.

module core_hyperobject_body() {
  // Example using BOSL2 attachments
  dims = get_prop(_cfg, "dimensions");

  cuboid([dims[0], dims[1], dims[2]], anchor=BOTTOM) {
    // Attach the external interface to the bottom
    attach(BOTTOM) external_interface_bottom_mount();

    // hollow it out
    attach(TOP, overlap=wall_thickness) cuboid([dims[0] - wall_thickness * 2, dims[1] - wall_thickness * 2, dims[2]], anchor=TOP, $fn=36);
  }
}

// ============================================================================
// [5] MAIN EXECUTION (Render Modes)
// ============================================================================

core_hyperobject_body();
