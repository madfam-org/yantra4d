// Yantra4D wrapper — Parametric Nut (threads-scad)
use <threads-scad/threads.scad>

diameter = 5;
width = 0;       // 0 = auto (1.7x diameter)
height = 0;      // 0 = auto (0.8x diameter)
pitch = 0.8;
nut_style_id = 0;  // 0=hex, 1=square, 2=nyloc
thread_enabled = true;
render_mode = 0;
fn = 0;

$fn = fn > 0 ? fn : 32;

_width = width > 0 ? width : diameter * 1.7;
_height = height > 0 ? height : diameter * 0.8;
_nyloc_extra = nut_style_id == 2 ? _height * 0.3 : 0;

difference() {
  // Outer shape
  if (nut_style_id == 1) {
    // Square nut
    translate([0, 0, 0])
      cube([_width, _width, _height + _nyloc_extra], center=true);
  } else {
    // Hex nut (default + nyloc)
    cylinder(d=_width, h=_height + _nyloc_extra, $fn=6, center=true);
  }
  // Thread hole
  if (thread_enabled) {
    ScrewHole(diameter, _height + _nyloc_extra + 1, pitch=pitch)
      cylinder(d=diameter, h=_height + _nyloc_extra + 1, center=true);
  } else {
    cylinder(d=diameter, h=_height + _nyloc_extra + 1, center=true);
  }
}
