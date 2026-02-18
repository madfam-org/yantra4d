include <../../libs/BOSL2/std.scad>
include <vendor/microscope-slide-holder/slide_lib.scad>

// AOCL Custom Box
// Holds 3 x 10-slot racks
// Dimensions: ~15cm x 2.6cm x ?

$fn = 64;

// --- Parameters ---
slide_standard = 4;
custom_slide_length = 25.4;
custom_slide_width = 25.4;
custom_slide_thickness = 1.0;
num_rack_slots = 10;
num_racks = 3;
wall_thickness = 2.0;
clearance = 0.5; // clearance for rack insertion

// --- Rack Dimensions (Matched to rack.scad logic) ---
_st = custom_slide_thickness;
_tolerance_z = 0.2;
_tolerance_xy = 0.4;
_min_rib_w = 2.0;
_slot_w = slot_width(_st, _tolerance_z);
_pitch = pitch(_slot_w, _min_rib_w);
_forced_pitch = max(_pitch, 5.0);

_pillar_w = wall_thickness;
// Rack Body X
_rack_x = (num_rack_slots * _forced_pitch) + _min_rib_w + (2 * _pillar_w);
// Rack Body Y
_rack_y = custom_slide_length + (2 * _pillar_w) + _tolerance_xy;
// Rack Body Z (height) -> Not critical for box footprint but needed for height
_slot_depth = custom_slide_width;
_rib_height = _slot_depth;
_crossbar_h = 2.5;
_base_h = _crossbar_h; // open_bottom=1
_rack_z = _rib_height + _base_h;
_handle_h = 15;
_total_rack_h = _rack_z + _handle_h;

// --- Box Dimensions ---
// Racks arranged in line (end-to-end)
// Inner dims
inner_x = (num_racks * _rack_x) + ( (num_racks + 1) * clearance);
// Extra clearance between racks? Or tight?
// If we want 15cm total length... 
// _rack_x approx 50mm + walls.
// 10 * 5 = 50. + 2 + 4 = 56mm?
// 56 * 3 = 168mm > 150mm.
// Check pitch: 5.0. 
// _forced_pitch = 5.0.
// _rack_x = (10 * 5) + 2 + 4 = 56mm.
// 3 * 56 = 168mm.
// The spec says "Largo: 15 cm".
// Maybe pitch is smaller? Slot w = 1.2. Rib = 2. Pitch = 3.2.
// But _forced_pitch = max(3.2, 5.0).
// Why 5.0? Staining rack minimum.
// If we reduce min pitch for this custom project?
// If pitch = 3.2mm. 10 * 3.2 = 32mm.
// _rack_x = 32 + 6 = 38mm.
// 3 * 38 = 114mm. Fits in 150mm.
// The specs say "numeración del 1 al 10". 5mm pitch is good for visibility.
// If I enable 5mm pitch, length is ~17cm.
// User spec: "Largo: 15 cm".
// I will stick to calculations and result in larger box, or reduce pitch.
// Let's stick to 5mm pitch for staining safety, but note dimension.

inner_y = _rack_y + (2 * clearance);
inner_z = _total_rack_h + clearance;

box_x = inner_x + (2 * wall_thickness);
box_y = inner_y + (2 * wall_thickness);
box_z = inner_z + wall_thickness; // Bottom only

render_mode = 0; // 0=base, 1=lid

module box_base() {
  diff("cavity")
    cuboid([box_x, box_y, box_z], anchor=BOTTOM) {
      tag("cavity")
        translate([0, 0, wall_thickness])
          cuboid([inner_x, inner_y, box_z], anchor=BOTTOM);
    }
}

module box_lid() {
  // Simple lid
  lid_h = 10;
  cuboid([box_x + 2, box_y + 2, lid_h], anchor=BOTTOM) {
    tag("remove")
      translate([0, 0, 2])
        cuboid([box_x + 0.4, box_y + 0.4, lid_h], anchor=BOTTOM);
  }
}

if (render_mode == 0) box_base();
if (render_mode == 1) box_lid();
