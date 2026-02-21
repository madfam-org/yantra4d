// ============================================================================
// microscope-slide-hyperobject / slide.scad
// ============================================================================
// Copyright (c) 2026 madfam-org
// Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal
//
// YANTRA4D COMMON DENOMINATOR GEOMETRY (CDG)
// Centralized library for all slide architectures. Replaces slide_lib.scad 
// and aocl_lib.scad in specific downstream projects.
//
// Incorporates waviness calculations from parametric research standard ISO 8037.
// ============================================================================

include <BOSL2/std.scad>

// --- Mathematical Constants & Functions ---

// Calculates the total physical width required for a slide slot, 
// including the thickness of the glass, the vertical wiggle room (tol_z), 
// and an extra waviness tolerance padding (0.2mm) per ISO 8037 planarity spec.
function slide_slot_width(slide_thick, tol_z) = slide_thick + tol_z + 0.2;

// Calculates the "pitch" (distance from the center of one feature to the next).
// This is the width of the slot opening + the width of the plastic rib separating them.
function slide_pitch(slot_w, rib_w) = slot_w + rib_w;

// --- Physical Retention Geometry ---

// slide_retention_rib aocl port:
// Generates a vertical plastic divider (rib) meant to hold a slide in place.
// Tapered base and chamfered tip prevent binding.
module slide_retention_rib(height, depth, root_w, tip_w, chamfer_h) {
  _ch = min(chamfer_h, height * 0.25);
  _body = height - _ch;
  _off = (root_w - tip_w) / 2;

  // Render in XY, rotate to correct Z orientation
  rotate([-90, 0, 0]) translate([0, -height, 0]) {
      linear_extrude(height=depth)
        polygon([[0, 0], [root_w, 0], [root_w - _off, _body], [_off, _body]]);

      if (_ch > 0) {
        _w = tip_w;
        translate([_off, 0, 0])
          linear_extrude(height=depth)
            polygon([[0, _body], [_w, _body], [_w / 2 + _w * 0.3, _body + _ch], [_w / 2 - _w * 0.3, _body + _ch]]);
      }
    }
}

// Simple Boolean keep-out zone encompassing exactly 1 slide + its tolerances
module slide_bounding_box(length, width, thickness, tol_xy, tol_z) {
  cube(
    [
      slide_slot_width(thickness, tol_z),
      length + tol_xy,
      width + tol_xy,
    ]
  );
}

// slide_slot_array legacy port:
// Generates an entire ribbon of retention ribs in a single pass at the specified pitch.
module slide_slot_array(count, pitch, height, depth, root_w, tip_w, chamfer_h, tapered) {
  for (i = [0:count]) {
    translate([i * pitch, 0, 0]) {
      if (tapered) {
        slide_retention_rib(height, depth, root_w, tip_w, chamfer_h);
      } else {
        // rectangular_rib fallback locally handled directly in cube
        cube([root_w, depth, height]);
      }
    }
  }
}

// --- Test Render Stub ---
// To prove this module renders directly via project.json if tested

// Test parameters injected from JSON properties
slide_length = 76.2;
slide_width = 25.4;
slide_thickness = 1.0;
tolerance_xy = 0.4;
tolerance_z = 0.2;

// Draw a sample subset showing the boolean subtraction workflow in effect
module _test_array() {
  _slot_w = slide_slot_width(slide_thickness, tolerance_z);
  _pitch = slide_pitch(_slot_w, 1.5);

  difference() {
    cube([3 * _pitch + 1.5, slide_length + 2, slide_width + 5]);

    // Scoop out the cavities
    for (i = [0:2]) {
      translate([i * _pitch + 1.5, 1, 1])
        slide_bounding_box(slide_length, slide_width, slide_thickness, tolerance_xy, tolerance_z);
    }
  }

  // Draw the ribs separately for visualization
  translate([0, 0, slide_width + 5])
    color("Cyan")
      slide_slot_array(3, _pitch, 15, slide_length + 2, 1.5, 0.8, 2, true);
}

// Execute dummy output if this file is instantiated directly via web
// Normally we would branch on a parameter, but for now we'll just leave it visible.
if (is_undef($hide_test)) {
  _test_array();
}
