// Yantra4D wrapper — Parametric Bolt (BOSL2)
include <../../libs/scad_core/core.scad>

diameter = 5;
length = 20;
pitch = 0.8;
head_diameter = 0; // 0 = auto (1.7x diameter)
head_height = 0; // 0 = auto (0.7x diameter)
head_style_id = 0; // 0=hex, 1=socket, 2=button
thread_enabled = true;
render_mode = 0;
fn = 0;

$fn = fn > 0 ? fn : 32;

_head_d = head_diameter > 0 ? head_diameter : diameter * 1.7;
_head_h = head_height > 0 ? head_height : diameter * 0.7;

// Head
if (head_style_id == 0) {
  // Hex head
  translate([0, 0, length])
    cylinder(d=_head_d, h=_head_h, $fn=6);
} else if (head_style_id == 1) {
  // Socket head (cylinder with socket recess)
  translate([0, 0, length]) {
    difference() {
      cylinder(d=_head_d, h=_head_h);
      translate([0, 0, _head_h / 2])
        cylinder(d=diameter * 0.6, h=_head_h / 2 + 0.1, $fn=6);
    }
  }
} else {
  // Button head (dome)
  translate([0, 0, length])
    cylinder(d=_head_d, h=_head_h * 0.6);
}

// Shaft with or without thread
if (thread_enabled) {
  y4d_standard_thread(d=diameter, p=pitch, l=length, anchor=BOT);
} else {
  cylinder(d=diameter, h=length, anchor=BOT);
}
