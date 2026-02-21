// Yantra4D Gear Reducer — Gear Set Only
// Renders the input and output gears for print plate layout

include <../../libs/BOSL2/std.scad>
include <../../libs/BOSL2/gears.scad>

input_teeth = 12;
output_teeth = 36;
module_size = 1.5;
gear_thickness = 8;
shaft_diameter = 5;
bore_diameter = 5;
wall_thickness = 3;
pressure_angle = 20;
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 48;

if (render_mode == 0 || render_mode == 2) {
    // Input gear (pinion)
    spur_gear(mod=module_size, teeth=input_teeth, thickness=gear_thickness,
              shaft_diam=bore_diameter, pressure_angle=pressure_angle);
} else if (render_mode == 1 || render_mode == 3) {
    // Output gear
    spur_gear(mod=module_size, teeth=output_teeth, thickness=gear_thickness,
              shaft_diam=bore_diameter, pressure_angle=pressure_angle);
}
