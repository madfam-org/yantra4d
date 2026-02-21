// Yantra4D wrapper — Spur Gear (BOSL2)
// Migrated from MCAD/involute_gears.scad → BOSL2 gears.scad
// BOSL2 advantages: active maintenance, shaft bore, helical support, rack-and-pinion
include <../../libs/BOSL2/std.scad>
include <../../libs/BOSL2/gears.scad>

// Parameters (injected by Yantra4D platform via -D flags)
teeth_count = 20;
module_size = 2; // gear module (mm per tooth)
pressure_angle = 20; // degrees
thickness = 5; // gear face width (mm)
bore_diameter = 5; // shaft bore (mm)
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 32;

spur_gear(
  mod=module_size,
  teeth=teeth_count,
  thickness=thickness,
  shaft_diam=bore_diameter,
  pressure_angle=pressure_angle
);
