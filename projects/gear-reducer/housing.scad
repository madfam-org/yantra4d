// Yantra4D Gear Reducer — Housing Only
// Renders just the housing parts for print plate layout

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
input_pd = pitch_radius(mod=module_size, teeth=input_teeth) * 2;
output_pd = pitch_radius(mod=module_size, teeth=output_teeth) * 2;
center_distance = (input_pd + output_pd) / 2;
clearance = 0.4;
bearing_od = 22;
bearing_h = 7;

housing_width = output_pd + wall_thickness * 2 + 10;
housing_depth = center_distance + output_pd / 2 + wall_thickness * 2 + 10;
housing_height = gear_thickness + bearing_h * 2 + wall_thickness * 2;

module housing_half() {
    half_h = housing_height / 2;
    difference() {
        translate([-housing_width/2, -output_pd/2 - wall_thickness, 0])
            cube([housing_width, housing_depth, half_h]);
        translate([0, 0, -1])
            cylinder(d=bearing_od + clearance, h=bearing_h + 1, $fn=$fn);
        translate([center_distance, 0, -1])
            cylinder(d=bearing_od + clearance, h=bearing_h + 1, $fn=$fn);
        translate([0, 0, bearing_h])
            hull() {
                cylinder(d=input_pd + module_size * 4 + clearance * 2, h=half_h, $fn=$fn);
                translate([center_distance, 0, 0])
                    cylinder(d=output_pd + module_size * 4 + clearance * 2, h=half_h, $fn=$fn);
            }
        for (x = [-housing_width/2 + 5, housing_width/2 - 5])
            for (y = [-output_pd/2 - wall_thickness + 5, -output_pd/2 - wall_thickness + housing_depth - 5])
                translate([x, y, -1])
                    cylinder(d=3.2, h=half_h + 2, $fn=24);
    }
}

if (render_mode == 0) {
    housing_half();
} else if (render_mode == 1) {
    mirror([0, 0, 1]) housing_half();
}
