// Qubic wrapper — Spur Gear (MCAD)
use <MCAD/involute_gears.scad>

teeth_count = 20;
module_size = 2;
pressure_angle = 20;
thickness = 5;
bore_diameter = 5;
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 32;

_cp = module_size * 3.14159;

gear(number_of_teeth=teeth_count,
     circular_pitch=_cp,
     pressure_angle=pressure_angle,
     clearance=0.2,
     gear_thickness=thickness,
     rim_thickness=thickness,
     hub_thickness=thickness,
     hub_diameter=bore_diameter * 2.5,
     bore_diameter=bore_diameter);
