// ============================================================================
// holder.scad — AOCL Single Substrate Holder (NATIVE)
// ============================================================================
// Copyright (c) 2026 madfam-org
// Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).

use <aocl_lib.scad>
include <BOSL2/std.scad>

// --- Configuration Parameters ---
// Substrate physical dimensions
substrate_size = 25.4;

// FDM printing clearances
tolerance_xy = 0.4;
tolerance_z = 0.2;

// Structural thickness for robust parts
wall_thickness = 2.0;

// Feature toggles
label_area = 1; // Checkbox to cut a recess for labels
chamfer_pocket = 1; // Checkbox to add insertion chamfers to the slot
fn = 0; // Geometry curve quality

$fn = fn > 0 ? fn : 32;

// --- Derived Geometry Variables ---
_length = 5 * 25.4;
_width = 3 * 25.4;
_thickness = 15.0;

// Add clearance to the pocket
_pocket_size = substrate_size + tolerance_xy;
_chamfer_size = 1.5;

// Area for adhesive or marker labels
_label_w = 40;
_label_h = 15;
_label_d = 0.4;

// --- Main Module ---
// Generates the solid body and uses BOSL2 boolean diff() to carve out the pocket
module holder_body() {
  translate([_length / 2, _width / 2, _thickness / 2]) {

    // Evaluate geometry matching "pocket" and "label" tags and subtract them from the untagged base
    diff("pocket label") {

      // Base cuboid block
      cuboid([_length, _width, _thickness], rounding=1.5, edges=[TOP, BOTTOM], anchor=CENTER);

      // Pocket geometry built to be subtracted
      tag("pocket") {
        cuboid([_pocket_size, _pocket_size, _thickness + 2], anchor=CENTER);

        // Subtract a chamfered rim area for easier slide insertion
        if (chamfer_pocket == 1) {
          up(_thickness / 2)
            chamfer_mask_z(l=_pocket_size * 2, r=_chamfer_size, square=true, anchor=CENTER);
        }
      }

      // Debossed label area geometry to be subtracted
      if (label_area == 1) {
        tag("label")
          down(_thickness / 2 - _label_d)
            aocl_label_recess(_label_w, _label_h, _label_d + 0.1);
      }
    }
  }
}

// Top-level instantiation
holder_body();
