// ============================================================================
// rack.scad — AOCL 10-Slot Substrate Rack
// ============================================================================
// AOCL Spec: Removable rack holding 10 × 1"×1" substrates in vertical slots.
// Slots are numbered 1–10 on the LEFT face of each slot divider rib.
// Three identical racks fit inside the AOCL outer box.
//
// Parameters are injected by the Yantra4D platform via OpenSCAD -D flag.
// ============================================================================

use <vendor/microscope-slide-holder/slide_lib.scad>
include <../../libs/BOSL2/std.scad>

// ---------------------------------------------------------------------------
// Parameters (injected by platform via -D)
// ---------------------------------------------------------------------------

// Substrate (fixed per AOCL spec — 1"×1"×~1mm)
custom_slide_length = 25.4; // substrate "length" direction (slot depth)
custom_slide_width = 25.4; // substrate "width"  (rib height = slot depth)
custom_slide_thickness = 1.0; // substrate thickness

// Tolerances
tolerance_xy = 0.4; // XY clearance (mm)
tolerance_z = 0.2; // Z / thickness clearance (mm)

// Structure
wall_thickness = 2.0; // Pillar / rail width (mm)
num_slots = 10; // Substrate positions per rack

// Features
handle = 1; // 1 = carry handle on top
open_bottom = 1; // 1 = open-frame base crossbars; 0 = solid floor
drainage_angle = 5; // Drainage slope in degrees (0 = flat)
label_area = 1; // 1 = debossed label recess on front rail face
numbering_start = 1; // First slot number embossed on left rib face

// Quality
fn = 0; // $fn; 0 = auto

// ---------------------------------------------------------------------------
// Resolution
// ---------------------------------------------------------------------------
$fn = fn > 0 ? fn : 32;

// ---------------------------------------------------------------------------
// Derived geometry (via slide_lib functions)
// ---------------------------------------------------------------------------
// For 1"×1"×1mm substrates:
//   slot_width  = 1.0 + 0.2 (tol_z) + 0.2 (waviness) = 1.4 mm
//   pitch       = 1.4 + min_rib_w = 1.4 + 2.0 = 3.4 mm
//   forced_pitch = max(3.4, 3.4) = 3.4 mm  (no staining-rack minimum here)

_min_rib_w = 2.0;
_slot_w = slot_width(custom_slide_thickness, tolerance_z);
_pitch = pitch(_slot_w, _min_rib_w);
// Note: we do NOT force 5mm minimum — that was for the staining rack.
// Allow natural pitch to keep 10 slots within ~42mm rack body footprint.
_slot_depth = custom_slide_width + tolerance_xy; // substrate sits to this depth
_rib_height = _slot_depth;
_chamfer_h = min(1.5, _rib_height * 0.15);

_pillar_w = wall_thickness;
_crossbar_w = 3.0;
_crossbar_h = 2.5;

_body_x = (num_slots * _pitch) + _min_rib_w + (2 * _pillar_w);
_body_y = custom_slide_length + (2 * _pillar_w) + tolerance_xy;
_base_h = open_bottom == 1 ? _crossbar_h : wall_thickness;
_body_z = _rib_height + _base_h;

_handle_w = min(_body_x * 0.7, 70);
_handle_h = 14;
_handle_thick = 3.5;

// Label recess on front pillar
_label_w = min(30, _body_x * 0.5);
_label_h = min(10, _body_z * 0.4);
_num_size = min(2.5, _pitch * 0.7);

// ---------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------

module rack_body() {
  // Top front rail
  translate([0, 0, _body_z - _crossbar_h])
    cube([_body_x, _pillar_w, _crossbar_h]);
  // Top back rail
  translate([0, _body_y - _pillar_w, _body_z - _crossbar_h])
    cube([_body_x, _pillar_w, _crossbar_h]);
  // Top left rail
  translate([0, 0, _body_z - _crossbar_h])
    cube([_pillar_w, _body_y, _crossbar_h]);
  // Top right rail
  translate([_body_x - _pillar_w, 0, _body_z - _crossbar_h])
    cube([_pillar_w, _body_y, _crossbar_h]);

