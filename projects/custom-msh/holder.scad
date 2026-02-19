// ============================================================================
// holder.scad — AOCL Single Substrate Holder (NATIVE)
// ============================================================================
// Copyright (c) 2026 madfam-org
// Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).

use <aocl_lib.scad>
include <BOSL2/std.scad>

// Substrate
substrate_size = 25.4;
tolerance_xy = 0.4;
tolerance_z = 0.2;
wall_thickness = 2.0;
label_area = 1;
chamfer_pocket = 1;
fn = 0;

$fn = fn > 0 ? fn : 32;

_length = 5 * 25.4;
_width = 3 * 25.4;
_thickness = 15.0;
_pocket_size = substrate_size + tolerance_xy;
_chamfer_size = 1.5;
_label_w = 40;
_label_h = 15;
_label_d = 0.4;

module holder_body() {
  translate([_length / 2, _width / 2, _thickness / 2]) {
    diff("pocket label") {
      cuboid([_length, _width, _thickness], rounding=1.5, edges=[TOP, BOTTOM], anchor=CENTER);
      tag("pocket") {
        cuboid([_pocket_size, _pocket_size, _thickness + 2], anchor=CENTER);
        if (chamfer_pocket == 1) {
          up(_thickness / 2)
            chamfer_mask_z(l=_pocket_size * 2, r=_chamfer_size, square=true, anchor=CENTER);
        }
      }
      if (label_area == 1) {
        tag("label")
          down(_thickness / 2 - _label_d)
            aocl_label_recess(_label_w, _label_h, _label_d + 0.1);
      }
    }
  }
}

holder_body();
