// Yantra4D wrapper — Parametric Nut (BOSL2)
include <../../libs/BOSL2/std.scad>
include <../../libs/BOSL2/threading.scad>

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

_nut_shape = (nut_style_id == 1) ? "square" : "hex";

// If using thread, use BOSL2 threaded_nut directly
if (thread_enabled) {
  threaded_nut(nutwidth=_width, id=diameter, h=_height + _nyloc_extra, pitch=pitch, shape=_nut_shape, $slop=0.1, anchor=CENTER);
} else {
  difference() {
    // Outer shape
    if (nut_style_id == 1) {
      // Square nut
      cuboid([_width, _width, _height + _nyloc_extra], anchor=CENTER);
    } else {
      // Hex nut (default + nyloc)
      cylinder(d=_width, h=_height + _nyloc_extra, $fn=6, anchor=CENTER);
    }
    // Plain hole
    cylinder(d=diameter, h=_height + _nyloc_extra + 1, anchor=CENTER);
  }
}
