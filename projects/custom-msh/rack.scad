include <../../libs/BOSL2/std.scad>
include <vendor/microscope-slide-holder/slide_lib.scad>

// AOCL Custom Rack
// Holds 10 substrates (1x1")
// Numbered 1-10

$fn = 64;

// --- Parameters ---
slide_standard = 4;
custom_slide_length = 25.4;
custom_slide_width = 25.4;
custom_slide_thickness = 1.0;
num_slots = 10;
wall_thickness = 2.0;

// Override defaults from staining_rack logic
handle = 1;
drainage_angle = 5;
open_bottom = 1;
label_area = 1;
tolerance_xy = 0.4;
tolerance_z = 0.2;

// --- Logic from staining_rack.scad ---
_slide = resolve_slide(slide_standard, custom_slide_length, custom_slide_width, custom_slide_thickness);
_sl = _slide[0];
_sw = _slide[1];
_st = _slide[2];

_min_rib_w = 2.0;
_slot_w = slot_width(_st, tolerance_z);
_pitch = pitch(_slot_w, _min_rib_w);
_forced_pitch = max(_pitch, 5.0);
_slot_depth = _sw;
_rib_height = _slot_depth;

_pillar_w = wall_thickness;
_crossbar_w = 3.0;
_crossbar_h = 2.5;

_body_x = (num_slots * _forced_pitch) + _min_rib_w + (2 * _pillar_w);
_body_y = _sl + (2 * _pillar_w) + tolerance_xy;
_base_h = open_bottom == 1 ? _crossbar_h : wall_thickness;
_body_z = _rib_height + _base_h;

_handle_w = min(_body_x * 0.6, 80);
_handle_h = 15;
_handle_thick = 4;

module rectangular_rib(h, w, t) {
  cube([t, w, h]);
}

module custom_rack() {
  // Top rails
  translate([0, 0, _body_z - _crossbar_h]) cube([_body_x, _pillar_w, _crossbar_h]); // Front
  translate([0, _body_y - _pillar_w, _body_z - _crossbar_h]) cube([_body_x, _pillar_w, _crossbar_h]); // Back
  translate([0, 0, _body_z - _crossbar_h]) cube([_pillar_w, _body_y, _crossbar_h]); // Left
  translate([_body_x - _pillar_w, 0, _body_z - _crossbar_h]) cube([_pillar_w, _body_y, _crossbar_h]); // Right

  // Corner Pillars
  cube([_pillar_w, _pillar_w, _body_z]);
  translate([_body_x - _pillar_w, 0, 0]) cube([_pillar_w, _pillar_w, _body_z]);
  translate([0, _body_y - _pillar_w, 0]) cube([_pillar_w, _pillar_w, _body_z]);
  translate([_body_x - _pillar_w, _body_y - _pillar_w, 0]) cube([_pillar_w, _pillar_w, _body_z]);

  // Bottom
  if (open_bottom) {
    cube([_body_x, _pillar_w, _crossbar_h]);
    translate([0, _body_y - _pillar_w, 0]) cube([_body_x, _pillar_w, _crossbar_h]);
    cube([_pillar_w, _body_y, _crossbar_h]);
    translate([_body_x - _pillar_w, 0, 0]) cube([_pillar_w, _body_y, _crossbar_h]);
    for (frac = [0.33, 0.66]) {
      translate([0, _body_y * frac - _crossbar_w / 2, 0]) cube([_body_x, _crossbar_w, _crossbar_h]);
    }
  }

  // Ribs
  translate([_pillar_w, 0, _crossbar_h]) {
    for (i = [0:num_slots]) {
      translate([i * _forced_pitch, 0, 0]) rectangular_rib(_rib_height, _pillar_w, _min_rib_w);
    }
  }
  translate([_pillar_w, _body_y - _pillar_w, _crossbar_h]) {
    for (i = [0:num_slots]) {
      translate([i * _forced_pitch, 0, 0]) rectangular_rib(_rib_height, _pillar_w, _min_rib_w);
    }
  }

  // Handle
  if (handle) {
    _hx = (_body_x - _handle_w) / 2;
    _hy = (_body_y - _handle_thick) / 2;
    _hz = _body_z;
    translate([_hx, _hy, _hz]) cube([_handle_thick, _handle_thick, _handle_h]);
    translate([_hx + _handle_w - _handle_thick, _hy, _hz]) cube([_handle_thick, _handle_thick, _handle_h]);
    translate([_hx, _hy, _hz + _handle_h - _handle_thick]) cube([_handle_w, _handle_thick, _handle_thick]);
  }

  // Numbering
  start_x = _pillar_w;
  // Number on the front top rail face
  color("black")for (i = [0:num_slots - 1]) {
    // Center of slot
    cx = start_x + (i * _forced_pitch) + (_forced_pitch / 2); // approximate center of slot space
    // Actually rib is at start of pitch. Slot is between ribs.
    // Rib at i*pitch. Slot between i*pitch and (i+1)*pitch.
    // Center of slot is i*pitch + pitch/2. But pitch includes rib.
    // Rib is min_rib_w. Slot gap is slot_w.
    // Center of gap = rib + slot_w/2.

    tx = start_x + (i * _forced_pitch) + _min_rib_w + (_slot_w / 2);

    // On top of front rail
    translate([tx, _pillar_w / 2, _body_z])
      linear_extrude(1)
        text(str(i + 1), size=2, halign="center", valign="center");
  }
}

custom_rack();
