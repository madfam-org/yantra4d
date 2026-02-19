/*
 * ============================================================================
 * YANTRA4D AOCL HYPEROBJECT LIBRARY (NATIVE)
 *
 * Copyright (c) 2026 madfam-org
 * Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).
 * ============================================================================
 * 
 * CORE CDG: AOCL Substrate Retention & Box Latches
 */

include <BOSL2/std.scad>

// CDG Algorithms
function slot_width(slide_thick, tol_z) = slide_thick + tol_z + 0.2;
function pitch(slot_w, rib_w) = slot_w + rib_w;

module aocl_retention_rib(height, depth, root_w, tip_w, chamfer_h) {
  _ch = min(chamfer_h, height * 0.25);
  _body = height - _ch;
  _off = (root_w - tip_w) / 2;
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

module aocl_label_recess(w, h, d = 0.4) {
  cuboid([w, h, d], anchor=BOTTOM);
}

module aocl_snap_arm(len, w, t, hook_h, hook_d) {
  cuboid([w, t, len], anchor=BOTTOM + BACK) {
    attach(TOP) cuboid([w, t + hook_d, hook_h], anchor=BOTTOM + BACK);
  }
}

module aocl_snap_catch(w, h, d) {
  cuboid([w, d, h], anchor=BOTTOM);
}