  // Corner pillars (full height)
  cube([_pillar_w, _pillar_w, _body_z]);
  translate([_body_x - _pillar_w, 0, 0])
    cube([_pillar_w, _pillar_w, _body_z]);
  translate([0, _body_y - _pillar_w, 0])
    cube([_pillar_w, _pillar_w, _body_z]);
  translate([_body_x - _pillar_w, _body_y - _pillar_w, 0])
    cube([_pillar_w, _pillar_w, _body_z]);

  // Base structure
  if (open_bottom == 1) {
    // Open-frame base: perimeter + 2 crossbars
    cube([_body_x, _pillar_w, _crossbar_h]);
    translate([0, _body_y - _pillar_w, 0])
      cube([_body_x, _pillar_w, _crossbar_h]);
    cube([_pillar_w, _body_y, _crossbar_h]);
    translate([_body_x - _pillar_w, 0, 0])
      cube([_pillar_w, _body_y, _crossbar_h]);
    for (frac = [0.33, 0.67]) {
      translate([0, _body_y * frac - _crossbar_w / 2, 0])
        cube([_body_x, _crossbar_w, _crossbar_h]);
    }
  } else {
    // Solid floor
    cube([_body_x, _body_y, wall_thickness]);
  }

  // Retention ribs (tapered — from slide_lib, AM-optimised chamfered profile)
  // Front rib row
  translate([_pillar_w, 0, _base_h]) {
    for (i = [0:num_slots]) {
      translate([i * _pitch, 0, 0])
        retention_rib(
          height=_rib_height,
          depth=_pillar_w,
          root_w=_min_rib_w,
          tip_w=_min_rib_w * 0.65,
          chamfer_h=_chamfer_h
        );
    }
  }
  // Back rib row
  translate([_pillar_w, _body_y - _pillar_w, _base_h]) {
    for (i = [0:num_slots]) {
      translate([i * _pitch, 0, 0])
        retention_rib(
          height=_rib_height,
          depth=_pillar_w,
          root_w=_min_rib_w,
          tip_w=_min_rib_w * 0.65,
          chamfer_h=_chamfer_h
        );
    }
  }

  // Carry handle
  if (handle == 1) {
    _hx = (_body_x - _handle_w) / 2;
    _hy = (_body_y - _handle_thick) / 2;
    _hz = _body_z;
    // Left post
    translate([_hx, _hy, _hz])
      cube([_handle_thick, _handle_thick, _handle_h]);
    // Right post
    translate([_hx + _handle_w - _handle_thick, _hy, _hz])
      cube([_handle_thick, _handle_thick, _handle_h]);
    // Top bar
    translate([_hx, _hy, _hz + _handle_h - _handle_thick])
      cube([_handle_w, _handle_thick, _handle_thick]);
  }
}

// Slot numbering on the LEFT face of each divider rib (per AOCL spec)
module slot_numbers() {
  if (fn > 0) {
    for (i = [0:num_slots - 1]) {
      _num = numbering_start + i;
      // Centre of each slot gap, on the front face of the front pillar
      _cx = _pillar_w + (i * _pitch) + _min_rib_w + (_slot_w / 2);
      // LEFT face of each slot = the rib at position i, left side
      _rib_x = _pillar_w + (i * _pitch);
      // Place number on left (−Y) face of front pillar at each slot
      translate([_rib_x + _num_size / 2 + 0.4, -0.01, _base_h + _rib_height * 0.4])
        rotate([90, 0, 0])
          linear_extrude(height=0.5)
            text(
              str(_num), size=_num_size,
              halign="center", valign="center",
              font="Liberation Sans:style=Bold"
            );
    }
  }
}

// Label recess on front face
module rack_label() {
  if (label_area == 1) {
    translate([(_body_x - _label_w) / 2, -0.01, (_body_z - _label_h) / 2])
      rotate([90, 0, 0])
        translate([0, 0, -0.4])
          label_recess(_label_w, _label_h, 0.5);
  }
}

// ---------------------------------------------------------------------------
// Assembly
// ---------------------------------------------------------------------------
difference() {
  rack_body();
  rack_label();
}
slot_numbers();
